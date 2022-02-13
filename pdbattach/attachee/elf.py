from elftools.elf.elffile import ELFFile


def search_symbol_offset(binary: str, symbol: str) -> int:
    with open(binary, "rb") as f:
        elf = ELFFile(f)
        symtab = elf.get_section_by_name(".symtab")
        if not symtab:
            raise ValueError(f"symtab not found in {binary}")

        syms = symtab.get_symbol_by_name(symbol)
        if not syms:
            raise ValueError(f'symbol "{symbol}" not found in {binary}')

        return syms[0]["st_value"]
