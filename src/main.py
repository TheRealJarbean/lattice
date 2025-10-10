import sys
from PySide6.QtWidgets import QApplication, QMenu, QHeaderView, QComboBox
from PySide6.QtCore import Qt, QTimer, QMutex
from PySide6.QtGui import QAction
import pyqtgraph as pg
import numpy as np
import time
import logging
import os
import yaml
import serial
from functools import partial
from pymodbus.client import ModbusSerialClient
from math import isclose

# Local imports
from devices.shutter import Shutter
from devices.source import Source
from devices.pressure import Pressure
from utils.serial_reader import SerialReader
from gui.input_modal_widget import InputModalWidget
from gui.source_control_widget import SourceControlWidget

# Set the log level based on env variable when program is run
# Determines which logging statements are printed to console
# Only level used at time of writing is DEBUG
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}

logging.basicConfig(level=LOG_LEVEL_MAP[LOG_LEVEL])
logger = logging.getLogger(__name__)

# Get the directory of this script and set other important directories
base_dir = os.path.dirname(os.path.abspath(__file__))
hardware_config_path = os.path.join(base_dir, 'config', 'hardware.yaml')
theme_config_path = os.path.join(base_dir, 'config', 'theme.yaml')
main_ui_path = os.path.join(base_dir, 'gui', 'main.ui')

# Load config files
with open(hardware_config_path, 'r') as f:
    hardware_config = yaml.safe_load(f)
    
with open(theme_config_path, 'r') as f:
    theme_config = yaml.safe_load(f)

uiclass, baseclass = pg.Qt.loadUiType(main_ui_path)

# Custom axis for scientific notation in plots
class ScientificAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [f"{v:.2e}" for v in values]

