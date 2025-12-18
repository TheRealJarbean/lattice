from PySide6.QtWidgets import (
    QWidget,
    QTableWidget,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QComboBox,
    QPushButton,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox
    )
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtGui import QAction, QColor, QBrush
import csv
import logging

# Local imports
from mbe_software.devices import PressureGauge, Source, Shutter
from mbe_software.utils import recipe
from .ui_recipe_tab import Ui_RecipeTab

logger = logging.getLogger(__name__)

SHUTTER_RECIPE_OPTIONS = (
    "",
    "OPEN",
    "CLOSE"
)

# Apply to combo boxes to ignore scrolling
class WheelEventFilter(QObject):
    def eventFilter(self, obj, event):
        # Ignore wheel events
        if event.type() == QEvent.Wheel:
            return True  # event handled — stop propagation
        return super().eventFilter(obj, event)
WHEEL_FILTER = WheelEventFilter()

class RecipeTab(QWidget, Ui_RecipeTab):
    def __init__(self, gauges: PressureGauge, sources: Source, shutters: Shutter):
        super().__init__()
        self.setupUi(self)

        self.gauges = gauges
        self.sources = sources
        self.shutters = shutters
        self.shutter_dict = {shutter.name: shutter for shutter in self.shutters}
        self.source_dict = {source.name: source for source in self.sources}

        #########
        # SETUP #
        #########

        # Set recipe attributes
        self.is_recipe_running = False
        self.is_recipe_paused = False
        self.current_recipe_step = 0
        self.current_recipe_action = None

        # Map recipe actions
        self.loop_action = recipe.LoopAction() # Need a reference for end loop action
        self.recipe_action_map: dict[str, recipe.RecipeAction] = {
            "RATE_LIMIT": recipe.RateLimitAction(self.source_dict),
            "SHUTTER": recipe.ShutterAction(self.shutter_dict),
            "SETPOINT": recipe.SetpointAction(self.source_dict),
            "WAIT_UNTIL_SETPOINT": recipe.WaitUntilSetpointAction(self.source_dict),
            "WAIT_UNTIL_SETPOINT_STABLE": recipe.WaitUntilSetpointStableAction(self.source_dict),
            "WAIT_FOR_TIME_SECONDS": recipe.WaitForSecondsAction(),
            "LOOP": self.loop_action,
            "END_LOOP": recipe.EndLoopAction(self.loop_action, lambda step: setattr(self, "current_recipe_step", step))
        }
        
        for action in self.recipe_action_map.values():
            action.can_continue.connect(self._trigger_next_recipe_step)
        
        # Copied rows data
        self.copied_rows_data = None

        ##############
        # GUI CONFIG #
        ##############

        self.recipe_table: QTableWidget = getattr(self, "recipe_table", None)

        # Match number of columns to number of sources plus one for action column
        self.recipe_table.setColumnCount(1 + len(self.sources))
        
        # Configure column resizing: first column fixed, others stretch
        self.recipe_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.recipe_table.setColumnWidth(0, 200)
        for col in range(1, self.recipe_table.columnCount()):
            self.recipe_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
            
        # Label columns with source names
        column_names = ["Action"] + [source.get_name() for source in self.sources]
        self.recipe_table.setHorizontalHeaderLabels(column_names)
            
        # Center content when editing
        self.recipe_table.itemChanged.connect(lambda item: item.setTextAlignment(Qt.AlignCenter))
        
        # Add custom context menu for adding and removing steps
        self.recipe_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recipe_table.customContextMenuRequested.connect(self.on_recipe_row_context_menu)
        self.recipe_table.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.recipe_table.verticalHeader().customContextMenuRequested.connect(self.on_recipe_row_context_menu)
        
        # Add dropdown to default row
        self.add_recipe_action_dropdown(0)
        
        # Connect start button
        recipe_start_button = getattr(self, "recipe_start", None)
        recipe_start_button.clicked.connect(self.recipe_toggle_running)
        
        # Connect pause button
        recipe_pause_button = getattr(self, "recipe_pause", None)
        recipe_pause_button.clicked.connect(self.recipe_toggle_pause)
        
        # Connect add step button
        add_step_button = getattr(self, "add_recipe_step", None)
        add_step_button.clicked.connect(lambda: self.recipe_insert_row(self.recipe_table.rowCount()))
        
        # Connect save button
        recipe_save_button = getattr(self, "recipe_save", None)
        recipe_save_button.clicked.connect(self.recipe_save_to_csv)
        
        # Connect load button
        recipe_load_button = getattr(self, "recipe_load", None)
        recipe_load_button.clicked.connect(self.recipe_load_from_csv)
        
        # Connect new recipe button
        recipe_new_button = getattr(self, "new_recipe", None)
        recipe_new_button.clicked.connect(self.recipe_reset)
        
        # Connect time monitor label and data
        self.recipe_time_monitor_label: QLabel = getattr(self, "recipe_time_monitor_label", None)
        self.recipe_time_monitor_data: QLineEdit = getattr(self, "recipe_time_monitor_data", None)

        self.recipe_action_map["WAIT_FOR_TIME_SECONDS"].update_monitor_data.connect(self.recipe_time_monitor_data.setText)
        
        # Connect loop monitor label and data
        self.recipe_loop_monitor_label: QLabel = getattr(self, "recipe_loop_monitor_label", None)
        self.recipe_loop_monitor_data: QLineEdit = getattr(self, "recipe_loop_monitor_data", None)

        self.recipe_action_map["LOOP"].update_monitor_data.connect(self.recipe_loop_monitor_data.setText)

    def on_recipe_row_context_menu(self, point):
        row = self.recipe_table.rowAt(point.y())
        if row == -1:
            return # No row under the cursor
        
        selected_rows = set(idx.row() for idx in self.recipe_table.selectedIndexes())
        selected_rows.add(row) # Ensure currently clicked row is included
        
        # Create context menu
        menu = QMenu(self)
        
        # Add row above action
        add_above = QAction("Add step above", self)
        add_above.triggered.connect(lambda: self.recipe_insert_row(row))
        menu.addAction(add_above)
        
        # Add row below action
        add_below = QAction("Add step below", self)
        add_below.triggered.connect(lambda: self.recipe_insert_row(row + 1))
        menu.addAction(add_below)
        
        # Delete row action
        # Don't let user delete only row
        if self.recipe_table.rowCount() != 1:
            delete_rows = QAction("Delete step(s)", self)
            delete_rows.triggered.connect(lambda: self.recipe_remove_rows(selected_rows))
            menu.addAction(delete_rows)
            
        # Copy rows action
        if selected_rows:
            copy_rows = QAction("Copy step(s)", self)
            copy_rows.triggered.connect(lambda: self.recipe_copy_selected_rows(selected_rows))
            menu.addAction(copy_rows)
        
        # Paste rows action
        if self.copied_rows_data:
            paste_rows = QAction("Paste step(s)", self)
            paste_rows.triggered.connect(lambda: self.recipe_paste_rows(row + 1))
            menu.addAction(paste_rows)
        
        # Show menu at global position
        menu.exec(self.recipe_table.viewport().mapToGlobal(point))
        
    def add_recipe_action_dropdown(self, row):
        combo = QComboBox()
        combo.addItems(self.recipe_action_map.keys())
        combo.installEventFilter(WHEEL_FILTER)
        combo.currentIndexChanged.connect(self.recipe_on_action_changed)
        self.recipe_table.setCellWidget(row, 0, combo)
        
    def recipe_on_action_changed(self):
        sender: QComboBox = self.sender()
        sender_row = None
        
        # Figure out which row the sender is in
        col = 0
        for row in range(self.recipe_table.rowCount()):
            if self.recipe_table.cellWidget(row, col) is sender:
                sender_row = row
                break
                
        if sender_row is None:
            logger.error("Couldn't find row of action selection")
            return
        
        action = sender.currentText()
        self.recipe_action_map[action].format_row(self.recipe_table, sender_row)
        
    def recipe_insert_row(self, row):
        self.recipe_table.insertRow(row)
        self.add_recipe_action_dropdown(row)
        
    def recipe_remove_rows(self, selected_rows):
        # Start with higher indexes so lower indexes don't change
        for row in sorted(selected_rows, reverse=True): 
            self.recipe_table.removeRow(row)
        
    def recipe_toggle_running(self):
        toggle_button: QPushButton = getattr(self, "recipe_start", None)
        pause_button: QPushButton = getattr(self, "recipe_pause", None)
        self.current_recipe_step = 0
        
        # If recipe is already running
        if self.is_recipe_running:
            self.is_recipe_running = False
            self.is_recipe_paused = False
            
            # If current step is a wait action, stop it
            if isinstance(self.current_recipe_action, recipe.WaitAction):
                self.current_recipe_action.stop()
                
            # Reset current recipe action
            self.current_recipe_action = None
            
            # Return all rows to white
            for row in range(self.recipe_table.rowCount()):
                self._style_row(self.recipe_table, row, "#FFFFFF")
            
            # Reset start recipe button
            toggle_button.setText("Start Recipe")
            toggle_button.setStyleSheet("""
                background-color: rgb(0, 255, 0);
                """) 
            
            # Reset pause recipe button
            pause_button.setText("Pause")
            pause_button.setStyleSheet("""
                background-color: rgb(255, 255, 0);
                """)
            
            # Clear monitor
            self.recipe_time_monitor_data.setText("")
            self.recipe_loop_monitor_data.setText("")
            
            self.recipe_table.setEnabled(True)
            return
        
        # If recipe is not running
        
        # Disable recipe table editing
        self.recipe_table.setEnabled(False)

        # Override disabled row styling
        for row in range(self.recipe_table.rowCount()):
            self._style_row(self.recipe_table, row)
        
        # Change start button to stop
        toggle_button.setText("Stop Recipe")
        toggle_button.setStyleSheet("""
            background-color: rgb(255, 0, 0);
            """) 
        
        self.is_recipe_running = True
        self._trigger_next_recipe_step()
        
    def _trigger_next_recipe_step(self): 
        step = self.current_recipe_step
        
        # If recipe is over, toggle recipe off
        if step == (self.recipe_table.rowCount()):
            self.recipe_toggle_running()
            return
        
        # Style currently running step yellow, previous step green
        self._style_row(self.recipe_table, step, "#FDF586")
        if step != 0:
            self._style_row(self.recipe_table, step - 1, "#75FF75")
        
        # Get the selected action
        combo_widget = self.recipe_table.cellWidget(step, 0)
        if combo_widget is None:
            logger.warning('No widget found in recipe column 0 row {step}, can be safely ignored on startup')
            return
        selection = combo_widget.currentText()
        
        # Increment recipe step
        # This is done before executing the current action in case it executes
        # so fast the step number becomes desynced
        self.current_recipe_step += 1
        
        # Run current action
        self.current_recipe_action = self.recipe_action_map[selection]
        self.current_recipe_action.run(self.recipe_table, step)
            
    def recipe_toggle_pause(self):
        if not self.is_recipe_running:
            return
        
        pause_button: QPushButton = getattr(self, "recipe_pause", None)
        
        if self.is_recipe_paused:
            logger.debug("Unpausing recipe")
            
            # This should always be true
            if not isinstance(self.current_recipe_action, recipe.WaitAction):
                logger.error("The current step somehow changed between pausing and resuming.")
                self.recipe_toggle_running()
                return
            
            # Resume current action
            self.current_recipe_action.resume()
            
            # Style pause button
            pause_button.setText("Pause")
            pause_button.setStyleSheet("""
                background-color: rgb(255, 255, 0);
                """)
            
            self.is_recipe_paused = False
            return
        
        # Check if current action is pausable
        if not isinstance(self.current_recipe_action, recipe.WaitAction):
            # This will trigger most commonly when clicking the pause button
            # just as a wait is ending
            logger.debug("Step is currently executing, try pausing again on a wait step.")
            return
        
        # Pause current action
        self.current_recipe_action.pause()
        
        # Style resume button
        pause_button.setText("Resume")
        pause_button.setStyleSheet("""
            background-color: rgb(0, 255, 0);
            """)
        
        self.is_recipe_paused = True
        
    def recipe_copy_selected_rows(self, selected_rows):
        self.copied_rows_data = []
        for i, row in enumerate(selected_rows):
            self.copied_rows_data.append([])
            for col in range(self.recipe_table.columnCount()):
                widget = self.recipe_table.cellWidget(row, col)
                if widget:
                    self.copied_rows_data[i].append(widget)
                    continue
                
                item = self.recipe_table.item(row, col)
                text = item.text() if item else None
                self.copied_rows_data[i].append(text)
    
    def recipe_paste_rows(self, start_row):
        if not self.copied_rows_data:
            return
        
        for i in range(len(self.copied_rows_data)):
            self.recipe_table.insertRow(start_row + i)
            for col, item in enumerate(self.copied_rows_data[i]):
                if not item:
                    continue
                
                if isinstance(item, (str, int, float)):
                    self.recipe_table.setItem(start_row + i, col, QTableWidgetItem(item))
                    continue
                
                if isinstance(item, QComboBox):
                    new_widget = QComboBox()
                    new_widget.installEventFilter(WHEEL_FILTER)
                    # Copy items
                    for j in range(item.count()):
                        new_widget.addItem(item.itemText(j))
                    new_widget.setCurrentIndex(item.currentIndex())
                
                if not new_widget:
                    logger.error("Something went wrong when copying rows")
                    for j in reversed(range(i)):
                        self.recipe_table.removeRow(start_row + j)
                    return
                
                self.recipe_table.setCellWidget(start_row + i, col, new_widget)
                
    def recipe_save_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            None, "Save CSV", "", "CSV files (*.csv);;All Files (*)"
        )
        
        if not path:
            return # User cancelled
        
        with open(path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write headers
            headers = [self.recipe_table.horizontalHeaderItem(col).text()
                       for col in range(self.recipe_table.columnCount())]
            writer.writerow(headers)
            
            # Write table data
            for row in range(self.recipe_table.rowCount()):
                row_data = []
                
                for col in range(self.recipe_table.columnCount()):
                    widget = self.recipe_table.cellWidget(row, col)
                    if isinstance(widget, QComboBox):
                        row_data.append(widget.currentText())
                        continue
                    
                    item = self.recipe_table.item(row, col)
                    if item:
                        row_data.append(item.text())
                        continue
                        
                    row_data.append("")
                        
                writer.writerow(row_data)
                
    def recipe_load_from_csv(self):
        msg = "Loading recipe will delete all current steps. Do you want to continue?"
        if not self.confirm_action(msg):
            return
        
        path, _ = QFileDialog.getOpenFileName(
            None, "Open CSV", "", "CSV files (*.csv);;All Files (*)"
        )
        
        if not path:
            return # User cancelled
        
        with open(path, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
            
        if not rows:
            QMessageBox.warning(None, "Empty File", "The selected CSV file is empty.")
            return
        
        # Extract header row from CSV
        csv_headers = rows[0]
        
        # Get headers from existing recipe table
        recipe_headers = [
            self.recipe_table.horizontalHeaderItem(col).text()
            for col in range(self.recipe_table.columnCount())
        ]
        
        # Compare headers
        # if headers are different csv was likely saved with a different hardware config
        if csv_headers != recipe_headers:
            QMessageBox.critical(
                None,
                "Header Mismatch",
                f"""
                The CSV headers do not match the expected table headers. 
                Was the CSV saved with a different hardware config?\n\n
                CSV: {csv_headers}\n
                Expected: {recipe_headers}
                """
            )
            return
                    
        # Clear existing steps
        for row in reversed(range(self.recipe_table.rowCount())):
            self.recipe_table.removeRow(row)
            
        # Load data
        data_rows = rows[1:]
        self.recipe_table.setRowCount(len(data_rows))
        
        for row, row_data in enumerate(data_rows):
            for col, cell_text in enumerate(row_data):
                # Handle action column
                if col == 0:
                    actions = list(self.recipe_action_map.keys())
                    if cell_text not in actions:
                        QMessageBox.critical(
                            None,
                            "Unknown Action",
                            f"""
                            Error loading recipe, unknown action\n\n
                            CSV: {cell_text}\n
                            Valid Actions: {actions}
                            """
                        )
                        return
                    
                    combo = QComboBox()
                    combo.installEventFilter(WHEEL_FILTER)
                    combo.addItems(actions)
                    selected_action_idx = actions.index(cell_text)
                    combo.setCurrentIndex(selected_action_idx)
                    
                    self.recipe_table.setCellWidget(row, col, combo)
                    continue
                
                # Special case for shutter action
                if self.recipe_table.cellWidget(row, 0).currentText() == "SHUTTER":
                    if cell_text not in SHUTTER_RECIPE_OPTIONS:
                        QMessageBox.critical(
                            None,
                            "Unknown Shutter State",
                            f"""
                            Error loading recipe, unknown shutter state\n\n
                            CSV: {cell_text}\n
                            Valid States: {SHUTTER_RECIPE_OPTIONS}
                            """
                        )
                        return
                    
                    combo = QComboBox()
                    combo.installEventFilter(WHEEL_FILTER)
                    combo.addItems(SHUTTER_RECIPE_OPTIONS)
                    selected_option = SHUTTER_RECIPE_OPTIONS.index(cell_text)
                    combo.setCurrentIndex(selected_option)
                    
                    self.recipe_table.setCellWidget(row, col, combo)
                    continue
                    
                item = QTableWidgetItem(cell_text)
                self.recipe_table.setItem(row, col, item)
    
    def recipe_reset(self):
        msg = "Creating a new recipe will delete all current steps. Do you want to continue?"
        if not self.confirm_action(msg):
            return
        
        # Remove all rows
        for row in reversed(range(self.recipe_table.rowCount())):
            self.recipe_table.removeRow(row)
        
        # Add one new row
        self.recipe_insert_row(0)

    def _style_row(self, table, row, bg_color="#FFFFFF"):
        cols = table.columnCount()
        for col in range(1, cols): # Ignore first column
            item: QTableWidgetItem = table.item(row, col)
            if item is None:
                item = QTableWidgetItem()
                table.setItem(row, col, item)

            # Set BG Color
            item.setBackground(QBrush(QColor(bg_color)))

    def confirm_action(self, msg: str):
        reply = QMessageBox.question(
            None,
            "Confirm Action",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default selected button
        )

        if reply == QMessageBox.Yes:
            return True
        else:
            return False