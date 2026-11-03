"""Bounded retries for transient Windows file-sharing locks during atomic replace."""
import time


def atomic_replace(source, destination):
    for attempt in range(8):
        try:
            return source.replace(destination)
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.05)
