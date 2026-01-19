from PySide6.QtWidgets import (
    QWidget, 
    QCheckBox, 
    QSpinBox, 
    QAbstractSpinBox, 
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QSpacerItem,
    QSizePolicy
    )
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont
from collections import deque
from functools import partial
from datetime import timedelta
import pyqtgraph as pg
import numpy as np
import logging
import time

# Local imports
from lattice.devices.source import Source
from lattice.gui.widgets import SourceControlWidget, InputModalWidget
from lattice.utils import config, START_TIME

logger = logging.getLogger(__name__)

# Custom axis for time in plots
class TimeAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [str(timedelta(seconds=v)) for v in values]

class SourceTab(QWidget):
    start_polling = Signal(Source, int) # Source, interval_ms
    stop_polling = Signal(Source) # Source
    set_setpoint = Signal(Source, float) # Source, setpoint
    set_rate_limit = Signal(Source, float) # Source, rate_limit
    set_safety = Signal(Source, float, float, float) # Source, rate_limit, from, to

    def __init__(self, sources: list[Source]):
        super().__init__()
        
        self.sources = sources
        
        #########
        # SETUP #
        #########

        # Initialize source data object
        self.process_variable_data = {}
        self.working_setpoint_data = {}
        for source in self.sources:
            self.process_variable_data[source] = deque(maxlen=7200) # 3 hours of data at default polling rate of 500ms
            self.working_setpoint_data[source] = deque(maxlen=7200)

        # Connect source process variable and working setpoint changes to data handling
        for source in self.sources:
            source.process_variable_changed.connect(self.on_new_process_variable)
            source.working_setpoint_changed.connect(self.on_new_working_setpoint)

        # Connect own signals
        for source in self.sources:
            self.start_polling.connect(source.start_polling)
            self.stop_polling.connect(source.stop_polling)
            self.set_setpoint.connect(source.set_setpoint)
            self.set_rate_limit.connect(source.set_rate_limit)
            self.set_safety.connect(source.set_rate_limit_safety)
            
        #########################
        # CONTROL WIDGET CONFIG #
        #########################

        # Create header labels
        self.temperature_label = QLabel("Temperature")
        self.setpoint_label = QLabel("Setpoint")
        self.working_setpoint_label = QLabel("Working Setpoint")
        self.rate_limit_label = QLabel("Rate Limit")
        self.new_setpoint_label = QLabel("New Setpoint")
        self.new_rate_limit_label = QLabel("New Rate Limit")

        # Create font
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        font.setUnderline(True)

        # Apply font to header labels
        self.temperature_label.setFont(font)
        self.setpoint_label.setFont(font)
        self.working_setpoint_label.setFont(font)
        self.rate_limit_label.setFont(font)
        self.new_setpoint_label.setFont(font)
        self.new_rate_limit_label.setFont(font)
        
        # Create the source control widgets
        self.control_widgets: list[SourceControlWidget] = []

        # Load config colors
        config_colors = config.THEME_CONFIG['source_tab']['colors']
        # Safety in case config is missing color values or has too many
        config_colors = (config_colors + ["#FFFFFF"] * len(self.sources))[:len(self.sources)]
        self.colors = dict(zip(self.sources, config_colors))
            
        for source in self.sources:
            color = self.colors[source]
            controls = SourceControlWidget(color=color)

            # Set source name labels
            controls.label.setText(source.get_name())
            
            # Connect color change methods
            controls.circle.color_changed.connect(partial(self.on_color_change, source))
            
            # Assign modals to PID and Safe Rate Limit buttons
            controls.pid_button.clicked.connect(partial(self.open_pid_input_modal, source))
            controls.safety_button.clicked.connect(partial(self.open_safe_rate_limit_input_modal, source))

            # Connect set controls
            controls.set_setpoint.connect(source.set_setpoint)
            controls.set_rate_limit.connect(source.set_rate_limit)
            
            # Connect variable displays
            source.process_variable_changed.connect(
                controls.update_process_variable
            )
            source.setpoint_changed.connect(
                controls.update_setpoint
            )
            source.working_setpoint_changed.connect(
                controls.update_working_setpoint
            )
            source.rate_limit_changed.connect(
                controls.update_rate_limit
            )

            # Connect working setpoint curve visibility checkboxes
            controls.plot_working_setpoint.stateChanged.connect(
                lambda state, source=source: self.working_setpoint_curves[source].setVisible(bool(state))
            )

            # Add controls to controls
            self.control_widgets.append(controls)
        
        ######################
        # PLOT WIDGET CONFIG #
        ######################

        # Configure source data plot
        self.data_plot = pg.PlotWidget()
        self.data_plot.setAxisItems({'bottom': TimeAxis('bottom')})
        self.data_plot.enableAutoRange(axis='x', enable=False)
        self.data_plot.enableAutoRange(axis='y', enable=True)
        self.data_plot.setXRange(0, 30)
        
        # Create curves
        self.process_variable_curves: dict[Source, pg.PlotCurveItem] = {}
        self.working_setpoint_curves: dict[Source, pg.PlotCurveItem] = {}
        for source in self.sources:
            print(self.colors[source])
            self.process_variable_curves[source] = self.data_plot.plot(pen=pg.mkPen(self.colors[source], width=2))
            self.working_setpoint_curves[source] = self.data_plot.plot(pen=pg.mkPen(self.colors[source], width=2, style=Qt.DashLine))
        
        # Clip rendered data to only what is currently visible
        for curve in list(self.process_variable_curves.values()) + list(self.working_setpoint_curves.values()):
            curve.setClipToView(True)
        
        # Hide working setpoint curves by default
        for curve in list(self.working_setpoint_curves.values()):
            curve.setVisible(False)
            
        # Add cursor tracking line
        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('y', width=1))
        self.cursor_label = pg.TextItem(color="y")

        self.data_plot.plotItem.addItem(self.cursor_line, ignoreBounds=True)
        self.data_plot.plotItem.addItem(self.cursor_label, ignoreBounds=True)

        self.cursor_line.hide()
        self.cursor_label.hide()
        
        # Connect mouse tracking
        self._last_mouse_scene_pos = None
        self.data_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
            
        # Start timer to update source data plot
        self.plot_update_timer = QTimer()
        self.plot_update_timer.timeout.connect(self.update_data_plot)
        self.plot_update_timer.start(1000)

        # Create time window lock widgets
        self.time_lock_checkbox = QCheckBox("Lock Time Window (seconds)")
        self.time_lock_checkbox.setChecked(True)
        self.time_lock_input = QSpinBox(minimum=0, maximum=100000, value=30)
        self.time_lock_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.time_lock_input.setAlignment(Qt.AlignmentFlag.AlignRight)

        #################
        # LAYOUT WIGETS #
        #################

        # Create main layout
        layout = QVBoxLayout()

        # Create header layout
        header_layout = QHBoxLayout()

        # Add header labels and spacers
        # Spacer widths are based on widths of control widget items with manual tuning
        header_layout.addSpacerItem(QSpacerItem(140, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))
        header_layout.addWidget(self.temperature_label)
        header_layout.addWidget(self.setpoint_label)
        header_layout.addWidget(self.working_setpoint_label)
        header_layout.addWidget(self.rate_limit_label)
        header_layout.addWidget(self.new_setpoint_label)
        header_layout.addSpacerItem(QSpacerItem(85, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))
        header_layout.addWidget(self.new_rate_limit_label)
        header_layout.addSpacerItem(QSpacerItem(85, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))
        header_layout.addSpacerItem(QSpacerItem(167, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))

        # Add header layout to controls layout
        layout.addLayout(header_layout)

        # Add control widgets
        for control_widget in self.control_widgets:
            layout.addWidget(control_widget)

        # Add plot
        layout.addWidget(self.data_plot)

        # Create plot controls layout
        plot_controls_layout = QHBoxLayout()

        # Add plot controls and spacer
        plot_controls_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        for widget in [
            self.time_lock_checkbox,
            self.time_lock_input
        ]:
            plot_controls_layout.addWidget(widget)

        # Add plot controls layout to main layout
        layout.addLayout(plot_controls_layout)

        # Apply main layout to self
        self.setLayout(layout)

        # Start polling for source data
        for source in self.sources:
            source.start_polling(2000)

    ##################
    # SOURCE METHODS #
    ##################

    def on_new_process_variable(self, pv: float, source: Source):
        self.process_variable_data[source].append((time.monotonic() - START_TIME, pv))
        
    def on_new_working_setpoint(self, wsp: float, source: Source):
        self.working_setpoint_data[source].append((time.monotonic() - START_TIME, wsp))
    
    def open_pid_input_modal(self, source: Source):
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
            logger.debug(f"PID Input {source.get_name()} Submitted: {values}")
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
            logger.debug(f"PID Input {source.get_name()} Cancelled")
    
    def open_safe_rate_limit_input_modal(self, source: Source):
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
            logger.debug(f"Safe Rate Limit Input {source.get_name()} Submitted: {values}")
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
            logger.debug(config.PARAMETER_CONFIG)
            if source.name not in config.PARAMETER_CONFIG['sources']['safety']:
                config.PARAMETER_CONFIG['sources']['safety'][source.name] = {}
                
            config = config.PARAMETER_CONFIG['sources']['safety'][source.name]
            config["from"] = safe_from
            config["to"] = safe_to
            config["rate_limit"] = safe_rate_limit
            config["max_setpoint"] = max_sp
            config["stability_tolerance"] = stability_tolerance
            config.PARAMETER_CONFIG.save()
        
        # On cancellation
        else:
            logger.debug(f"Safe Rate Limit Input {source.get_name()} Cancelled")
            
    def on_color_change(self, source: Source, color: str):        
        self.process_variable_curves[source].setPen(color)
        
        # Save color change to config file
        self.colors[source] = color
        config.THEME_CONFIG['source_tab']['colors'] = list(self.colors.values())
        config.THEME_CONFIG.save()

    def update_data_plot(self):
        # Update the plot with new full dataset
        max_time = 0 # To scale x axis later
        
        # Handle process variable data
        for source in self.sources:
            if self.process_variable_data[source]:
                timestamps, values = zip(*self.process_variable_data[source])
                if timestamps[-1] > max_time:
                    max_time = timestamps[-1]
                self.process_variable_curves[source].setData(
                    np.array(timestamps),
                    np.array(values)
                )
        
        # Handle working setpoint data
        for source in self.sources:
            curve = self.working_setpoint_curves[source]
            
            if curve.isVisible() and self.working_setpoint_data[source]:
                timestamps, values = zip(*self.working_setpoint_data[source])
                if timestamps[-1] > max_time:
                    max_time = timestamps[-1]
                curve.setData(
                    np.array(timestamps),
                    np.array(values)
                )

        # Optional: auto-scroll x-axis
        time_delta = self.time_lock_input.value()
        if self.time_lock_checkbox.isChecked():
            # Show last time_delta seconds
            if max_time >= time_delta:
                self.data_plot.setXRange(max(0, max_time - time_delta), max_time)
            else:
                self.data_plot.setXRange(max(0, max_time - time_delta), time_delta)
            
            # Update cursor position
            if self._last_mouse_scene_pos is not None:
                self._update_cursor_from_scene_pos(self._last_mouse_scene_pos)
                
    def _on_mouse_moved(self, pos):
        self._last_mouse_scene_pos = pos
        self._update_cursor_from_scene_pos(pos)
        
    def _update_cursor_from_scene_pos(self, pos):
        """Track mouse location and show cursor line in the source plot."""

        # Hide everything first
        self.cursor_line.hide()
        self.cursor_label.hide()

        # Check if plot is currently under the mouse
        if not self.data_plot.plotItem.vb.sceneBoundingRect().contains(pos):
            return

        target_vb = self.data_plot.plotItem.vb
        
        # Convert scene → data coords
        mouse_point = target_vb.mapSceneToView(pos)
        x = mouse_point.x()

        self.cursor_line.setPos(x)
        self.cursor_line.show()

        # Label at top of plot
        time_str = str(timedelta(seconds=x))
        time_str = time_str[:time_str.index('.') + 3] # Truncate to two decimals
        (_, _), (ymin, ymax) = target_vb.viewRange()
        self.cursor_label.setText(f"t = {time_str}")
        self.cursor_label.setPos(x, ymax)
        self.cursor_label.show()

# # Run as standalone app for testing
# if __name__ == "__main__":
#     # Override logging to DEBUG
#     logging.basicConfig(level=logging.DEBUG)
    
#     app = QApplication(sys.argv)
#     window = QWidget()
#     layout = QVBoxLayout()
    
#     names = ["Intro Gauge", "Ion Gauge", "Transfer Gauge"]
#     addresses = ["T1", "I1", "I2"]
#     mutex = QMutex()
#     gauges = []
    
#     for i in range(len(names)):
#         ser = MockPressureGauge(port="COM1", baudrate=9600, timeout=0.1)
#         gauges.append(PressureGauge(
#             name=names[i],
#             address=addresses[i],
#             idx=i,
#             ser=ser,
#             serial_mutex=mutex
#         ))
        
#     pressure_tab = PressureTab(gauges)
#     layout.addWidget(pressure_tab)
    
#     window.setLayout(layout)
#     window.setWindowTitle("Pressure Tab Widget")
#     window.show()
#     sys.exit(app.exec())