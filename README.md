# pdbattach

Attach pdb to a running Python process.

## Install

```
python3.8 -m pip install git+https://github.com/jschwinger233/pdbattach.git
```

## Usage

Suppose we have a `python3.9` process running with command `python3.9 test.py`, where `test.py` is a simple script:

```python
import time
for i in range(1000):
    print(i)
    time.sleep(10)
```

then we can attach it:

```bash
$ sudo pdbattach $(pgrep -f test.py)
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
