import logging
from PySide6.QtCore import Signal, QEvent, QObject
from PySide6.QtWidgets import QTableWidget, QComboBox

# Local imports
from .recipe_action import RecipeAction
from devices.shutter import Shutter

logger = logging.getLogger(__name__)

# Discard scroll wheel events completely
class WheelEventFilter(QObject):
    def eventFilter(self, obj, event):
        # Ignore wheel events
        if event.type() == QEvent.Wheel:
            return True  # event handled — stop propagation
        return super().eventFilter(obj, event)
WHEEL_FILTER = WheelEventFilter()

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
             
    def format_cell(self, recipe_table: QTableWidget, col: int, row: int):
        combo = QComboBox()
        combo.installEventFilter(WHEEL_FILTER)
        combo.addItems(["", "OPEN", "CLOSE"])
        recipe_table.setCellWidget(row, col, combo)