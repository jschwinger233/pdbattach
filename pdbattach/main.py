import argparse

from .exchange import Exchange
from .eventloop import EventLoop
from .attachee import Attachee
from .rpdb import Client
from .pty import Pty


def main():
    parser = argparse.ArgumentParser(
        description="pdb attach a running Python process."
    )
    parser.add_argument(
        "pid",
        type=int,
        help="a Python process pid",
    )
    args = parser.parse_args()

    attachee = Attachee(args.pid)
    pdb_client = Client()
    pty = Pty()

    exchange = Exchange()
    exchange.attach(attachee)
    exchange.attach(pdb_client)
    exchange.attach(pty)

    attachee.start_inject()
    EventLoop().run()
