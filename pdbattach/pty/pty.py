import os
import sys
import fcntl
import selectors

from ..eventloop import EventLoop
from ..exchange import Exchange, Subscriber, message


class Pty(Subscriber):
    def __init__(self):
        self._initiated = False
        self._stdin = sys.stdin

    def handle_msg_PdbDataReceived(self, msg: message.PdbDataReceived):
        if not self._initiated:
            self._initiated = True
            fl = fcntl.fcntl(self._stdin, fcntl.F_GETFL)
            fcntl.fcntl(self._stdin, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            EventLoop().register(
                self._stdin,
                selectors.EVENT_READ,
                self.handle_stdin_input,
            )

        if not msg.buf:
            os.close(self._stdin.fileno())
            EventLoop().unregister(self._stdin)
            return
        print(msg.buf.decode(), end="", flush=True)

    def handle_stdin_input(self, _):
        buf = os.read(self._stdin.fileno(), 4096)
        if not buf:
            EventLoop().unregister(self._stdin)

        Exchange().send(message.PtyDataReceived(buf))
