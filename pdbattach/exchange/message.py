import dataclasses


@dataclasses.dataclass
class RemotePdbUp:
    unix_address: str


@dataclasses.dataclass
class PdbDataReceived:
    buf: bytes


@dataclasses.dataclass
class PtyDataReceived:
    buf: str
