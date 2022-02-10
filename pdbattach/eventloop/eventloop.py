import selectors

from ..utils import singleton


@singleton
class EventLoop:
    def __init__(self):
        self._cnt = 0
        self._selector = selectors.DefaultSelector()

    def register(self, fd: int, event_type, callback):
        self._selector.register(fd, event_type, callback)
        self._cnt += 1

    def unregister(self, fd: int):
        self._selector.unregister(fd)
        self._cnt -= 1
        if self._cnt == 0:
            self._run = False

    def run(self):
        self._run = True
        while self._run:
            events = self._selector.select()
            for key, _ in events:
                key.data(key.fileobj)
