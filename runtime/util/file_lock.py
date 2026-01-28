import os
import time
import contextlib

class FileLock:
    """
    A simple file-based lock for process capabilities.
    Not robust against crashes leaving stale locks (needs TTL or manual cleanup),
    but sufficient for single-run/short-lived contention tests.
    """
    def __init__(self, lock_path: str, timeout: float = 10.0, poll_interval: float = 0.1):
        self.lock_path = lock_path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._acquired = False

    def acquire(self):
        start_time = time.time()
        while True:
            try:
                # Exclusive creation - fails if file exists
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self._acquired = True
                return True
            except FileExistsError:
                if time.time() - start_time >= self.timeout:
                    return False
                time.sleep(self.poll_interval)
            except OSError:
                return False

    def release(self):
        if self._acquired:
            try:
                os.remove(self.lock_path)
            except OSError:
                pass # Already gone?
            self._acquired = False

    @contextlib.contextmanager
    def acquire_ctx(self):
        if self.acquire():
            try:
                yield True
            finally:
                self.release()
        else:
            yield False
