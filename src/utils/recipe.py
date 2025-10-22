"""
IMPORTANT: In the main program, these recipe action objects will only be created once.
This means they need to be reset in the run() method.
So any attributes that store temporary state (any data that changes between steps or recipes)
need to be reset to their initial values. (see WaitUntilSetpoint for example)
"""

import logging
from PySide6.QtCore import Signal, QTimer, QObject
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QComboBox

# Local imports
from devices.source import Source
from devices.shutter import Shutter

logger = logging.getLogger(__name__)

# Base class for all recipe actions
class RecipeAction(QObject):
    can_continue = Signal()
    
    def __init__(self):
        super().__init__()
        
    def run(self, recipe_table: QTableWidget, row: int):
        """
        Execute some logic on provided values
        """
        raise NotImplementedError("This method should be implemented!")
    
    def validate(self, recipe_table: QTableWidget, row: int):
        """
        Validate provided values
        """
        raise NotImplementedError("This method should be implemented!")
    
    def gather_values(self, recipe_table: QTableWidget, row: int) -> list:
        """
        Returns all values in list
        """
        values = []
        for col in range(1, recipe_table.columnCount()):
            item = recipe_table.item(row, col)
            value = item.text() if item is not None else None
            values.append(value)
            
        return values
            
    def gather_values_dict(self, recipe_table: QTableWidget, row: int) -> dict[str, str]:
        """
        Returns values in a dictionary with column name keys
        """
        values_dict = {}
        for col in range(1, recipe_table.columnCount()):
            name = recipe_table.horizontalHeaderItem(col).text()
            item = recipe_table.item(row, col)
            
            if item is None:
                values_dict[name] = None
            
            value = item.text() if item.text() is not "" else None
            values_dict[name] = value
            
        return values_dict
        
    def format_row(self, recipe_table: QTableWidget, row: int):
        for col in range(1, recipe_table.columnCount()):
            self.format_cell(recipe_table, col, row)
            
    def format_cell(self, recipe_table: QTableWidget, col: int, row: int):
        recipe_table.removeCellWidget(row, col)
        recipe_table.setItem(row, col, QTableWidgetItem(""))

# Base class for actions that may have to pause, resume, and stop
# i.e. recipe action is not executed instantaneously
class WaitAction(RecipeAction):
    def __init__(self):
        super().__init__()
        
    def pause(self):
        raise NotImplementedError("This method should be implemented!")
    
    def resume(self):
        raise NotImplementedError("This method should be implemented!")
    
    def stop(self):
        raise NotImplementedError("This method should be implemented!")

# WAIT_FOR_TIME_SECONDS action
class WaitForSecondsAction(WaitAction):
    def __init__(self):
        super().__init__()
        self.wait_timer = QTimer()
        self.wait_timer.setSingleShot(True)
        self.wait_timer.timeout.connect(self.can_continue.emit)
        self.time_remaining = None
        
    def run(self, recipe_table: QTableWidget, row: int):
        values = self.gather_values(recipe_table, row)
        time_seconds = float(values[0])
        time_ms = int(time_seconds * 1000)
        self.wait_timer.start(time_ms)

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
        
    def resume(self):
        if not self.wait_timer.isActive() and self.time_remaining is not None:
            self.wait_timer.start(self.time_remaining)
            self.time_remaining = None
    
    def stop(self):
        if self.wait_timer.isActive():
            self.wait_timer.stop()
        self.time_remaining = None

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
        
        # Gather values and associate with source names
        values_dict = self.gather_values_dict(recipe_table, row)
        for source_name, value in values_dict.items():
            if value is not None:
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
            if self.sources[source_name].is_pv_close_to_sp():
                self.sources_finished.add(source_name)
                