class MainWindow(uiclass, baseclass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # Set application start time
        self.start_time = time.time()
        
        ##################
        # PRESSURE SETUP #
        ##################
        pressure_config = hardware_config['devices']['pressure']
        ser = serial.Serial(
            port=pressure_config['serial']['port'], 
            baudrate=pressure_config['serial']['baudrate']
            )
        mutex = QMutex()
        
        self.pressure_reader = SerialReader(ser, mutex)
        self.pressure_reader.start()
        self.pressure_gauges = [Pressure(
            name=gauge['name'], 
            address=gauge['address'], 
            ser=ser, 
            mutex=mutex,
            ser_reader=self.pressure_reader
            ) for gauge in pressure_config['connections']]
        
        ################
        # SOURCE SETUP #
        ################
        # Sources are the only devices that have multiple physical connections
        # An empty list is created first, then each device on each different connection
        # is appended
        self.sources = []
        
        for source_config in hardware_config['devices']['sources'].values():
            client = ModbusSerialClient(
                port=source_config['serial']['port'], 
                baudrate=source_config['serial']['baudrate']
                )
            mutex = QMutex()
            self.sources.extend([Source(
                name=device['name'],
                device_id=device['device_id'],
                address_set=device['address_set'],
                client=client,
                mutex=mutex
                ) for device in source_config['connections']])
        
        #################
        # SHUTTER SETUP #
        #################
        shutter_config = hardware_config['devices']['shutters']
        ser = serial.Serial(
            port=shutter_config['serial']['port'], 
            baudrate=shutter_config['serial']['baudrate']
            )
        mutex = QMutex()
        
        self.shutter_reader = SerialReader(ser, mutex)
        self.shutter_reader.start()
        self.shutters = [Shutter(
            name=shutter['name'], 
            address=shutter['address'], 
            ser=ser, 
            mutex=mutex,
            ser_reader=self.shutter_reader
            ) for shutter in shutter_config['connections']]
        
        # The on_shutter_state_change function will handle any gui
        # changes that need to be made based on shutter state
        # The index of the shutter is baked to the connection in for reference later
        for i, shutter in enumerate(self.shutters):
            shutter.is_open.connect(partial(self.on_shutter_state_change, i))
        
        self.current_shutter_step = 0
        self.shutter_loop_step_timer = QTimer()
        self.shutter_loop_step_timer.setSingleShot(True)
        self.shutter_loop_step_timer.timeout.connect(self._trigger_next_shutter_step)
        
        # The two QElapsed timers remain accurate even if the program or system lags
        self.shutter_loop_time_elapsed_ms = 0
        self.shutter_step_time_elapsed_ms = 0
        self.shutter_loop_stopwatch_update_timer = QTimer()
        self.shutter_loop_stopwatch_update_timer.timeout.connect(self.update_shutter_loop_timers)

        ###########################
        # PRESSURE TAB GUI CONFIG #
        ###########################
        
        #########################
        # SOURCE TAB GUI CONFIG #
        #########################
        
        self.source_controls_layout = getattr(self, "source_controls", None)
        self.source_controls = []
        # mg_bulk and mg_cracker have separate entries for polling power values for some reason
        # This can be replaced with len(self.sources) if that is changed
        num_unique_sources = 10 
        
        # Create the source control widgets
        colors = theme_config['source_tab']['colors']
        for i in range(num_unique_sources):
            controls = SourceControlWidget(color=f"#{colors[i]}")
            self.source_controls.append(controls)
            self.source_controls_layout.addWidget(controls)

        # Set source name labels
        for i, controls in enumerate(self.source_controls):
            controls.label.setText(self.sources[i].name)
            
        # Connect color change methods
        for i, controls in enumerate(self.source_controls):
            controls.circle.color_changed.connect(partial(self.on_source_color_change, i))
            
        # Assign modals to PID and Safe Rate Limit buttons
        for i, controls in enumerate(self.source_controls):
            controls.pid_button.clicked.connect(partial(self.open_pid_input_modal, i))
            controls.safety_button.clicked.connect(partial(self.open_safe_rate_limit_input_modal, i))
            
        
        ###########################
        # SHUTTER TAB GUI CONFIG  #
        ###########################
        
        # Set shutter name fields
        for i in range(len(self.shutters)):
            shutter_name_label = getattr(self, f"shutter_name_{i}")
            shutter_name_label.setText(self.shutters[i].name)
            
        # Connect manual shutter control buttons to logic
        for i in range(len(self.shutters)):
            shutter_output_button = getattr(self, f"shutter_output_button_{i}")
            shutter_output_button.setProperty('shutter_idx', i)
            shutter_output_button.setProperty('is_open', False)
            shutter_output_button.clicked.connect(self.on_shutter_output_button_click)
        
        # Connect loop step shutter state buttons to logic
        max_steps = 6
        for i in range(max_steps):
            for j in range(len(self.shutters)):
                shutter_state_button = getattr(self, f"step_{i}_shutter_state_{j}")
                # By default, the button clicked signal passes a boolean "checked" value
                # the toggle_open_close_button_ui doesn't need this, so we pass a lambda with
                # an underscore to discard it and pass a reference to the button
                shutter_state_button.clicked.connect(lambda _, b=shutter_state_button: self.toggle_open_close_button(b))
                
        # Connect start/stop button to logic
        shutter_loop_toggle_button = getattr(self, "shutter_loop_toggle")
        shutter_loop_toggle_button.clicked.connect(self.on_toggle_loop_button_click)

        # Connect state time inputs
        num_states = 6
        for i in range(num_states):
            widget = getattr(self, f"state_time_{i}", None)
            if widget:
                widget.valueChanged.connect()
                
        #########################
        # RECIPE TAB GUI CONFIG #
        #########################
        self.recipe_table = getattr(self, "recipe_table", None)
        
        # Configure column resizing: first column stretches, others fixed
        self.recipe_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 11):
            self.recipe_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
            self.recipe_table.setColumnWidth(col, 100)
            
        # Label columns with source names
        column_names = ["Variable"] + [source.name for source in self.sources]
        self.recipe_table.setHorizontalHeaderLabels(column_names)
            
        # Center content when editing
        self.recipe_table.itemChanged.connect(lambda item: item.setTextAlignment(Qt.AlignCenter))
        
        # Add custom context menu for adding and removing steps
        self.recipe_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recipe_table.customContextMenuRequested.connect(self.on_recipe_row_context_menu)
        
        # Add dropdown to default row
        self.add_recipe_variable_dropdown(0)
        

        # Pressure data and plot initialization
        self.pressure_data = {
            "x" : [],
            "y" : [[], [], [], []]
        }
        self.pressure_graph_widget.plotItem.setAxisItems({'left': ScientificAxis('left')})
        self.pressure_graph_widget.enableAutoRange(axis='x', enable=False)
        self.pressure_graph_widget.enableAutoRange(axis='y', enable=False)
        self.pressure_graph_widget.setXRange(0, 30)
        self.pressure_graph_widget.setYRange(-1, 1) # TODO: change this
        # TODO: Maybe add color to config and create curve for each gauge
        self.pressure_curves = [
            self.pressure_graph_widget.plot(pen=pg.mkPen('r', width=2)),
            self.pressure_graph_widget.plot(pen=pg.mkPen('g', width=2)),
            self.pressure_graph_widget.plot(pen=pg.mkPen('b', width=2)),
            self.pressure_graph_widget.plot(pen=pg.mkPen('y', width=2))
        ]
        for curve in self.pressure_curves:
            curve.setClipToView(True)
            
        # Set up a timer to update the plot every 5 seconds
        self.timer = QTimer(self)
        self.timer.setInterval(25)  # milliseconds
        self.timer.timeout.connect(self.update_pressure_plot)
        self.timer.start()
    
    ####################
    # Pressure Methods #
    ####################
    
    def update_pressure_plot(self):
        # Simulate real-time data (you can replace this with sensor/API input)
        current_time = time.time() - self.start_time
        new_x = current_time
        new_y = [np.sin(new_x), np.sin(new_x + 90), np.sin(new_x + 180), np.sin(new_x + 270)] # sin wave
        # new_y = np.sin(current_time) + np.random.normal(scale=0.1)  # noisy sine wave

        # Display most recent values
        self.growth_display.setText(f"{new_y[0]:.2e}")
        self.flux_display.setText(f"{new_y[1]:.2e}")
        self.intro_display.setText(f"{new_y[2]:.2e}")
        self.thermocouple_display.setText(f"{new_y[3]:.2e}")

        # Append new data
        self.pressure_data['x'].append(new_x)
        for i in range(len(new_y)):
            self.pressure_data['y'][i].append(new_y[i])
        
        # Update the plot with new full dataset
        for i in range(len(self.pressure_curves)):
            self.pressure_curves[i].setData(np.array(
                self.pressure_data['x']),
                self.pressure_data['y'][i]
                )

        # Optional: auto-scroll x-axis
        time_lock_checkbox = getattr(self, "pressure_plot_time_lock", None)
        time_delta_field = getattr(self, "pressure_plot_time_delta", None)
        time_delta = time_delta_field.value()
        if time_lock_checkbox.isChecked():
            # Show last time_delta seconds
            if new_x >= time_delta:
                self.pressure_graph_widget.setXRange(max(0, new_x - time_delta), new_x)
            else:
                self.pressure_graph_widget.setXRange(max(0, new_x - time_delta), time_delta)
                
    ##################
    # SOURCE METHODS #
    ##################
    
    def open_pid_input_modal(self, idx):
        pid_input_settings = ["1", "2", "3"] # TODO: Ask what these should be
        input_modal = InputModalWidget(pid_input_settings, 'PID Settings')
        if input_modal.exec():
            logger.debug(f"PID Input {idx} Submitted: {input_modal.get_values()}" )
        else:
            logger.debug(f"PID Input {idx} Cancelled")
    
    def open_safe_rate_limit_input_modal(self, idx):
        safe_rate_limit_settings = ["From", "To", "Rate Limit"]
        input_modal = InputModalWidget(safe_rate_limit_settings, 'Safe Rate Limit Settings')
        if input_modal.exec():
            logger.debug(f"Safe Rate Limit Input {idx} Submitted: {input_modal.get_values()}")
        else:
            logger.debug(f"Safe Rate Limit Input {idx} Cancelled")
            
    def on_source_color_change(self, idx, color):
        logger.debug(f"Changing source {idx} color to {color}")
        
        # TODO: Update plot line color
        
        # Save color change to config file
        theme_config['source_tab']['colors'][idx] = color[1:] # Remove leading '#'
        self.write_theme_config_changes()
        
    ###################
    # SHUTTER METHODS #
    ###################
    
    def on_toggle_loop_button_click(self):
        button = self.sender()
        self.current_shutter_step = 0
        
        step_display = getattr(self, "shutter_current_step", None)
        step_display.setText("0")
        loop_count_display = getattr(self, "shutter_loop_count", None)
        loop_count_display.setProperty("loop_count", 0)
        loop_count_display.setText("0")
        
        # If loop is already running
        if self.shutter_loop_step_timer.isActive():
            self.shutter_loop_step_timer.stop()
            self.shutter_loop_stopwatch_update_timer.stop()
            self.reset_shutter_loop_timers()
            button.setText("Start")
            return
        
        # If loop is not running
        # TODO: Disable shutter loop GUI
        button.setText("Stop")
        self.shutter_loop_start_time = time.monotonic()
        self.shutter_loop_stopwatch_update_timer.start(100)
        self._trigger_next_shutter_step()
        
    def _trigger_next_shutter_step(self):
        step = self.current_shutter_step
        if step == 0:
            loop_count_display = getattr(self, "shutter_loop_count", None)
            count = loop_count_display.property("loop_count")
            loop_count_display.setProperty("loop_count", count + 1)
            loop_count_display.setText(f"{count + 1}")
        step_display = getattr(self, "shutter_current_step", None)
        step_display.setText(f"{step + 1}") # Match user-facing number, not index
        self.shutter_step_start_time = time.monotonic()
        logger.debug(f"Triggering shutter loop step {step}")
        for i in range(len(self.shutters)):
            shutter_state_widget = getattr(self, f"step_{step}_shutter_state_{i}")
            if shutter_state_widget.text() == "Open":
                self.shutters[i].open()
            else:
                self.shutters[i].close()
            
        time_input_widget = getattr(self, f"step_time_{step}", None)
        if time_input_widget is None:
            # TODO: Handle this error
            return
        state_time = int(time_input_widget.value() * 1000) # Sec to ms
        logger.debug(f"State time is {state_time}")
        
        max_step_input_widget = getattr(self, "max_loop_step", None)
        max_step = max_step_input_widget.value() - 1 # Indexing starts at 0, user-facing count starts at 1
        if self.current_shutter_step < max_step:
            self.current_shutter_step += 1
        else:
            self.current_shutter_step = 0
        
        if self.shutter_loop_step_timer.isActive():
            self.shutter_loop_step_timer.stop()
        self.shutter_loop_step_timer.start(state_time)
        
    def update_shutter_loop_timers(self):
        loop_seconds = time.monotonic() - self.shutter_loop_start_time
        step_seconds = time.monotonic() - self.shutter_step_start_time
        
        loop_timer = getattr(self, "shutter_loop_time_elapsed", None)
        step_timer = getattr(self, "shutter_loop_time_in_step", None)
        
        loop_timer.setText(f"{loop_seconds:04.1f} s")
        step_timer.setText(f"{step_seconds:04.1f} s")
        
    def reset_shutter_loop_timers(self):
        loop_timer = getattr(self, "shutter_loop_time_elapsed", None)
        step_timer = getattr(self, "shutter_loop_time_in_step", None)
        
        loop_timer.setText(f"{0:04.1f} s")
        step_timer.setText(f"{0:04.1f} s")
        
    def toggle_open_close_button(self, button, is_open=None):
        if is_open is None:
            is_open = button.property('is_open')
            
        if is_open:
            button.setText("Closed")
            button.setProperty("is_open", not is_open)
            button.setStyleSheet("""
                background-color: rgb(255, 0, 0);
                border: 1px solid black;                     
            """)
        else:
            button.setText("Open")
            button.setProperty("is_open", not is_open)
            button.setStyleSheet("""
                background-color: rgb(0, 255, 0);
                border: 1px solid black;                     
            """)
            
    def on_shutter_output_button_click(self):
        button = self.sender()
        shutter_idx = button.property('shutter_idx')
        is_open = button.property('is_open')
        
        if is_open:
            self.shutters[shutter_idx].close()
            button.setProperty('is_open', False)
        else:
            self.shutters[shutter_idx].open()
            button.setProperty('is_open', True)
            
    def on_shutter_state_change(self, shutter_idx, is_open):
        shutter_output_button = getattr(self, f"shutter_output_button_{shutter_idx}")
        self.toggle_open_close_button(shutter_output_button, not is_open) # Call function as if button was clicked in opposite state
                
    ##################
    # RECIPE METHODS #
    ##################
    
    def on_recipe_row_context_menu(self, point):
        row = self.recipe_table.rowAt(point.y())
        if row == -1:
            return # No row under the cursor
        
        # Create context menu
        menu = QMenu(self)
        
        # Add row above action
        add_above = QAction("Add step above", self)
        add_above.triggered.connect(lambda: self.insert_recipe_row(row))
        menu.addAction(add_above)
        
        # Add row below action
        add_below = QAction("Add step below", self)
        add_below.triggered.connect(lambda: self.insert_recipe_row(row + 1))
        menu.addAction(add_below)
        
        # Delete row action
        # Don't let user delete only row
        if self.recipe_table.rowCount() != 1:
            delete_row = QAction("Delete step", self)
            delete_row.triggered.connect(lambda: self.recipe_table.removeRow(row))
            menu.addAction(delete_row)
        
        # Show menu at global position
        menu.exec(self.recipe_table.viewport().mapToGlobal(point))
        
    def add_recipe_variable_dropdown(self, row):
        combo = QComboBox()
        combo.addItems([
            "SHUTTER",
            "RAMP_RATE",
            "SETPOINT",
            "WAIT_UNTIL_SETPOINT",
            "WAIT_FOR_SECONDS",
        ])
        self.recipe_table.setCellWidget(row, 0, combo)
        
    def insert_recipe_row(self, row):
        self.recipe_table.insertRow(row)
        self.add_recipe_variable_dropdown(row)
        
    # def on_recipe_start_button_click(self):
    #     button = self.sender()
    #     self.current_recipe_step = 0
        
    #     step_display = getattr(self, "shutter_current_step", None)
    #     step_display.setText("0")
    #     loop_count_display = getattr(self, "shutter_loop_count", None)
    #     loop_count_display.setProperty("loop_count", 0)
    #     loop_count_display.setText("0")
        
    #     # If loop is already running
    #     if self.recipe_loop_step_timer.isActive():
    #         self.shutter_loop_step_timer.stop()
    #         self.shutter_loop_stopwatch_update_timer.stop()
    #         self.reset_shutter_loop_timers()
    #         button.setText("Start")
    #         return
        
    #     # If loop is not running
    #     # TODO: Disable shutter loop GUI
    #     button.setText("Stop")
    #     self.shutter_loop_start_time = time.monotonic()
    #     self.shutter_loop_stopwatch_update_timer.start(100)
    #     self._trigger_next_shutter_step()
        
    # def _trigger_next_recipe_step(self):
    #     step = self.current_shutter_step
    #     if step == 0:
    #         loop_count_display = getattr(self, "shutter_loop_count", None)
    #         count = loop_count_display.property("loop_count")
    #         loop_count_display.setProperty("loop_count", count + 1)
    #         loop_count_display.setText(f"{count + 1}")
    #     step_display = getattr(self, "shutter_current_step", None)
    #     step_display.setText(f"{step + 1}") # Match user-facing number, not index
    #     self.shutter_step_start_time = time.monotonic()
    #     logger.debug(f"Triggering shutter loop step {step}")
    #     for i in range(len(self.shutters)):
    #         shutter_state_widget = getattr(self, f"step_{step}_shutter_state_{i}")
    #         if shutter_state_widget.text() == "Open":
    #             self.shutters[i].open()
    #         else:
    #             self.shutters[i].close()
            
    #     time_input_widget = getattr(self, f"step_time_{step}", None)
    #     if time_input_widget is None:
    #         # TODO: Handle this error
    #         return
    #     state_time = int(time_input_widget.value() * 1000) # Sec to ms
    #     logger.debug(f"State time is {state_time}")
        
    #     max_step_input_widget = getattr(self, "max_loop_step", None)
    #     max_step = max_step_input_widget.value() - 1 # Indexing starts at 0, user-facing count starts at 1
    #     if self.current_shutter_step < max_step:
    #         self.current_shutter_step += 1
    #     else:
    #         self.current_shutter_step = 0
        
    #     if self.shutter_loop_step_timer.isActive():
    #         self.shutter_loop_step_timer.stop()
    #     self.shutter_loop_step_timer.start(state_time)
    
    ################
    # MISC METHODS #
    ################
    
    def write_theme_config_changes(self):
        with open(theme_config_path, "w") as f:
            yaml.dump(theme_config, f, default_flow_style=False)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()