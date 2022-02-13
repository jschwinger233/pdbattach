from ..utils import singleton


class Subscriber:
    def recv(self, msg):
        handle = getattr(self, "handle_msg_" + msg.__class__.__name__, None)
        if handle:
            handle(msg)


@singleton
class Exchange:
    def __init__(self):
        self._subs = set()

    def attach(self, sub: Subscriber):
        self._subs.add(sub)

    def detach(self, sub: Subscriber):
        self._subs.remove(sub)

    def send(self, msg):
        for sub in self._subs:
            sub.recv(msg)
