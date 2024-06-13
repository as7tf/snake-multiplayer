import multiprocessing as mp

from utils.timer import Timer, print_func_time


class DataStream:
    def __init__(self):
        self._read, self._write = mp.Pipe(duplex=False)
        self._timer = Timer()

    def write(self, data, timeout: float = 0) -> bool:
        """Thread and Process safe"""
        self._timer.reset()
        while self._read.poll():
            if self._timer.elapsed_sec() < timeout:
                return False
        else:
            self._write.send(data)
            return True

    def read(self, timeout: float = 0) -> str | None:
        """Thread and Process safe"""
        if not self._read.poll(timeout):
            return None
        return self._read.recv()
