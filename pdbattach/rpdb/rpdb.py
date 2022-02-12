import os
import sys
import socket
from pdb import Pdb
from contextlib import suppress


class rPdb(Pdb):
    def __init__(self, conn):
        self.conn = conn
        stream = conn.makefile("rw")
        return super().__init__(stdin=stream, stdout=stream)

    def do_detach(self, *args, **kws):
        self.conn.close()
        self.clear_all_breaks()
        return super().do_continue(*args, **kws)

    def do_quit(self, *args, **kws):
        self.conn.close()
        self.clear_all_breaks()
        return super().do_quit(*args, **kws)

    do_de = do_detach
    do_q = do_exit = do_quit


def set_trace(address: str):
    with suppress(FileNotFoundError):
        os.unlink(address)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(address)
    sock.listen(1)
    conn, _ = sock.accept()
    sock.close()
    pdb = rPdb(conn)
    frame = sys._getframe().f_back
    pdb.set_trace(frame)