import multiprocessing as mp


class DataStream:
    def __init__(self, blocking=False):
        self._read, self._write = mp.Pipe(duplex=False)
        self.blocking = blocking

    def write(self, data) -> bool:
        if not self.blocking:
            if self._read.poll():
                return False
            else:
                self._write.send(data)
                return True
        else:
            self._write.send(data)
            return True

    def read(self):
        if not self.blocking:
            if self._read.poll():
                return self._read.recv()
            else:
                return None
        else:
            return self._read.recv()