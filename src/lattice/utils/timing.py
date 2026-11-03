import time
from datetime import datetime, timedelta
from lattice.utils.config import AppConfig

START_TIME = time.monotonic()

def uptime_seconds() -> float:
    return time.monotonic() - START_TIME

def duration_to_str(total_seconds: int):
    if AppConfig.PREFERENCES["display_time_as_local_time"]:
        now = datetime.now().astimezone()
        dt = now - timedelta(seconds=uptime_seconds()) + timedelta(seconds=total_seconds)
        return dt.strftime("%H:%M:%S")
        
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"