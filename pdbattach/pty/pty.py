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
            self._initiated = True
            fl = fcntl.fcntl(self._stdin, fcntl.F_GETFL)
            fcntl.fcntl(self._stdin, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            EventLoop().register(
                self._stdin,
                selectors.EVENT_READ,
                self.callback,
            )

        if not event.buf:
            os.close(self._stdin.fileno())
            EventLoop().unregister(self._stdin)
            return
        print(event.buf.decode(), end='')

    def callback(self, _):
        buf = os.read(self._stdin.fileno(), 4096)
        if not buf:
            EventLoop().unregister(self._stdin)

        Exchange().send(event.PtyDataReceived(buf))
