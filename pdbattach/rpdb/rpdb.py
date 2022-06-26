import os
import io
import sys
from pdb import Pdb
import _socket as socket
from contextlib import suppress


class rPdb(Pdb):
    def __init__(self, conn: int):
        self.conn = conn
        self.r, self.w = io.open(conn, "r"), io.open(conn, "w")
        return super().__init__(stdin=self.r, stdout=self.w)

    def _detach(self):
        with suppress(OSError):
            self.r.close()
            self.w.close()
            os.close(self.conn)
        self.clear_all_breaks()

    def do_detach(self, *args, **kws):
        self._detach()
        return super().do_continue(*args, **kws)

    def do_EOF(self, *args, **kws):
        self._detach()
        return super().do_EOF(*args, **kws)

    do_q = do_exit = do_quit = do_de = do_detach


def set_trace(address: str):
    with suppress(FileNotFoundError):
        os.unlink(address)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(address)
    sock.listen(1)
    conn, _ = sock._accept()
    sock.close()
    pdb = rPdb(conn)
    frame = sys._getframe().f_back
    pdb.set_trace(frame)
