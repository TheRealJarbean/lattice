import time

START_TIME = time.monotonic()

def uptime_seconds() -> float:
    return time.monotonic() - START_TIME