# WAIT_UNTIL_SETPOINT_STABLE action
# Extends WaitUntilSetpointAction because it is almost identical, just a slightly different check
class WaitUntilSetpointStableAction(WaitUntilSetpointAction):
    def __init__(self, source_dict: dict[str, Source]):
        super().__init__(source_dict)
        
        # Reconnect timer to subclass version of _check
        self.check_timer.timeout.disconnect()
        self.check_timer.timeout.connect(self._check)
        
    def _check(self):
        if self.sources_checking == self.sources_finished:
            self.can_continue.emit()
            self.check_timer.stop()
            return
        
        for source_name in self.sources_checking:
            source = self.sources[source_name]
            if source.get_is_stable() and source.is_pv_close_to_sp():
                self.sources_finished.add(source_name)
            else:
                self.sources_finished.discard(source_name)
                
# RATE_LIMIT action
class RateLimitAction(RecipeAction):
    def __init__(self, source_dict: dict[str, Source]):
        super().__init__()
        self.sources = source_dict
        
    def run(self, recipe_table: QTableWidget, row: int):
        values_dict = self.gather_values_dict(recipe_table, row)
        for source_name, value in values_dict.items():
            if value is not None:
                self.sources[source_name].set_rate_limit(float(value))
                
        self.can_continue.emit()
    
    def validate(self, recipe_table: QTableWidget, row: int):
        values = self.gather_values(recipe_table, row)
        for value in values:
            try:
                float(value)
            except (ValueError, TypeError):
                logger.error(f"{value} is an invalid value.")
                return False
            
            if float(value) <= 0:
                logger.error(f"{value} is invalid. Rate limit cannot be 0 or negative.")
                return False
        
        return True

# SETPOINT action
class SetpointAction(RecipeAction):
    def __init__(self, source_dict: dict[str, Source]):
        super().__init__()
        self.sources = source_dict
        
    def run(self, recipe_table: QTableWidget, row: int):
        values_dict = self.gather_values_dict(recipe_table, row)
        for source_name, value in values_dict.items():
            if value is not None:
                self.sources[source_name].set_setpoint(float(value))
        
        self.can_continue.emit()
    
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
    
# SHUTTER action
class ShutterAction(RecipeAction):
    open_shutter = Signal(Shutter)
    close_shutter = Signal(Shutter)
    
    def __init__(self, shutter_dict: dict[str, Shutter]):
        super().__init__()
        self.shutters = shutter_dict
        
        for shutter in self.shutters.values():
            self.open_shutter.connect(shutter.open)
            self.close_shutter.connect(shutter.close)
        
    def run(self, recipe_table: QTableWidget, row: int):
        for col in range(1, recipe_table.columnCount()):
            shutter_name = recipe_table.horizontalHeaderItem(col).text()
            widget: QComboBox = recipe_table.cellWidget(row, col)
            
            if widget.currentText() == "":
                continue
            
            if widget.currentText() == "OPEN":
                self.open_shutter.emit(self.shutters[shutter_name])
                
            if widget.currentText() == "CLOSE":
                self.close_shutter.emit(self.shutters[shutter_name])
                
        self.can_continue.emit()
    
    def validate(self, recipe_table: QTableWidget, row: int):
        for col in range(1, recipe_table.columnCount()):
            widget = recipe_table.cellWidget(row, col)
            
            if not widget:
                logger.error(f"No widget found in column {col}, check ShutterAction")
                return False
            
            if not isinstance(widget, QComboBox):
                logger.error(f"No QComboBox found in column {col}, check ShutterAction")
                return False
            
            if widget.currentText() not in ["", "OPEN", "CLOSE"]:
                logger.error(f"Somehow, shutter dropdown in column {col} is not blank, OPEN, or CLOSE")
                return False
            
            return True
            
        
    def format_row(self, recipe_table: QTableWidget, row: int):
        for col in range(1, recipe_table.columnCount()):
            combo = QComboBox()
            combo.addItems(["", "OPEN", "CLOSE"])
            recipe_table.setCellWidget(row, col, combo)
        return