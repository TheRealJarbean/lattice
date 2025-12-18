from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtGui import QFont
import logging

# Local imports
from mbe_software.devices import PressureGauge, Shutter, Source
from mbe_software.gui.widgets import ModbusLogWidget, SerialLogWidget

logger = logging.getLogger(__name__)

class DiagnosticsTab(QWidget):
    def __init__(self, gauges: PressureGauge, sources: Source, shutters: Shutter):
        super().__init__()
        self.gauges = gauges
        self.sources = sources
        self.shutters = shutters

        self.shutter_dict = {shutter.name: shutter for shutter in self.shutters}
        self.source_dict = {source.name: source for source in self.sources}

        # Create serial log widgets
        serial_log_layout = QHBoxLayout()
        
        self.pressure_serial_log = SerialLogWidget(
            app=self,
            name="Pressure Gauges",
            device_names=[gauge.name for gauge in self.gauges]
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
        for gauge in self.gauges:
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
        
        # Create main layout
        layout = QVBoxLayout()
        
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setUnderline(True)

        label = QLabel("SERIAL LOGS")
        label.setFont(font)

        layout.addWidget(label)
        layout.addLayout(serial_log_layout)

        self.setLayout(layout)