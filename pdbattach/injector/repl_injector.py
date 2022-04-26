import time
import shutil

from .simple_injector import SimpleInjector
from ..exchange import Exchange, message
from ..pty import Pty
from ..rpdb import rpdb
from ..rpdb import Client


class REPLInjector(SimpleInjector):
    def __init__(self, *args, **kws):
        super().__init__(*args, **kws)

        exchange = Exchange()
        exchange.attach(Client())
        exchange.attach(Pty())

    def _do_call_PyRun_SimpleStringFlags(self, fd):
        shutil.copy(rpdb.__file__, f"/proc/{self.pid}/cwd")
        super()._do_call_PyRun_SimpleStringFlags(fd)
        time.sleep(0.1)
        Exchange().send(
            message.RemotePdbUp(f"/proc/{self.pid}/root/tmp/debug-{self.pid}.unix") # noqa
        )
        return True
