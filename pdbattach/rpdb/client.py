import socket
import selectors

from ..eventloop import EventLoop
from ..exchange import Subscriber, Exchange, message


class Client(Subscriber):
    def __init__(self):
        self._unix_sock = None

    def handle_msg_RemotePdbUp(self, msg: message.RemotePdbUp):
        self._unix_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._unix_sock.connect(msg.unix_address)
        self._unix_sock.setblocking(0)
        EventLoop().register(
            self._unix_sock,
            selectors.EVENT_READ,
            self.handle_socket_inbound,
        )

    def handle_msg_PtyDataReceived(self, msg: message.PtyDataReceived):
        if not msg.buf:
            self._unix_sock.close()
            EventLoop().unregister(self._unix_sock)
            return
        self._unix_sock.send(msg.buf)

    def handle_socket_inbound(self, _):
        buf = self._unix_sock.recv(40960)
        if not buf:
            EventLoop().unregister(self._unix_sock)
            self._unix_sock.close()

        Exchange().send(message.PdbDataReceived(buf))
