import os
import tempfile
import time
from contextlib import contextmanager


@contextmanager
def tts_process_lock(timeout_s: float = 30.0, poll_s: float = 0.05):
    """
    Cross-process lock (Windows-friendly) to prevent overlapping TTS playback
    when multiple Jarvis entrypoints run simultaneously (e.g. GUI + main).
    """
    lock_path = os.path.join(tempfile.gettempdir(), "jarvis_tts.lock")
    start = time.time()
    f = None

    while True:
        try:
            # os.O_EXCL makes creation atomic across processes
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            f = os.fdopen(fd, "w", encoding="utf-8")
            f.write(str(os.getpid()))
            f.flush()
            break
        except FileExistsError:
            if (time.time() - start) >= timeout_s:
                # Best effort: don't block forever; allow speaking to continue.
                break
            time.sleep(poll_s)

    try:
        yield
    finally:
        try:
            if f is not None:
                f.close()
            # Only delete if we own it; if timed out we might not own.
            if f is not None and os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception:
            pass
