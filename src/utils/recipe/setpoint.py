import logging
from PySide6.QtWidgets import QTableWidget

# Local imports
from .recipe_action import RecipeAction
from devices.source import Source

logger = logging.getLogger(__name__)

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