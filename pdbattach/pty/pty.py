import os
import sys
import fcntl
import selectors

from ..eventloop import EventLoop
from ..exchange import Exchange, Subscriber, event


class Pty(Subscriber):
    def __init__(self):
        self._initiated = False
        self._stdin = sys.stdin

    def _on_PdbDataReceived(self, event: event.PdbDataReceived):
        if not self._initiated:
            fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
            fcntl.fcntl(sys.stdin, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            EventLoop().register(
                self._stdin,
                selectors.EVENT_READ,
                self.callback,
            )

        if not event.buf:
            event.buf = "EOF"
            sys.stdin.close()
        print(event.buf)

    def callback(self, _):
        buf = os.read(sys.stdin.fileno(), 4096)
        if not buf:
            EventLoop().unregister(self._stdin)

        Exchange().send(event.PtyDataReceived(buf))
