from ..utils import singleton


class Subscriber:
    def recv(self, event):
        event_callback = getattr(self, "_on_" + event.__class__.__name__, None)
        if event_callback:
            event_callback(event)


@singleton
class Exchange:
    def __init__(self):
        self._subs = set()

    def attach(self, sub: Subscriber):
        self._subs.add(sub)

    def detach(self, sub: Subscriber):
        self._subs.remove(sub)

    def send(self, event):
        for sub in self._subs:
            sub.recv(event)
