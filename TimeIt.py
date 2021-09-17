import time

def eprint(*args, **kwargs):
    import sys

    print(*args, file=sys.stderr, **kwargs)

class TimeIt(object):
    def __init__(self, task_str, printf=eprint):
        self.print = printf
        self.s = task_str.ljust(35)

    def __enter__(self):
        self.t0 = time.time()
        return

    def __exit__(self, type, value, traceback):
        t1 = time.time()
        ts = f"{t1-self.t0:,.3f}".rjust(10)
        self.print(f"{self.s} {ts} s")
