import os
import subprocess
from . import print_sym_offset


def search_symbol_offset(pid: int, symbol: str) -> int:
    with open(print_sym_offset.__file__) as f:
        script_code = f.read()

    bin_under_mount = os.readlink(f"/proc/{pid}/exe")

    try:
        process = subprocess.run(
            [
                "nsenter",
                f"--pid=/proc/{pid}/ns/pid",
                "chroot",
                f"/proc/{pid}/root",
                bin_under_mount,
                "-",
                symbol,
            ],
            capture_output=True,
            encoding="utf8",
            check=True,
            input=script_code,
        )
    except subprocess.CalledProcessError as err:
        print(err.stderr)
        raise

    parts = process.stdout.split(":")
    offset, elf, seq = int(parts[0]), parts[1], int(parts[2])

    with open(f"/proc/{pid}/maps") as f:
        cnt = -1
        for line in f:
            if not line.rstrip().endswith(elf):
                continue
            cnt += 1
            if cnt == seq:
                return offset + int(line.split("-")[0], base=16)

    raise ValueError(f"map not found: elf {elf}, seq {seq}")


if __name__ == "__main__":
    import sys

    print(search_symbol_offset(int(sys.argv[1]), sys.argv[2]))
