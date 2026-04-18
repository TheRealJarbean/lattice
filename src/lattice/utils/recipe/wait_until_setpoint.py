import logging
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QTableWidget

# Local imports
from .wait_action import WaitAction
from lattice.devices.source import Source

logger = logging.getLogger(__name__)

# WAIT_UNTIL_SETPOINT action 
class WaitUntilSetpointAction(WaitAction):
    def __init__(self, source_dict: dict[str, Source]):
        super().__init__()
        self.sources = source_dict
        self.check_interval_ms = 500
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check)
        
    def run(self, recipe_table: QTableWidget, row: int):
        self.sources_finished = set()
        self.sources_checking = set()
        self.recipe_table = recipe_table
        self.row = row
        self.target_setpoints = {}
        self.previous_setpoints = {}
        
        # Gather values and associate with source names
        values_dict = self.gather_values_dict(recipe_table, row)
        for source_name, value in values_dict.items():
            if value is not None:
                self.previous_setpoints[source_name] = self.sources[source_name].get_setpoint()
                self.target_setpoints[source_name] = float(value)
                self.sources[source_name].set_setpoint(float(value))
                self.sources_checking.add(source_name)
        
        self.check_timer.start(self.check_interval_ms)
    
    def validate(self, recipe_table: QTableWidget, row: int):
        values_dict = self.gather_values_dict(recipe_table, row)
        for source_name, value in values_dict.items():
            try:
                float(value)
            except (ValueError, TypeError):
                logger.error(f"{value} is an invalid value.")
                return False
            
            if float(value) < 0:
                logger.error(f"{value} is invalid. Setpoint cannot be negative.")
                return False
            
            if float(value) > self.sources[source_name].get_max_setpoint():
                logger.error(f"{value} is invalid. Setpoint exceeds max setpoint safety")
                return False
        
        return True
    
    def pause(self):
        if self.check_timer.isActive():
            self.check_timer.stop()
    
    def resume(self):
        if not self.check_timer.isActive():
            self.check_timer.start(self.check_interval_ms)
    
    def stop(self):
        if self.check_timer.isActive():
            self.check_timer.stop()
    
    def _check(self):
        if self.sources_checking == self.sources_finished:
            self.can_continue.emit()
            self.check_timer.stop()
            return
        
        for source_name in self.sources_checking:
            previous = self.previous_setpoints[source_name]
            target = self.target_setpoints[source_name]
            process_variable = self.sources[source_name].get_process_variable()
            
            # Perform sign comparison to check if target has been "passed"
            if (process_variable - target) * (previous - target) < 0:
                self.sources_finished.add(source_name)