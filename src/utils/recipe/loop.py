import logging
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

# Local imports
from .recipe_action import RecipeAction

logger = logging.getLogger(__name__)

class LoopAction(RecipeAction):
    def __init__(self):
        super().__init__()
        self.start_step = None
        self.count_remaining = 0
        
    def run(self, recipe_table: QTableWidget, row: int):
        """
        Execute some logic on provided values
        """
        values = self.gather_values(recipe_table, row)
        count = int(values[0]) - 1 # don't loop an extra time following logic below
        self.start_step = row

        if self.count_remaining == 0:
            self.update_monitor_data.emit(str(1))
            self.count_remaining = count
        else:
            self.count_remaining -= 1
            self.update_monitor_data.emit(str(count - self.count_remaining + 1))
        
        self.can_continue.emit()
    
    def validate(self, recipe_table: QTableWidget, row: int):
        """
        Validate provided values
        """
        values = self.gather_values(recipe_table, row)
        count = values[0]
        try:
            int(count)
        except (ValueError, TypeError):
            logger.error(f"{count} is an invalid value.")
            return False
        
        if float(count) <= 0:
            logger.error(f"{count} is invalid.")
            return False
        
        return True