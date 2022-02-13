# pdbattach
Attach pdb to a running Python process.

## Requirements

1. The `.symtab` section in the binary is required; or please prepare the corresponding debug version of CPython, we also accept separate debug file.
2. The CPython which is running the attached process must pip install the `pdbattach`; this calls for attention when there are multiple versions of CPython installed.

## Install

```
python3.8 -mpip install git+https://github.com/jschwinger233/pdbattach.git
```

## Usage

Suppose we have only one `python3.9` process running with command `python3.9 test.py`, and we want to attach it using the separate debug file `/usr/bin/python3.9-dbg`:


```bash
$ sudo pdbattach --symtab /usr/bin/python3.9-dbg $(pidof python3.9)
--Return--
> <string>(1)<module>()->None
(Pdb) b test.py:3
Breakpoint 1 at /home/gray/Dropbox/mac.local/Documents/src/github.com/jschwinger233/pdbattach/test.py:3
(Pdb) c
> /home/gray/Dropbox/mac.local/Documents/src/github.com/jschwinger233/pdbattach/test.py(3)<module>()->None
-> print(i)
(Pdb) p i
5
(Pdb) l
  1  	import time
  2  	for i in range(1000):
  3 B->	   print(i)
  4  	   time.sleep(10)
[EOF]
(Pdb) q
```
