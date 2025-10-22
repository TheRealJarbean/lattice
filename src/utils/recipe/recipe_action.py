import logging
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

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