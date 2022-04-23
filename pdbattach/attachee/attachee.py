import os
import enum
import time
import copy
import signal
import shutil
import selectors

import syscall

from . import elf
from ..rpdb import rpdb
from .utils import pokebytes
from ..eventloop import EventLoop
from ..exchange import Exchange, message, Subscriber


class State(enum.Enum):
    init = 0
    call_PyGILState_Ensure = 1
    syscall_mmap = 2
    call_PyRun_SimpleStringFlags = 3
    call_PyGILState_Release = 4
    syscall_munmap = 5
    restore_and_detach = 6


class Attachee(Subscriber):
    ALLOCATE_SIZE_IN_BYTE = 1024

    def __init__(self, pid: int):
        self.pid = pid

        self._signalfd = None
        self._state = 0

        self._offset_PyGILState_Ensure = elf.search_symbol_offset(
            pid, "PyGILState_Ensure"
        )
        self._offset_PyRun_SimpleStringFlags = elf.search_symbol_offset(
            pid, "PyRun_SimpleStringFlags"
        )
        self._offset_PyGILState_Release = elf.search_symbol_offset(
            pid, "PyGILState_Release"
        )

    def start_inject(self):
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

    def handle_general_signal(self, signo: int):
        signame = signal.Signal(signo).name
        print(f"got signal {signame}")

    @property
    def unix_address(self):
        return f"/tmp/debug-{self.pid}.unix"

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
        call(fd)
        self._state += 1

    def _do_call_PyGILState_Ensure(self, fd):
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
        regs.rax = self._offset_PyGILState_Ensure
        regs.rsp -= 152
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

    def _do_syscall_mmap(self, fd):
        regs = copy.copy(self._saved_regs)
        regs.rax = syscall.mmap.no
        regs.rdi = 0
        regs.rsi = self.ALLOCATE_SIZE_IN_BYTE
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

    def _do_call_PyRun_SimpleStringFlags(self, fd):
        rregs = syscall.UserRegsStruct()
        syscall.ptrace(syscall.PTRACE_GETREGS, self.pid, 0, rregs.byref())
        self._allocated_address = rregs.rax
        shutil.copy(rpdb.__file__, f"/proc/{self.pid}/cwd")
        pokebytes(
            self.pid,
            self._allocated_address,
            f'import sys; sys.path.insert(0, ""); import rpdb; rpdb.set_trace("{self.unix_address}")'.encode(),  # noqa
        )
        regs = copy.copy(self._saved_regs)
        regs.rax = self._offset_PyRun_SimpleStringFlags
        regs.rdi = self._allocated_address
        regs.rsi = 0
        regs.rsp -= 152
        regs.rbp = regs.rsp
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            regs.byref(),
        )
        syscall.ptrace(syscall.PTRACE_CONT, self.pid, 0, 0)

        time.sleep(0.1)
        Exchange().send(
            message.RemotePdbUp(f"/proc/{self.pid}/root/{self.unix_address}")
        )

    def _do_call_PyGILState_Release(self, fd):
        regs = copy.copy(self._saved_regs)
        regs.rax = self._offset_PyGILState_Release
        regs.rdi = 0x1
        regs.rsp -= 152  # magic
        regs.rbp = regs.rsp
        syscall.ptrace(
            syscall.PTRACE_SETREGS,
            self.pid,
            0,
            regs.byref(),
        )
        syscall.ptrace(syscall.PTRACE_CONT, self.pid, 0, 0)

    def _do_syscall_munmap(self, fd):
        regs = copy.copy(self._saved_regs)
        regs.rax = syscall.munmap.no
        regs.rdi = self._allocated_address
        regs.rsi = self.ALLOCATE_SIZE_IN_BYTE
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

    def _do_restore_and_detach(self, fd):
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
