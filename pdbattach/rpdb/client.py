import socket
import selectors

from ..eventloop import EventLoop
from ..exchange import Subscriber, Exchange, event


class Client(Subscriber):
    def __init__(self):
        self._unix_sock = None

    def _on_RemotePdbUp(self, event: event.RemotePdbUp):
        self._unix_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._unix_sock.connect(event.unix_address)
        self._unix_sock.setblocking(0)
        EventLoop().register(
            self._unix_sock,
            selectors.EVENT_READ,
            self.callback,
        )

    def _on_PtyDataReceived(self, event: event.PtyDataReceived):
        if not event.buf:
            self._unix_sock.close()
            return
        self._unix_sock.send(event.buf)

    def callback(self, _):
        buf = self._unix_sock.read(40960)
        if not buf:
            EventLoop().unregister(self._unix_sock)
            self._unix_sock.close()

        Exchange().send(event.PdbDataReceived(buf))
