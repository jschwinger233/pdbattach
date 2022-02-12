import sys

from .exchange import Exchange
from .eventloop import EventLoop
from .attachee import Attachee
from .rpdb import Client

# from .pty import Pty


def main():
    pid = int(sys.argv[1])

    attachee = Attachee(pid)
    pdb_client = Client()
    # pty = Pty()

    exchange = Exchange()
    exchange.attach(attachee)
    exchange.attach(pdb_client)
    # exchange.attach(pty)

    attachee.start_inject()
    EventLoop().run()
