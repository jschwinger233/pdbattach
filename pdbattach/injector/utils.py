import syscall


def pokebytes(pid, address, bytes_):
    for i in range(len(bytes_) // 8 + 1):
        syscall.ptrace(
            syscall.PTRACE_POKEDATA,
            pid,
            address+8*i,
            int.from_bytes(
                bytes_[i*8:i*8+8],
                "little",
            ),
        )
