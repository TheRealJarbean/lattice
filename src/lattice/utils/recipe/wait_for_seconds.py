import logging
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QTableWidget

# Local imports
from .wait_action import WaitAction

logger = logging.getLogger(__name__)

# WAIT_FOR_TIME_SECONDS action
class WaitForSecondsAction(WaitAction):
    def __init__(self):
        super().__init__()
        self.wait_timer = QTimer()
        self.wait_timer.setSingleShot(True)
        self.wait_timer.timeout.connect(self.can_continue.emit)
        
        self.time_remaining = None
        
        self.update_monitor_timer = QTimer()
        self.update_monitor_timer.timeout.connect(lambda: self.update_monitor_data.emit(self._get_formatted_remaining_time()))
        
    def run(self, recipe_table: QTableWidget, row: int):
        values = self.gather_values(recipe_table, row)
        time_seconds = float(values[0])
        time_ms = int(time_seconds * 1000)
        self.wait_timer.start(time_ms)
        self.update_monitor_timer.start(10)

    def validate(self, recipe_table: QTableWidget, row: int) -> bool:
        values = self.gather_values(recipe_table, row)
        time_seconds = values[0]
        try:
            float(time_seconds)
        except (ValueError, TypeError):
            logger.error(f"{time_seconds} is an invalid value.")
            return False
        
        if float(time_seconds) <= 0:
            logger.error(f"{time_seconds} is invalid. Cannot wait for negative or 0 seconds.")
            return False
        
        return True
    
    def pause(self):
        if self.wait_timer.isActive():
            self.time_remaining = self.wait_timer.remainingTime()
            self.wait_timer.stop()
            
        if self.update_monitor_timer.isActive():
            self.update_monitor_timer.stop()
        
    def resume(self):
        if not self.wait_timer.isActive() and self.time_remaining is not None:
            self.wait_timer.start(self.time_remaining)
            self.time_remaining = None
            
            if not self.update_monitor_timer.isActive():
                self.update_monitor_timer.start(10)
    
    def stop(self):
        if self.wait_timer.isActive():
            self.wait_timer.stop()
            
        if self.update_monitor_timer.isActive():
            self.update_monitor_timer.stop()
        
        # Ensure any junk data sent while timers are stopping is cleared
        self.update_monitor_data.emit("")
        
        self.time_remaining = None
        
    def _get_formatted_remaining_time(self):
        total_ms = self.wait_timer.remainingTimeAsDuration()
        ms = total_ms % 1000
        hours = total_ms // (60 * 60 * 1000)
        minutes = (total_ms % (60 * 60 * 1000)) // (60 * 1000)
        seconds = (total_ms % (60 * 1000)) // 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"