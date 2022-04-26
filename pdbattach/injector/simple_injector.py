import os
import enum
import copy
import uuid
import signal
import selectors
import contextlib

import syscall

from . import elf
from .utils import pokebytes
from ..eventloop import EventLoop


class State(enum.Enum):
    init = 0
    syscall_mmap = 1
    call_PyGILState_Ensure = 2
    probe_stack_offset = 3
    call_PyRun_SimpleStringFlags = 4
    call_PyGILState_Release = 5
    syscall_munmap = 6
    restore_and_detach = 7


class SimpleInjector:
    def __init__(self, pid: int, command: str):
        self.pid = pid
        self.command = command

        self._signalfd = None
        self._state = 0
        self._sentinel = f"/tmp/{uuid.uuid4()}"
        self._new_frame_offset = 16

        self._offset_PyGILState_Ensure = elf.search_symbol_offset(
            pid, "PyGILState_Ensure"
        )
        self._offset_PyRun_SimpleStringFlags = elf.search_symbol_offset(
            pid, "PyRun_SimpleStringFlags"
        )
        self._offset_PyGILState_Release = elf.search_symbol_offset(
            pid, "PyGILState_Release"
        )

    def start(self):
        signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGCHLD])
        self._signalfd = syscall.signalfd(
            -1,
            [signal.SIGCHLD],
            syscall.SFD_NONBLOCK,
        )
        EventLoop().register(
            self._signalfd,
            selectors.EVENT_READ,
            self.callback,
        )

        syscall.ptrace(syscall.PTRACE_ATTACH, self.pid, 0, 0)

    def callback(self, fd):
        ssi = syscall.SignalfdSiginfo()
        n = syscall.read(fd, ssi.byref(), ssi.sizeof())
        if n != len(ssi):
            raise RuntimeError(
                f"expect to read {len(ssi)} bytes, but got {n} only"
            )

        if ssi.ssi_signo != signal.SIGCHLD:
            self.handle_general_signal(ssi.ssi_signo)
            return

        os.wait()
        call = getattr(self, "_do_" + State(self._state + 1).name)
        if call(fd):
            self._state += 1

    def handle_general_signal(self, signo: int):
        signame = signal.Signal(signo).name
        print(f"got signal {signame}")

    def _do_syscall_mmap(self, fd) -> bool:
        self._saved_regs = syscall.UserRegsStruct()
        syscall.ptrace(
            syscall.PTRACE_GETREGS, self.pid, 0, self._saved_regs.byref()
        )
        self._current_instruction = syscall.ptrace(
            syscall.PTRACE_PEEKDATA,
            self.pid,
            self._saved_regs.rip,
            0,
        )
        self._next_instruction = syscall.ptrace(
            syscall.PTRACE_PEEKDATA,
            self.pid,
            self._saved_regs.rip + 2,
            0,
        )
        syscall.ptrace(
            syscall.PTRACE_POKEDATA,
            self.pid,
            self._saved_regs.rip,
            self._current_instruction & ~0xFFFF | 0xD0FF,  # call *%rax
        )
        syscall.ptrace(
            syscall.PTRACE_POKEDATA,
            self.pid,
            self._saved_regs.rip + 2,
            self._next_instruction & ~0xFF | 0xCC,  # int
        )

        regs = copy.copy(self._saved_regs)
        regs.rax = syscall.mmap.no
        regs.rdi = 0
        regs.rsi = 1024  # todo
        regs.rdx = syscall.PROT_READ | syscall.PROT_WRITE
        regs.r10 = syscall.MAP_PRIVATE | syscall.MAP_ANONYMOUS
        regs.r8 = 0
        regs.r9 = 0
        regs.rip -= 2
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            regs.byref(),
        )
        syscall.ptrace(
            syscall.PTRACE_SINGLESTEP,
            self.pid,
            0,
            0,
        )
        return True

    def _do_call_PyGILState_Ensure(self, fd) -> bool:
        rregs = syscall.UserRegsStruct()
        syscall.ptrace(syscall.PTRACE_GETREGS, self.pid, 0, rregs.byref())
        self._allocated_address = rregs.rax

        regs = copy.copy(self._saved_regs)
        regs.rax = self._offset_PyGILState_Ensure
        regs.rsp -= self._new_frame_offset
        regs.rbp = regs.rsp
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            regs.byref(),
        )
        syscall.ptrace(
            syscall.PTRACE_CONT,
            self.pid,
            0,
            0,
        )
        return True

    def _do_probe_stack_offset(self, fd) -> bool:

        regs = copy.copy(self._saved_regs)

        with contextlib.suppress(FileNotFoundError):
            os.stat(f"/proc/{self.pid}/root/{self._sentinel}")

            pokebytes(
                self.pid,
                self._allocated_address,
                f"import os; os.remove('{self._sentinel}')".encode(),
            )
            regs.rax = self._offset_PyRun_SimpleStringFlags
            regs.rdi = self._allocated_address
            regs.rsi = 0
            regs.rsp -= self._new_frame_offset
            regs.rbp = regs.rsp
            syscall.ptrace(syscall.PTRACE_SETREGS, self.pid, 0, regs.byref())
            syscall.ptrace(syscall.PTRACE_CONT, self.pid, 0, 0)
            return True

        self._new_frame_offset += 8
        if self._new_frame_offset > 8*50:
            raise RuntimeError("valid new frame offset not found")

        pokebytes(
            self.pid,
            self._allocated_address,
            f"import os; os.mknod('{self._sentinel}')".encode(),
        )
        regs.rax = self._offset_PyRun_SimpleStringFlags
        regs.rdi = self._allocated_address
        regs.rsi = 0
        regs.rsp -= self._new_frame_offset
        regs.rbp = regs.rsp
        syscall.ptrace(syscall.PTRACE_SETREGS, self.pid, 0, regs.byref())
        syscall.ptrace(syscall.PTRACE_CONT, self.pid, 0, 0)
        return False

    def _do_call_PyRun_SimpleStringFlags(self, fd) -> bool:
        pokebytes(
            self.pid,
            self._allocated_address,
            self.command.encode(),
        )
        regs = copy.copy(self._saved_regs)
        regs.rax = self._offset_PyRun_SimpleStringFlags
        regs.rdi = self._allocated_address
        regs.rsi = 0
        regs.rsp -= self._new_frame_offset
        regs.rbp = regs.rsp
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            regs.byref(),
        )
        syscall.ptrace(syscall.PTRACE_CONT, self.pid, 0, 0)
        return True

    def _do_call_PyGILState_Release(self, fd) -> bool:
        regs = copy.copy(self._saved_regs)
        regs.rax = self._offset_PyGILState_Release
        regs.rdi = 0x1
        regs.rsp -= self._new_frame_offset
        regs.rbp = regs.rsp
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            regs.byref(),
        )
        syscall.ptrace(syscall.PTRACE_CONT, self.pid, 0, 0)
        return True

    def _do_syscall_munmap(self, fd) -> bool:
        regs = copy.copy(self._saved_regs)
        regs.rax = syscall.munmap.no
        regs.rdi = self._allocated_address
        regs.rsi = 1024
        regs.rdx = 0
        regs.r10 = 0
        regs.r8 = 0
        regs.r9 = 0
        regs.rip -= 2
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            regs.byref(),
        )
        syscall.ptrace(
            syscall.PTRACE_SINGLESTEP,
            self.pid,
            0,
            0,
        )
        return True

    def _do_restore_and_detach(self, fd) -> True:
        syscall.ptrace(
            syscall.PTRACE_POKEDATA,
            self.pid,
            self._saved_regs.rip + 2,
            self._next_instruction,
        )
        syscall.ptrace(
            syscall.PTRACE_POKEDATA,
            self.pid,
            self._saved_regs.rip,
            self._current_instruction,
        )
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            self._saved_regs.byref(),
        )
        syscall.ptrace(syscall.PTRACE_DETACH, self.pid, 0, 0)

        eventloop = EventLoop()
        eventloop.unregister(self._signalfd)
        return True
