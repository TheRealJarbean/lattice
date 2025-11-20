import logging
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtGui import QBrush, QColor

# Local imports
from .recipe_action import RecipeAction
from .loop import LoopAction

logger = logging.getLogger(__name__)

class EndLoopAction(RecipeAction):
    def __init__(self, loop_action: LoopAction, set_recipe_step_callback):
        super().__init__()
        self.loop_action = loop_action
        self.set_recipe_step = set_recipe_step_callback
        
    def run(self, recipe_table: QTableWidget, row: int):
        """
        Execute some logic on provided values
        """
        if self.loop_action.count_remaining == 0:
            self.can_continue.emit()
            return
        
        self.remove_style(recipe_table, self.loop_action.start_step, row)
        self.set_recipe_step(self.loop_action.start_step)
        self.can_continue.emit()
        
    
    def validate(self, recipe_table: QTableWidget, row: int):
        """
        Validate provided values
        """
        # TODO: Ensure row is empty? Or just format disabled, check that it follows a LOOP
        pass

    def remove_style(self, recipe_table: QTableWidget, start_row: int, end_row: int):
        cols = recipe_table.columnCount()
        for row in range(start_row, end_row + 1): # Include end row
            for col in range(1, cols): # Ignore first column
                item: QTableWidgetItem = recipe_table.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    recipe_table.setItem(row, col, item)

                # Set BG Color
                item.setBackground(QBrush(QColor("#ffffff")))