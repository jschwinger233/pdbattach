import click
import shutil

from .injector import REPLInjector, SimpleInjector
from .eventloop import EventLoop


@click.group(
    context_settings=dict(help_option_names=["-h", "--help"]),
    invoke_without_command=True,
)
@click.option(
    "-p",
    "--pid",
    help="the Python process to tamper",
    type=int,
)
@click.option(
    "-c",
    "--command",
    help="the command to inject, e.g. -c 'print(2333)'",
)
@click.option(
    "-f",
    "--filename",
    help="the script to inject, e.g. -f evil.py",
    type=click.Path(exists=True, dir_okay=False),
)
def main(pid: int, command: str, filename: str):
    injector_cls = SimpleInjector

    if not command and not filename:
        command = f'import sys; sys.path.insert(len(sys.path), ""); import rpdb; rpdb.set_trace("/tmp/debug-{pid}.unix")'  # noqa
        injector_cls = REPLInjector

    elif filename:
        if not filename.endswith(".py"):
            raise ValueError('filename must endwith ".py"')

        shutil.copy(filename, f"/proc/{pid}/cwd/")
        command = f"import {filename[:-3]}"

    injector = injector_cls(pid, command)
    injector.start()
    EventLoop().run()
