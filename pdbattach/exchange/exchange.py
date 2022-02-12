from ..utils import singleton


@singleton
class Exchange:
    def __init__(self):
        self._subs = set()

    def attach(self, sub):
        self._subs.add(sub)

    def detach(self, sub):
        self._subs.remove(sub)

    def send(self, event):
        for sub in self._subs:
            sub.recv(event)
