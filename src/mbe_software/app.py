import sys
from PySide6.QtWidgets import (
    QApplication, QMenu, QHeaderView,
    QComboBox, QTableWidgetItem, QTableWidget, 
    QPushButton, QFileDialog, QMessageBox,
    QLabel, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QMutex, QThread, Signal, QEvent, QObject
from PySide6.QtGui import QAction, QBrush, QColor
import pyqtgraph as pg
import numpy as np
import time
import logging
import os
import yaml
import serial
import csv
from collections import deque
from datetime import timedelta
from functools import partial
from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus import pymodbus_apply_logging_config

# Local imports
from mbe_software.utils.config import *
from mbe_software.devices import Shutter, Source, PressureGauge
from mbe_software.gui.widgets import (
    InputModalWidget,
    SourceControlWidget,
    SerialLogWidget,
    ModbusLogWidget,
    ShutterControlWidget
)
from mbe_software.gui.tabs import PressureTab
from mbe_software.utils import recipe, EmailAlert

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
# Disable pymodbus logging in favor of own logging
pymodbus_apply_logging_config(level=logging.CRITICAL)

logging.basicConfig(level=LOG_LEVEL_MAP[LOG_LEVEL])
logger = logging.getLogger(__name__)

main_ui_path = os.path.join(base_dir, 'gui', 'main.ui')

uiclass, baseclass = pg.Qt.loadUiType(main_ui_path)

SHUTTER_RECIPE_OPTIONS = (
    "",
    "OPEN",
    "CLOSE"
)

# Custom axis for scientific notation in plots
class ScientificAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [f"{v:.2e}" for v in values]
    
# Custom axis for time in plots
class TimeAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(timedelta(seconds=v)) for v in values]

# Apply to combo boxes to ignore scrolling, specifically in recipes
class WheelEventFilter(QObject):
    def eventFilter(self, obj, event):
        # Ignore wheel events
        if event.type() == QEvent.Wheel:
            return True  # event handled — stop propagation
        return super().eventFilter(obj, event)
WHEEL_FILTER = WheelEventFilter()

# Clear focus from focusable widgets when clicking elsewhere on the screen
class FocusClearingFilter(QObject):
    def eventFilter(self, obj, event):
        # On mouse click
        if event.type() == QEvent.MouseButtonPress:
            widget = QApplication.widgetAt(event.globalPos())
            if widget is None or widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
                focused_widget = QApplication.focusWidget()
                if focused_widget is not None:
                    focused_widget.clearFocus()
                    
        return super().eventFilter(obj, event)
CLEAR_FOCUS_FILTER = FocusClearingFilter()

