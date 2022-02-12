import os
import time
import copy
import signal
import selectors
from enum import Enum

import syscall

from .utils import pokebytes
from ..eventloop import EventLoop
from ..exchange import Exchange, event, Subscriber


class State(Enum):
    init = 0
    call_PyGILState_Ensure = 1
    syscall_mmap = 2
    call_PyRun_SimpleString = 3
    call_PyGILState_Release = 4
    restore_and_detach = 5


class Attachee(Subscriber):
    def __init__(self, pid):
        self.pid = pid

        self._signalfd = None
        self._state = 0

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
        regs.rax = 0x523CCF
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
        regs.rsi = 1024  # 1024 bytes
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

    def _do_call_PyRun_SimpleString(self, fd):
        rregs = syscall.UserRegsStruct()
        syscall.ptrace(syscall.PTRACE_GETREGS, self.pid, 0, rregs.byref())
        self._allocated_address = rregs.rax
        pokebytes(
            self.pid,
            self._allocated_address,
            f'from pdbattach import rpdb; rpdb.set_trace("{self.unix_address}")'.encode(),  # noqa
        )
        regs = copy.copy(self._saved_regs)
        regs.rax = 0x527C0A
        regs.rdi = self._allocated_address
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
        Exchange().send(event.RemotePdbUp(self.unix_address))

    def _do_call_PyGILState_Release(self, fd):
        regs = copy.copy(self._saved_regs)
        regs.rax = 0x523D87
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
