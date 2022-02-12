import dataclasses


@dataclasses.dataclass
class RemotePdbUp:
    address: str


@dataclasses.dataclass
class PdbDataReceived:
    buf: str
