import multiprocessing as mp


class DataStream:
    def __init__(self):
        self._read, self._write = mp.Pipe(duplex=False)

    def write(self, data, timeout: float = 0) -> bool:
        """Thread and Process safe"""
        if self._read.poll(timeout):
            return False
        self._write.send(data)
        return True

    def read(self, timeout: float = 0) -> str | None:
        """Thread and Process safe"""
        if not self._read.poll(timeout):
            return None
        return self._read.recv()
