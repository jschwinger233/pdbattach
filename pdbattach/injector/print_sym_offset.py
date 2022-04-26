import os
import sys
import ctypes


if __name__ == "__main__":
    symbol = sys.argv[-1]
    func = ctypes.pythonapi[symbol]
    address = ctypes.cast(func, ctypes.c_void_p).value
    with open("/proc/{}/maps".format(os.getpid())) as f:
        last_elf, seq = "", -1
        for line in f:
            columns = line.split()
            elf = columns[-1]
            if not elf.startswith("/"):
                continue
            if last_elf == elf:
                seq += 1
            else:
                last_elf = elf
                seq = 0
            parts = columns[0].split("-")
            start, end = int(parts[0], base=16), int(parts[1], base=16)
            if start <= address < end:
                print(
                    address - start,
                    elf,
                    seq,
                    sep=":",
                    end="",
                )
                sys.exit(0)
    sys.exit(1)
