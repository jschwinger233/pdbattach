import socket
import selectors

from ..eventloop import EventLoop
from ..exchange import Exchange, event


class Client:
    def __init__(self):
        self._unix_sock = None

    def recv(self, event):
        event_callback = getattr(self, "_on_" + event.__name__)
        event_callback(event)

    def _on_RemotePdbUp(self, event: event.RemotePdbUp):
        self._unix_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._unix_sock.connect(event.unix_address)
        self._unix_sock.setblocking(0)
        EventLoop().register(
            self._unix_sock,
            selectors.EVENT_READ,
            self.callback,
        )

    def callback(self, _):
        buf = self._unix_sock.read(40960)
        if not buf:
            buf = 'EOF'
            EventLoop().unregister(self._unix_sock)
            self._unix_sock.close()

        Exchange().send(event.PdbDataReceived(buf))
