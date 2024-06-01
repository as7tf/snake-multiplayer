import time


class Timer:
    def __init__(self):
        self._time = time.time_ns()

    def reset(self):
        self._time = time.time_ns()

    def elapsed_ms(self):
        ret = time.time_ns() - self._time
        ret = ret / 10e5
        return ret
