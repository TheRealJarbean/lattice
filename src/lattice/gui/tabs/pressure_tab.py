from PySide6.QtWidgets import (
    QWidget, 
    QSpacerItem, 
    QSizePolicy, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton,
    QCheckBox,
    QSpinBox,
    QAbstractSpinBox,
    QApplication
)
from PySide6.QtCore import (
    QThread, 
    Qt,
    Signal,
    Slot,
    QMutex
)
from PySide6.QtGui import QColor
from collections import deque
import sys
import logging

# Local imports
from lattice.devices import PressureGauge, MockPressureGauge
from lattice.gui.widgets import PressureControlWidget, StackedScrollingPlotWidget
from lattice.utils import timing

logger = logging.getLogger(__name__)

class PressureTab(QWidget):
    start_polling = Signal(PressureGauge, int) # Gauge, interval_ms
    stop_polling = Signal(PressureGauge) # Gauge
    
    def __init__(self, pressure_gauges: list[PressureGauge]):
        super().__init__()
        self.pressure_gauges = pressure_gauges
        
        #########
        # SETUP #
        #########
        
        # Initialize pressure data object and connect signal
        self.pressure_data = {}
        for gauge in self.pressure_gauges:
            self.pressure_data[gauge] = deque(maxlen=7200) # 3 hours of data at polling rate of 500ms
            gauge.pressure_changed.connect(self.on_new_pressure_data)
        
        # Connect start/stop polling signals
        for gauge in self.pressure_gauges:
            self.start_polling.connect(gauge.start_polling)
            self.stop_polling.connect(gauge.stop_polling)
            
        #####################
        # CONFIGURE WIDGETS #
        #####################
        
        # Create and connect pressure control widgets
        self.pressure_control_widgets: list[PressureControlWidget] = []
        hue_step_size = int(360 / len(self.pressure_gauges))
        
        for i, gauge in enumerate(self.pressure_gauges):
            # Generate a unique color
            hue = (i * hue_step_size) + 15
            saturation = 255
            brightness = 255
            color = QColor()
            color.setHsv(hue, saturation, brightness)
            
            # Create control widget
            controls = PressureControlWidget(gauge.name, color)
            self.pressure_control_widgets.append(controls)
            
            # Connect displayed pressure
            gauge.pressure_changed.connect(controls.format_and_display_pressure)
            
            # Connect rate display
            gauge.rate_changed.connect(controls.format_and_display_rate)
            
            # Connect on / off button text
            gauge.is_on_changed.connect(controls.update_on_off_text)
            
            # Connect power toggle button action
            controls.power_toggle_button.clicked.connect(gauge.toggle_on_off)
        
        # Create pressure data plot
        self.pressure_plot = StackedScrollingPlotWidget(
            names=[gauge.name for gauge in self.pressure_gauges],
            data_dict=self.pressure_data,
            colors=[controls.color for controls in self.pressure_control_widgets]
        )
        
        # Create and connect pressure plot split and combine buttons
        self.plot_split_button = QPushButton("Split")
        self.plot_combine_button = QPushButton("Combine")
        
        self.plot_split_button.clicked.connect(self.pressure_plot.show_stacked)
        self.plot_combine_button.clicked.connect(self.pressure_plot.show_combined)
        
        # Create time window lock widgets
        self.time_lock_checkbox = QCheckBox("Lock Time Window (seconds)")
        self.time_lock_checkbox.setChecked(True)
        self.time_lock_input = QSpinBox(minimum=0, maximum=100000, value=30)
        self.time_lock_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.time_lock_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        ##################
        # LAYOUT WIDGETS #
        ##################
        
        # Create pressure controls layout
        self.pressure_controls_layout = QHBoxLayout()
        
        for widget in self.pressure_control_widgets:
            # Add a spacer
            self.pressure_controls_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
            
            # Add the widget
            self.pressure_controls_layout.addWidget(widget)
            
        # Add one last spacer (at this point the layout is | widget | widget ... with no closing spacer)
        self.pressure_controls_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Create plot controls layout
        self.plot_controls_layout = QHBoxLayout()
        self.plot_controls_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        for widget in [
            self.plot_split_button,
            self.plot_combine_button,
            self.time_lock_checkbox,
            self.time_lock_input
        ]:
            self.plot_controls_layout.addWidget(widget)
        
        # Create main layout
        self.main_layout = QVBoxLayout()
        
        # Add sub layouts and widgets to main layout
        self.main_layout.addLayout(self.pressure_controls_layout)
        self.main_layout.addWidget(self.pressure_plot)
        self.main_layout.addLayout(self.plot_controls_layout)
        
        # Apply main layout
        self.setLayout(self.main_layout)
        
        # Start polling for pressure data
        for gauge in self.pressure_gauges:
            self.start_polling.emit(gauge, 1000)

    @Slot(PressureGauge, float) # Gauge ref, Value
    def on_new_pressure_data(self, data, gauge: PressureGauge):
        # Store data
        self.pressure_data[gauge].append((timing.uptime_seconds(), data))
        
        # Update plot and constrain x-axis
        if self.time_lock_checkbox.isChecked():
            time_delta = self.time_lock_input.value()
            self.pressure_plot.update_data(time_delta)
            return
        
        # Don't constrain x-axis
        self.pressure_plot.update_data()
        
# Run as standalone app for testing
if __name__ == "__main__":
    # Override logging to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout()
    
    names = ["Intro Gauge", "Ion Gauge", "Transfer Gauge"]
    addresses = ["T1", "I1", "I2"]
    mutex = QMutex()
    gauges = []
    
    for i in range(len(names)):
        ser = MockPressureGauge(port="COM1", baudrate=9600, timeout=0.1)
        gauges.append(PressureGauge(
            name=names[i],
            address=addresses[i],
            ser=ser,
            serial_mutex=mutex
        ))
        
    pressure_tab = PressureTab(gauges)
    layout.addWidget(pressure_tab)
    
    window.setLayout(layout)
    window.setWindowTitle("Pressure Tab Widget")
    window.show()
    sys.exit(app.exec())