# pdbattach

Attach pdb to a running Python process.

## Install

```
python3.8 -mpip install git+https://github.com/jschwinger233/pdbattach.git
```

## Usage

### check process stack

```
sudo pdbattach -p $pid -c 'import traceback; f=open("/tmp/bt", "w+"); print("".join(traceback.format_stack()), file=f, flush=True); f.close()'
```

Then you will find the process's stack backtrace at `/tmp/bt` like:

```
  File "/usr/lib/python3.8/runpy.py", line 194, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.8/runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "/usr/lib/python3.8/http/server.py", line 1294, in <module>
    test(
  File "/usr/lib/python3.8/http/server.py", line 1257, in test
    httpd.serve_forever()
  File "/usr/lib/python3.8/socketserver.py", line 232, in serve_forever
    ready = selector.select(poll_interval)
  File "/usr/lib/python3.8/selectors.py", line 415, in select
    fd_event_list = self._selector.poll(timeout)
  File "<string>", line 1, in <module>
```

### interactive debugging using pdb

Suppose we have a `python3.9` process running with command `python3.9 test.py`, where `test.py` is a simple script:

```python
import time
for i in range(1000):
    print(i)
    time.sleep(10)
```

then we can attach it:

```bash
$ sudo pdbattach -p $(pgrep -f test.py)
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

### inject any code snippets

Suppose we have a simple HTTP server causing memory leak, and we want to use [memray](https://github.com/bloomberg/memray) to do a memory profile by attaching.

Firstly let's enable the tracker:

```bash
sudo pdbattach -p $(pidof python3.9) -c 'import memray; global t; t = memray.Tracker("out.bin"); t.__enter__(); print(t)'
```

You can also put the statements in a script file and run by:

```bash
sudo pdbattach -p $(pidof python3.9) -f mem_track.py
```

Suppose the output of the above injection is:

```
Memray WARNING: Correcting symbol for malloc from 0x421420 to 0x7f0400389110
Memray WARNING: Correcting symbol for free from 0x421890 to 0x7f0400389700
<memray._memray.Tracker object at 0x7f03ff6598d0>
```

Then after a while, stop the tracker and inspect the outcomes:

```bash
sudo pdbattach -p $(pidof python3.9) -c 'import ctypes; ctypes.cast(0x7f03ff6598d0, ctypes.py_object).value.__exit__(None, None, None)'
```

## Known Issues

1. pdb doesn't work properly under multi-thread scenarios. See [issue](https://bugs.python.org/issue41571).
2. ptrace(2) relies on `struct user_regs_struct` whose definition varies across platforms, therefore running pdbattach inside a container (e.g. from docker.io/python:3 image) to attach a host process will cause segmentation fault. See [issue](https://github.com/jschwinger233/pdbattach/issues/4).