class MainWindow(uiclass, baseclass):
    # Shutter signals
    open_shutter = Signal(Shutter)
    close_shutter = Signal(Shutter)
    send_shutter_command = Signal(Shutter, str) # Shutter reference, command

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # Change default window size
        self.resize(1400, 900)
        
        # Set application start time
        self.start_time = time.monotonic()
        
        # Configure email alerts
        self.alert = EmailAlert(ALERT_CONFIG['recipients'])
        
        # Apply focus clearing filter
        QApplication.instance().installEventFilter(CLEAR_FOCUS_FILTER)
        
        ##################
        # PRESSURE SETUP #
        ##################
        
        self.pressure_gauges: list[PressureGauge] = []
        
        for pressure_config in HARDWARE_CONFIG['devices']['pressure'].values():
            ser = serial.Serial(
                port=pressure_config['serial']['port'], 
                baudrate=pressure_config['serial']['baudrate'],
                timeout=0.1
                )
            
            mutex = QMutex()
            
            for i, gauge in enumerate(pressure_config['connections']):
                self.pressure_gauges.append(PressureGauge(
                    name=gauge['name'], 
                    address=gauge['address'],
                    idx=i,
                    ser=ser,
                    serial_mutex=mutex
                ))
            
        self.pressure_tab = PressureTab(self.pressure_gauges)
        
        ################
        # SOURCE SETUP #
        ################
        
        self.sources: list[Source] = []
        
        if PARAMETER_CONFIG['sources']['safety'] is None:
            PARAMETER_CONFIG['sources']['safety'] = {}
        safety_settings = PARAMETER_CONFIG['sources']['safety']
        for source_config in HARDWARE_CONFIG['devices']['sources'].values():
            logger.debug(source_config)
            logger.debug(source_config['serial']['port'])
            client = ModbusClient(
                port=source_config['serial']['port'], 
                baudrate=source_config['serial']['baudrate'],
                timeout=0.1
                )
            mutex = QMutex()
            self.sources.extend([Source(
                name=device['name'],
                device_id=device['device_id'],
                address_set=device['address_set'],
                safety_settings=safety_settings.get(device['name'], {}),
                client=client,
                serial_mutex=mutex
                ) for device in source_config['connections']])
        
        #################
        # SHUTTER SETUP #
        #################
        
        self.shutters: list[Shutter] = []
        
        for shutter_config in HARDWARE_CONFIG['devices']['shutters'].values():
            ser = serial.Serial(
                port=shutter_config['serial']['port'], 
                baudrate=shutter_config['serial']['baudrate'],
                timeout=0.1
                )
            
            serial_mutex = QMutex()
            
            self.shutters.extend([Shutter(
                name=shutter['name'], 
                address=shutter['address'], 
                ser=ser, 
                serial_mutex=serial_mutex
                ) for shutter in shutter_config['connections']])
        
        # Create dict for accessing shutters by name
        self.shutter_dict = {shutter.name: shutter for shutter in self.shutters}
        
        # Create thread
        self.shutter_thread = QThread()
        for shutter in self.shutters:
            shutter.moveToThread(self.shutter_thread)
            
        # The on_shutter_state_change function will handle any gui
        # changes that need to be made based on shutter state
        # The index of the shutter is baked to the connection in for reference later
        for i, shutter in enumerate(self.shutters):
            shutter.is_open_changed.connect(self.on_shutter_state_change)
            self.open_shutter.connect(shutter.open)
            self.close_shutter.connect(shutter.close)
            self.send_shutter_command.connect(shutter.send_custom_command)
        
        self.current_shutter_step = 0
        self.shutter_loop_step_timer = QTimer()
        self.shutter_loop_step_timer.setSingleShot(True)
        self.shutter_loop_step_timer.timeout.connect(self._trigger_next_shutter_step)
        
        # The two QElapsed timers remain accurate even if the program or system lags
        self.shutter_loop_time_elapsed_ms = 0
        self.shutter_step_time_elapsed_ms = 0
        self.shutter_loop_stopwatch_update_timer = QTimer()
        self.shutter_loop_stopwatch_update_timer.timeout.connect(self.update_shutter_loop_timers)
        
        ################
        # RECIPE SETUP #
        ################
        
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
        
        ###########################
        # SHUTTER TAB GUI CONFIG  #
        ###########################
        
        # Create shutter control widgets
        shutter_controls_layout = getattr(self, "shutter_controls_layout", None)
        self.shutter_controls: list[ShutterControlWidget] = []
        for shutter in self.shutters:
            widget = ShutterControlWidget(shutter.name, 6)
            self.shutter_controls.append(widget)
            shutter_controls_layout.addWidget(widget)
            
        # Connect shutter controls displays and buttons
        for i, controls in enumerate(self.shutter_controls):
            # Connect control buttons and set property
            controls.control_button.clicked.connect(self.on_shutter_control_button_click)
            controls.control_button.setProperty('idx', i)
            
            # Connect output buttons and set property
            controls.output_button.clicked.connect(self.on_shutter_output_button_click)
            controls.output_button.setProperty('idx', i)
            
            # Connect state buttons and set property
            for button in controls.step_state_buttons:
                button.clicked.connect(self.on_shutter_step_state_button_clicked)
                button.setProperty('idx', i)
            
        # Connect shutter disable all button
        shutter_control_off_all_button = getattr(self, "shutter_control_off_all")
        shutter_control_off_all_button.clicked.connect(self.on_shutter_control_off_all_click)
                
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
        
        ##############################
        # DIAGNOSTICS TAB GUI CONFIG #
        ##############################
        
        # Create serial log widgets
        serial_log_layout = getattr(self, "serial_log_layout", None)
        
        self.pressure_serial_log = SerialLogWidget(
            app=self,
            name="Pressure Gauges",
            device_names=[gauge.name for gauge in self.pressure_gauges]
        )
        serial_log_layout.addWidget(self.pressure_serial_log)
        
        self.source_serial_log = ModbusLogWidget(
            app=self,
            name="Sources",
            device_names=[source.name for source in self.sources]
        )
        serial_log_layout.addWidget(self.source_serial_log)
        
        self.shutter_serial_log = SerialLogWidget(
            app=self,
            name="Shutters",
            device_names=[shutter.name for shutter in self.shutters]
        )
        serial_log_layout.addWidget(self.shutter_serial_log)
        
        # Connect signals
        for gauge in self.pressure_gauges:
            gauge.new_serial_data.connect(self.pressure_serial_log.append_data)
            self.pressure_serial_log.send_command.connect(lambda _, cmd, g=gauge: g.send_custom_command(cmd))
        
        self.source_serial_log.read_modbus.connect(
            lambda name, address: self.source_dict[name].read_data_by_address(address)
        )
        self.source_serial_log.write_modbus.connect(
            lambda name, address, value: self.source_dict[name].write_data_by_address(address, value)
        )
        for source in self.sources:
            source.new_modbus_data.connect(self.source_serial_log.append_data)
        
        self.shutter_serial_log.send_command.connect(
            lambda name, cmd: self.send_shutter_command.emit(self.shutter_dict[name], cmd)
        )
        for shutter in self.shutters:
            shutter.new_serial_data.connect(self.shutter_serial_log.append_data)
        
        ###################
        # MISC GUI CONFIG #
        ###################
        
        # Set tab bar context menu
        tab_widget = getattr(self, "main_tabs", None)
        tab_widget.addTab(self.pressure_tab, "Pressure")
        tab_widget.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        tab_widget.tabBar().customContextMenuRequested.connect(self.on_tab_context_menu)
        
        # Store any popout windows
        self.popouts = getattr(self, "popouts", {})
        
        #################
        # START THREADS #
        #################

        self.source_thread.start()
        self.shutter_thread.start()

        # # Start polling for source data
        for source in self.sources:
            source.start_polling(500)
                
    ##################
    # SOURCE METHODS #
    ##################

    def on_new_source_process_variable(self, idx, pv):
        self.source_process_variable_data[idx].append((time.monotonic() - self.start_time, pv))
        
    def on_new_source_working_setpoint(self, idx, wsp):
        self.source_working_setpoint_data[idx].append((time.monotonic() - self.start_time, wsp))
        
    def on_source_setpoint_set_clicked(self, idx):
        setpoint = self.source_controls[idx].input_setpoint.value()
        self.sources[idx].set_setpoint(setpoint)
    
    def on_source_rate_limit_set_clicked(self, idx):
        rate_limit = self.source_controls[idx].input_rate_limit.value()
        logger.debug(f"VALUE OF BOX {self.source_controls[idx].input_rate_limit.value()}")
        self.sources[idx].set_rate_limit(rate_limit)
    
    def open_pid_input_modal(self, idx):
        source = self.sources[idx]
        pid_input_settings = ["PB", "TI", "TD"] # TODO: Ask what these should be
        current_values = source.get_pid()
        input_modal = InputModalWidget(
            pid_input_settings, 
            defaults=current_values, 
            window_title='PID Settings'
            )
            
        # On submission
        if input_modal.exec():
            values = input_modal.get_values()
            logger.debug(f"PID Input {idx} Submitted: {values}")
            pid_pb = values["PB"]
            pid_ti = values["TI"]
            pid_td = values["TD"]
            
            # Apply changes to source
            source.set_pid(
                pid_pb=pid_pb,
                pid_ti=pid_ti,
                pid_td=pid_td
                )
            
        # On cancellation
        else:
            logger.debug(f"PID Input {idx} Cancelled")
    
    def open_safe_rate_limit_input_modal(self, idx):
        source: Source = self.sources[idx]
        logger.debug(idx)
        safe_rate_limit_settings = ["Rate Limit (C/s)", "From (C)", "To (C)", "Max Setpoint (C)", "Stability Tolerance (C)"]
        current_values = list(source.get_rate_limit_safety())
        current_values.append(source.get_max_setpoint())
        current_values.append(source.get_stability_tolerance())
        input_modal = InputModalWidget(
            safe_rate_limit_settings,
            defaults=current_values,
            window_title='Safety Settings'
            )
        
        # On submission
        if input_modal.exec():
            values = input_modal.get_values()
            logger.debug(f"Safe Rate Limit Input {idx} Submitted: {values}")
            safe_rate_limit = values[safe_rate_limit_settings[0]]
            safe_from = values[safe_rate_limit_settings[1]]
            safe_to = values[safe_rate_limit_settings[2]]
            max_sp = values[safe_rate_limit_settings[3]]
            stability_tolerance = values[safe_rate_limit_settings[4]]
            
            # Apply changes to source
            source.set_rate_limit_safety(
                safe_rate_limit=safe_rate_limit,
                safe_rate_limit_from=safe_from,
                safe_rate_limit_to=safe_to
                )
            source.set_max_setpoint(max_sp)
            source.set_stability_tolerance(stability_tolerance)
            
            # Save changes to config since safety settings are not stored on-device
            # Ensure source entry exists
            logger.debug(PARAMETER_CONFIG)
            if source.name not in PARAMETER_CONFIG['sources']['safety']:
                PARAMETER_CONFIG['sources']['safety'][source.name] = {}
                
            config = PARAMETER_CONFIG['sources']['safety'][source.name]
            config["from"] = safe_from
            config["to"] = safe_to
            config["rate_limit"] = safe_rate_limit
            config["max_setpoint"] = max_sp
            config["stability_tolerance"] = stability_tolerance
            self.write_config_changes(config, parameter_config_path)
        
        # On cancellation
        else:
            logger.debug(f"Safe Rate Limit Input {idx} Cancelled")
            
    def on_source_color_change(self, idx, color: str):
        logger.debug(f"Changing source {idx} color to {color}")
        
        self.source_process_variable_curves[idx].setPen(color)
        
        # Save color change to config file
        THEME_CONFIG['source_tab']['colors'][idx] = color[1:] # Remove leading '#'
        self.write_config_changes(THEME_CONFIG, theme_config_path)

    def update_source_plot(self):
        # Update the plot with new full dataset
        max_time = 0 # To scale x axis later
        
        # Handle process variable data
        for i in range(len(self.source_process_variable_data)):
            if self.source_process_variable_data[i]:
                timestamps, values = zip(*self.source_process_variable_data[i])
                if timestamps[-1] > max_time:
                    max_time = timestamps[-1]
                self.source_process_variable_curves[i].setData(
                    np.array(timestamps),
                    np.array(values)
                )
        
        # Handle working setpoint data
        for i in range(len(self.source_working_setpoint_data)):
            curve = self.source_working_setpoint_curves[i]
            
            if curve.isVisible() and self.source_working_setpoint_data[i]:
                timestamps, values = zip(*self.source_working_setpoint_data[i])
                if timestamps[-1] > max_time:
                    max_time = timestamps[-1]
                curve.setData(
                    np.array(timestamps),
                    np.array(values)
                )

        # Optional: auto-scroll x-axis
        time_lock_checkbox = getattr(self, "source_plot_time_lock", None)
        time_delta_field = getattr(self, "source_plot_time_delta", None)
        time_delta = time_delta_field.value()
        if time_lock_checkbox.isChecked():
            # Show last time_delta seconds
            if max_time >= time_delta:
                self.source_graph_widget.setXRange(max(0, max_time - time_delta), max_time)
            else:
                self.source_graph_widget.setXRange(max(0, max_time - time_delta), time_delta)
            
            # Update cursor position
            if self._last_mouse_scene_pos is not None:
                self._update_source_cursor_from_scene_pos(self._last_mouse_scene_pos)
                
    def _on_source_mouse_moved(self, pos):
        self._last_mouse_scene_pos = pos
        self._update_source_cursor_from_scene_pos(pos)
        
    def _update_source_cursor_from_scene_pos(self, pos):
        """Track mouse location and show cursor line in the source plot."""

        # Hide everything first
        self.source_cursor_line.hide()
        self.source_cursor_label.hide()

        # Check if plot is currently under the mouse
        if not self.source_graph_widget.plotItem.vb.sceneBoundingRect().contains(pos):
            return

        target_vb = self.source_graph_widget.plotItem.vb
        
        # Convert scene → data coords
        mouse_point = target_vb.mapSceneToView(pos)
        x = mouse_point.x()

        self.source_cursor_line.setPos(x)
        self.source_cursor_line.show()

        # Label at top of plot
        time_str = str(timedelta(seconds=x))
        time_str = time_str[:time_str.index('.') + 3] # Truncate to two decimals
        (_, _), (ymin, ymax) = target_vb.viewRange()
        self.source_cursor_label.setText(f"t = {time_str}")
        self.source_cursor_label.setPos(x, ymax)
        self.source_cursor_label.show()
        
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
            button.setStyleSheet("""
                font: 48pt "Segoe UI";
                background-color: rgb(0, 255, 0);
                """)
            return
        
        # If loop is not running
        # TODO: Disable shutter loop GUI
        button.setText("Stop")
        button.setStyleSheet("""
            font: 48pt "Segoe UI";
            background-color: rgb(255, 0, 0);
            """)
        self.shutter_loop_start_time = time.monotonic()
        self.shutter_loop_stopwatch_update_timer.start(100)
        self._trigger_next_shutter_step()
        
    def _trigger_next_shutter_step(self):
        step = self.current_shutter_step
        
        # Increment loop count
        if step == 0:
            loop_count_display = getattr(self, "shutter_loop_count", None)
            count = loop_count_display.property("loop_count")
            loop_count_display.setProperty("loop_count", count + 1)
            loop_count_display.setText(f"{count + 1}")
        
        # Display current step
        step_display = getattr(self, "shutter_current_step", None)
        step_display.setText(f"{step + 1}") # Match user-facing number, not index
        
        # Store step start time
        self.shutter_step_start_time = time.monotonic()
        
        logger.debug(f"Triggering shutter loop step {step}")
        
        
        for i, controls in enumerate(self.shutter_controls):
            is_open = controls.step_state_buttons[step].property("is_open")
            if is_open:
                self.open_shutter.emit(self.shutters[i])
            else:
                self.close_shutter.emit(self.shutters[i])
        
        # Display elapsed time for state
        time_input_widget = getattr(self, f"step_time_{step}", None)
        state_time = int(time_input_widget.value() * 1000) # Sec to ms
        logger.debug(f"State time is {state_time}")
        
        # Increment step and check if max step has been reached
        max_step_input_widget = getattr(self, "max_loop_step", None)
        max_step = max_step_input_widget.value() - 1 # Indexing starts at 0, user-facing count starts at 1
        if self.current_shutter_step < max_step:
            self.current_shutter_step += 1
        else:
            self.current_shutter_step = 0
        
        # Start timer to trigger next step
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
        
    def on_shutter_step_state_button_clicked(self):
        button = self.sender()
        is_open = button.property('is_open')
            
        if is_open:
            button.setText("Closed")
            button.setProperty("is_open", False)
        else:
            button.setText("Open")
            button.setProperty("is_open", True)
        
        # Refresh button style
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
            
    def on_shutter_control_button_click(self):
        button: QPushButton = self.sender()
        is_on = button.property("is_on")
        idx = button.property("idx")
            
        if is_on:
            button.setText("OFF")
            button.setProperty("is_on", False)
            self.shutters[idx].disable()
        else:
            button.setText("ON")
            button.setProperty("is_on", True)
            self.shutters[idx].enable()
        
        # Refresh button style
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
    
    def on_shutter_control_off_all_click(self):
        for shutter in self.shutters:
            shutter.disable()
            
        for controls in self.shutter_controls:
            button = controls.control_button
            button.setProperty('is_on', False)
            button.setText("OFF")
            
            # Refresh button style
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
            
    def on_shutter_output_button_click(self):
        button: QPushButton = self.sender()
        is_open = button.property("is_open")
        idx = button.property("idx")
            
        if is_open:
            self.close_shutter.emit(self.shutters[idx])
        else:
            self.open_shutter.emit(self.shutters[idx])
            
        # Refresh button style
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
        
    def on_shutter_state_change(self, shutter: Shutter, is_open):
        for idx, s in enumerate(self.shutters):
            if s is not shutter:
                continue
            
            button = self.shutter_controls[idx].output_button
            button.setText("Open" if is_open else "Closed")
            button.setProperty('is_open', is_open)
        
            # Refresh button style
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
           
    ##################
    # RECIPE METHODS #
    ##################
    
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
    
    ################
    # MISC METHODS #
    ################
    
    def write_config_changes(self, config: dict, file_path):
        with open(file_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
            
    def time_since_start(self):
        return time.monotonic() - self.start_time
    
    def on_tab_context_menu(self, point):
        tab_widget = getattr(self, "main_tabs", None)
        tab_index = tab_widget.tabBar().tabAt(point)
        logger.debug(tab_index)
        
        if tab_index < 0:
            return # Didn't click a tab
        
        menu = QMenu()
        popout = QAction("Pop out tab", self)
        # Discard unneeded "checked" parameter and pass index
        popout.triggered.connect(lambda _, idx=tab_index: self.pop_out_tab(idx))
        menu.addAction(popout)
        
        # Show menu at global position
        menu.exec(tab_widget.tabBar().mapToGlobal(point))
    
    def pop_out_tab(self, tab_index):
        tab_widget = getattr(self, "main_tabs", None)
        tab = tab_widget.widget(tab_index)
        tab_text = tab_widget.tabText(tab_index)
        logger.debug(f"Stored tab info {(tab_index, tab, tab_text)}")
        
        # Remove tab to re-parent it
        tab_widget.removeTab(tab_index)

        # Change tab to a window
        tab.setWindowFlags(Qt.Window)
        tab.setParent(None)
        tab.setWindowTitle(tab_text)
        
        # Place back in main window on closing popout
        def on_close(event):
            tab.setWindowFlags(Qt.Widget)
            tab_widget.addTab(tab, tab.windowTitle())
            
        tab.closeEvent = on_close
            
        # Show the popped out tab
        tab.show()
        
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
        
app = QApplication(sys.argv)# 
window = MainWindow()
window.show()
app.exec()