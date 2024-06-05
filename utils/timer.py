import time


class Timer:
    def __init__(self):
        self.reset()

    def reset(self):
        self._time = time.time_ns()

    def elapsed_ms(self):
        elapsed = time.time_ns() - self._time
        elapsed = elapsed / 10e5
        return elapsed

    def elapsed_sec(self):
        elapsed = time.time_ns() - self._time
        elapsed = elapsed / 10e8
        return elapsed

if __name__ == "__main__":
    timer = Timer()
    timer.reset()
    counter = 0
    while counter < 10e5:
        counter += 1
    print(timer.elapsed_ms())
    print(timer.elapsed_sec())
