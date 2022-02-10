_classes = dict()


def singleton(cls):
    def new():
        if cls not in _classes:
            _classes[cls] = cls()
        return _classes[cls]

    return new
