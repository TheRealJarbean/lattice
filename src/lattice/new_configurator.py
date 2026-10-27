import sys
from PySide6.QtCore import (
    QCoreApplication
)
from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QWidget,
    QMainWindow,
    QTabWidget,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QComboBox,
)
from PySide6.QtCore import Qt, Signal, Slot
import serial.tools.list_ports
import logging

# Local imports
from lattice.utils.config import AppConfig

logger = logging.getLogger(__name__)

PORTS = [port.device for port in serial.tools.list_ports.comports()]

class HexSpinBox(QSpinBox):
    def textFromValue(self, value):
        return f"{value:X}"

    def valueFromText(self, text):
        return int(text,16)

class ShutterTab(QWidget):
    """
        Form data related to motors. Should ultimately return data in the following format:
        COM100:
            connections: [
                {
                    address: 1,
                    name: Gallium
                },
                {
                    address: B,
                    name: Indium
                },
                ...
            ],
            serial: {
                baudrate: 9600,
            }
        COM101:
            ...
    """
    class ShutterRow(QWidget):
        def __init__(self):
            super().__init__()
            layout = QHBoxLayout()

            self.name_input = QLineEdit(placeholderText="Shutter Name")
            self.address_input = HexSpinBox()
            self.address_input.setRange(0, 0xF)
            self.serial_port_selection = QComboBox()
            self.serial_port_selection.addItems([str(port) for port in PORTS])
            self.serial_port_selection.setCurrentIndex(-1)
            self.remove_button = QPushButton("Remove")
            self.remove_button.setFixedWidth(100)

            # Give the remove button a container for fixed spacing
            remove_button_container = QWidget()
            container_layout = QHBoxLayout()
            container_layout.addStretch()
            container_layout.addWidget(self.remove_button)
            container_layout.addStretch()
            remove_button_container.setLayout(container_layout)

            layout.addWidget(self.name_input, 1)
            layout.addWidget(self.address_input, 1)
            layout.addWidget(self.serial_port_selection, 1)
            layout.addWidget(remove_button_container, 1)
            layout.setContentsMargins(5, 0, 5, 0)
            self.setLayout(layout)

        def get_name(self) -> str:
            return self.name_input.text()

        def get_address(self) -> int:
            return self.address_input.value()

        def is_port_selected(self) -> bool:
            return self.serial_port_selection.currentIndex() != -1

        def get_port(self) -> str:
            return self.serial_port_selection.currentText()
        
    def __init__(self):
        super().__init__()

        self.shutter_rows: list["ShutterTab.ShutterRow"] = []
        
        self.main_layout = QVBoxLayout(self)
        self.settings_layout = QVBoxLayout(self)
        self.settings_layout.setContentsMargins(5, 5, 5, 5)
        self.settings_layout.setSpacing(0)
        add_row_button = QPushButton("+")
        add_row_button.setFixedWidth(200)
        add_row_button.clicked.connect(self.add_row)

        headers = [
            "Name",
            "Address",
            "Serial Port",
            ""
        ]

        header_row_layout = QHBoxLayout()
        for header in headers:
            label = QLabel(header, alignment=Qt.AlignmentFlag.AlignLeft)
            label.setMinimumWidth(100)
            header_row_layout.addWidget(label, 1)
        header_row_layout.setContentsMargins(5, 5, 5, 5)

        self.settings_layout.addLayout(header_row_layout)
        self.settings_layout.addSpacing(10)
        self.main_layout.addLayout(self.settings_layout)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(add_row_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addStretch()

    def add_row(self):
        row = self.ShutterRow()
        self.shutter_rows.append(row)
        self.settings_layout.addWidget(row)

        row.remove_button.clicked.connect(lambda: self._remove_row(row))

    def _remove_row(self, row: ShutterRow):
        if row in self.shutter_rows:
            self.shutter_rows.remove(row)
            self.settings_layout.removeWidget(row)
            row.deleteLater()
            return

    def to_dict(self) -> dict | None:
        settings = {}
        used_names = []
        used_addresses = {}
        for row in self.shutter_rows:
            name = row.get_name()
            if name == "":
                logger.error("Shutters must have a name")
                return None
            if name in used_names:
                logger.error(f"Shutters cannot have the same name: {name}")
                return None
            used_names.append(name)

            if not row.is_port_selected():
                logger.error(f"No serial port selected for Shutter {name}")
                return None
            
            port = row.get_port()
            if port not in settings.keys():
                settings[port] = {"connections": [], "serial": None}
            if port not in used_addresses.keys():
                used_addresses[port] = []

            address = row.get_address()
            if address in used_addresses[port]:
                logger.error(f"Shutters cannot have the same address")
                return None
            used_addresses[port].append(address)

            # Passed basic validation at this point

            settings[port]["connections"].append({"address": address, "name": name})

        return settings

    def get_ports(self):
        return [row.get_port() for row in self.shutter_rows if row.is_port_selected()]


class PressureTab(QWidget):
    """
    Form data related to pressure gauges. Should ultimately return data in the following format:
    COM100:
        connections: [
            {
                address: I1,
                name: Transfer
            },
            {
                address: I2,
                name: Ion
            }
        ],
        serial: {
            baudrate: 9600,
        }
    """
    class GaugeRow(QWidget):
        def __init__(self):
            super().__init__()
            layout = QHBoxLayout()

            self.name_input = QLineEdit(placeholderText="Gauge Name")
            self.address_input = QComboBox()
            self.address_input.addItems(["I1", "I2"])
            self.address_input.setCurrentIndex(-1)
            self.remove_button = QPushButton("Remove")
            self.remove_button.setFixedWidth(100)

            # Give the remove button a container for fixed spacing
            remove_button_container = QWidget()
            container_layout = QHBoxLayout()
            container_layout.addStretch()
            container_layout.addWidget(self.remove_button)
            container_layout.addStretch()
            remove_button_container.setLayout(container_layout)

            layout.addWidget(self.name_input, 1)
            layout.addWidget(self.address_input, 1)
            layout.addWidget(remove_button_container, 1)
            layout.setContentsMargins(5, 0, 5, 0)
            self.setLayout(layout)

        def get_name(self) -> str:
            return self.name_input.text()

        def get_address(self) -> int:
            return self.address_input.currentText()
        
    def __init__(self):
        super().__init__()

        self.gauge_rows: list["PressureTab.GaugeRow"] = []
        
        self.main_layout = QVBoxLayout(self)
        self.settings_layout = QVBoxLayout(self)
        self.settings_layout.setContentsMargins(5, 5, 5, 5)
        self.settings_layout.setSpacing(0)
        add_row_button = QPushButton("+")
        add_row_button.setFixedWidth(200)
        add_row_button.clicked.connect(self.add_row)
        serial_port_label = QLabel("Serial Port")
        self.serial_port_input = QComboBox()
        self.serial_port_input.addItems(PORTS)
        self.serial_port_input.setCurrentIndex(-1)

        headers = [
            "Name",
            "Address",
            ""
        ]

        header_row_layout = QHBoxLayout()
        for header in headers:
            label = QLabel(header, alignment=Qt.AlignmentFlag.AlignLeft)
            header_row_layout.addWidget(label, 1)
        header_row_layout.setContentsMargins(5, 5, 5, 5)

        top_row_layout = QHBoxLayout()
        top_row_layout.addWidget(serial_port_label)
        top_row_layout.addSpacing(10)
        top_row_layout.addWidget(self.serial_port_input)
        top_row_layout.addStretch()

        self.settings_layout.addLayout(top_row_layout)
        self.settings_layout.addSpacing(15)
        self.settings_layout.addLayout(header_row_layout)
        self.settings_layout.addSpacing(10)
        self.main_layout.addLayout(self.settings_layout)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(add_row_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addStretch()

    def add_row(self):
        row = self.GaugeRow()
        self.gauge_rows.append(row)
        self.settings_layout.addWidget(row)

        row.remove_button.clicked.connect(lambda: self._remove_row(row))

    def _remove_row(self, row:GaugeRow):
        if row in self.gauge_rows:
            self.gauge_rows.remove(row)
            self.settings_layout.removeWidget(row)
            row.deleteLater()
            return

    def to_dict(self) -> dict | None:
        if self.serial_port_input.currentIndex() == -1:
            logger.error("No serial port selected for gauges")

        port = self.serial_port_input.currentText()
        settings = {port: {"connections": [], "serial": {"baudrate": None}}}
        used_names = []
        used_addresses = []
        for row in self.gauge_rows:
            name = row.get_name()
            if name == "":
                logger.error("Pressure gauges must have a name")
                return None
            if name in used_names:
                logger.error(f"Pressure gauges cannot have the same name: {name}")
                return None
            used_names.append(name)

            address = row.get_address()
            if address in used_addresses:
                logger.error(f"Pressure gauges cannot have the same address")
                return None
            used_addresses.append(address)

            # Passed basic validation at this point

            settings[port]["connections"].append({"address": address, "name": name})

        return settings

    def get_port(self) -> str | None:
        return self.serial_port_input.currentText() if self.serial_port_input.currentIndex() != -1 else None

class SourceTab(QWidget):
    """
    Form data related to sources. Should ultimately return data in the following format:
    COM100:
        connections: [
            {
                address_set: 2604_loop_1,
                device_id: 1,
                name: Gallium
            },
            {
                address: 2604_loop_2,
                device_id: 2,
                name: Indium
            }
        ],
        serial: {
            baudrate: 9600,
        }
    """
    class SourceRow(QWidget):
        def __init__(self):
            super().__init__()
            layout = QHBoxLayout()

            self.name_input = QLineEdit(placeholderText="Source Name")
            self.address_set_input = QComboBox()
            self.address_set_input.addItems(["2604_loop_1", "2604_loop_2", "2404_loop_1"])
            self.address_set_input.setCurrentIndex(-1)
            self.device_id_input = QSpinBox(minimum=1)
            self.remove_button = QPushButton("Remove")
            self.remove_button.setFixedWidth(100)

            # Give the remove button a container for fixed spacing
            remove_button_container = QWidget()
            container_layout = QHBoxLayout()
            container_layout.addStretch()
            container_layout.addWidget(self.remove_button)
            container_layout.addStretch()
            remove_button_container.setLayout(container_layout)

            layout.addWidget(self.name_input, 1)
            layout.addWidget(self.address_set_input, 1)
            layout.addWidget(self.device_id_input, 1)
            layout.addWidget(remove_button_container, 1)
            layout.setContentsMargins(5, 0, 5, 0)
            self.setLayout(layout)

        def get_name(self) -> str:
            return self.name_input.text()

        def is_address_set_selected(self) -> bool:
            return self.address_set_input.currentIndex() != -1

        def get_address_set(self) -> str:
            return self.address_set_input.currentText()

        def get_device_id(self) -> int:
            return self.device_id_input.value()
        
    def __init__(self):
        super().__init__()

        self.source_rows: list["SourceTab.SourceRow"] = []
        
        self.main_layout = QVBoxLayout(self)
        self.settings_layout = QVBoxLayout(self)
        self.settings_layout.setContentsMargins(5, 5, 5, 5)
        self.settings_layout.setSpacing(0)
        add_row_button = QPushButton("+")
        add_row_button.setFixedWidth(200)
        add_row_button.clicked.connect(self.add_row)
        serial_port_label = QLabel("Serial Port")
        self.serial_port_input = QComboBox()
        self.serial_port_input.addItems(PORTS)
        self.serial_port_input.setCurrentIndex(-1)

        headers = [
            "Name",
            "Address Set",
            "Device ID",
            ""
        ]

        header_row_layout = QHBoxLayout()
        for header in headers:
            label = QLabel(header, alignment=Qt.AlignmentFlag.AlignLeft)
            header_row_layout.addWidget(label, 1)
        header_row_layout.setContentsMargins(5, 5, 5, 5)

        top_row_layout = QHBoxLayout()
        top_row_layout.addWidget(serial_port_label)
        top_row_layout.addSpacing(10)
        top_row_layout.addWidget(self.serial_port_input)
        top_row_layout.addStretch()

        self.settings_layout.addLayout(top_row_layout)
        self.settings_layout.addSpacing(15)
        self.settings_layout.addLayout(header_row_layout)
        self.settings_layout.addSpacing(10)
        self.main_layout.addLayout(self.settings_layout)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(add_row_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addStretch()

    def add_row(self):
        row = self.SourceRow()
        self.source_rows.append(row)
        self.settings_layout.addWidget(row)

        row.remove_button.clicked.connect(lambda: self._remove_row(row))

    def _remove_row(self, row:SourceRow):
        if row in self.source_rows:
            self.source_rows.remove(row)
            self.settings_layout.removeWidget(row)
            row.deleteLater()
            return

    def to_dict(self) -> dict | None:
        if self.serial_port_input.currentIndex() == -1:
            logger.error("No serial port selected for sources")

        port = self.serial_port_input.currentText()
        settings = {port: {"connections": [], "serial": {"baudrate": None}}}
        used_names = []
        used_device_ids = []
        for row in self.source_rows:
            name = row.get_name()
            if name == "":
                logger.error("Sources must have a name")
                return None
            used_names.append(name)

            if not row.is_address_set_selected():
                logger.error(f"No address set selected for Source {name}")
                return None
            address_set = row.get_address_set()

            device_id = row.get_device_id()
            if device_id in used_device_ids:
                logger.error(f"Sources cannot have the same device_id")
                return None
            used_device_ids.append(device_id)

            # Passed basic validation at this point

            settings[port]["connections"].append({"address_set": address_set, "device_id": device_id, "name": name})

        return settings

    def get_port(self) -> str | None:
        return self.serial_port_input.currentText() if self.serial_port_input.currentIndex() != -1 else None

class BaudrateTab(QWidget):
    BAUDRATES = [
        "9600",
        "14400",
        "19200",
        "38400",
        "57600"
    ]

    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        hint = QLabel("Ensure the baudrate matches the value configured on the hardware!")
        self.main_layout.addWidget(hint)
        self.main_layout.addSpacing(10)
        self.main_layout.addStretch()

        # Store port labels and associated label and selection widgets
        self.port_baudrate_input_map: dict[str, tuple[QLabel, QComboBox]] = {}
    
    def update_ports(self, ports):
        old_keys = list(self.port_baudrate_input_map.keys())
        for port in old_keys:
            if port not in ports:
                self.port_baudrate_input_map[port][0].deleteLater()
                self.port_baudrate_input_map[port][1].deleteLater()
                self.port_baudrate_input_map.pop(port)

        for port in ports:
            if port not in self.port_baudrate_input_map.keys():
                self.port_baudrate_input_map[port] = (
                    QLabel(port),
                    QComboBox()
                )
                self.port_baudrate_input_map[port][1].addItems(self.BAUDRATES)

                row = QHBoxLayout()
                row.addStretch()
                row.addWidget(self.port_baudrate_input_map[port][0])
                row.addWidget(self.port_baudrate_input_map[port][1])
                row.addStretch()

                # Add row before bottom strech area
                self.main_layout.insertLayout(self.main_layout.count() - 1, row)


class ConfiguratorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        config = AppConfig.HARDWARE
        print(config)

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        self.setWindowTitle("Lattice Configurator")

        # Tabs
        self.shutter_tab = ShutterTab()
        self.pressure_tab = PressureTab()
        self.source_tab = SourceTab()
        self.baudrate_tab = BaudrateTab()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.shutter_tab, "Shutters")
        self.tabs.addTab(self.pressure_tab, "Pressure Gauges")
        self.tabs.addTab(self.source_tab, "Sources")
        self.tabs.addTab(self.baudrate_tab, "Baudrates")
        self.tabs.currentChanged.connect(self.on_tab_change)

        main_layout.addWidget(self.tabs)

        # Save and Exit buttons
        self.exit_button = QPushButton("Exit Without Saving")
        self.exit_button.clicked.connect(self.cancel)
        self.save_button = QPushButton("Apply Changes")
        self.save_button.clicked.connect(self.submit)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.exit_button)
        row.addWidget(self.save_button)

        main_layout.addLayout(row)

        # Finish up
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def to_dict(self) -> dict | None:
        pressure = self.pressure_tab.to_dict()
        shutters = self.shutter_tab.to_dict()
        sources = self.source_tab.to_dict()

        if None in [pressure, shutters, sources]:
            return None

        all_ports = list(pressure.keys()) + list(shutters.keys()) + list(sources.keys())
        # Simple test to see if ports are reused
        if (len(all_ports) > len(set(all_ports))):
            logger.error(f"Different types of devices cannot use the same serial port.")
            return None

        return {
            "devices": {
                "pressure": self.pressure_tab.to_dict(),
                "shutters": self.shutter_tab.to_dict(),
                "sources": self.source_tab.to_dict()
            }
        }

    def submit(self):
        print(self.to_dict())
        AppConfig.HARDWARE.data = self.to_dict()
        AppConfig.HARDWARE.save()

    def cancel(self):
        QCoreApplication.quit()

    def on_tab_change(self):
        # Update listed serial ports upon switching to the baudrates tab
        if self.tabs.tabBar().tabText(self.tabs.currentIndex()) == "Baudrates":
            ports = self.shutter_tab.get_ports()

            for port in (self.pressure_tab.get_port(), self.source_tab.get_port()):
                if port is not None:
                    ports.append(port)

            print(ports)
            self.baudrate_tab.update_ports(ports)

def start():
    app = QApplication(sys.argv)

    window = ConfiguratorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start()