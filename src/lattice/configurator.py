import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QFileDialog, QStackedWidget, QHeaderView, QMenu, QSpinBox
)
from PySide6.QtCore import Qt
import yaml
from collections import defaultdict


class PressureForm(QWidget):
    def __init__(self, on_next, initial_data=None):
        super().__init__()
        self.on_next = on_next
        self.setWindowTitle("Pressure Gauge Configuration")

        self.layout = QVBoxLayout(self)

        label = QLabel("Pressure Gauges")
        label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout.addWidget(label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Name", "Address", "Port"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton("Add Row")
        add_btn.clicked.connect(self.add_row)
        btn_layout.addWidget(add_btn)

        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.collect_data)
        btn_layout.addWidget(next_btn)

        self.layout.addLayout(btn_layout)

        if initial_data:
            self.load_data(initial_data)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem("0"))
        self.table.setItem(row, 2, QTableWidgetItem("COM100"))

    def collect_data(self):
        devices = []
        for row in range(self.table.rowCount()):
            # Skip rows where name or port is None (empty)
            if self.table.item(row, 0) is None or self.table.item(row, 2) is None:
                continue
            name = self.table.item(row, 0).text()
            address_text = self.table.item(row, 1).text()
            port = self.table.item(row, 2).text()
            if not name or not port:
                continue
            try:
                address = address_text
            except ValueError:
                address = 0
            devices.append({
                "name": name,
                "address": address,
                "port": port
            })
        self.on_next(devices)

    def load_data(self, data):
        for dev in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(dev.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(str(dev.get("address", 0))))
            self.table.setItem(row, 2, QTableWidgetItem(dev.get("port", "COM100")))

    def show_context_menu(self, position):
        index = self.table.indexAt(position)
        if index.isValid():
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Row")
            if menu.exec(self.table.mapToGlobal(position)) == delete_action:
                self.table.removeRow(index.row())


class SourcesForm(QWidget):
    def __init__(self, on_next, on_back, initial_data=None):
        super().__init__()
        self.on_next = on_next
        self.back_callback = on_back
        self.setWindowTitle("Source Devices Configuration")

        self.layout = QVBoxLayout(self)

        label = QLabel("Sources and Shutters")
        label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout.addWidget(label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Name", "Device ID", "Address Set", "Port", "Shutter Address", "Shutter Port"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.handle_back)
        btn_layout.addWidget(back_btn)

        add_btn = QPushButton("Add Row")
        add_btn.clicked.connect(self.add_row)
        btn_layout.addWidget(add_btn)

        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.handle_next)
        btn_layout.addWidget(next_btn)

        self.layout.addLayout(btn_layout)

        if initial_data:
            self.load_data(initial_data)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(""))         # Name
        self.table.setItem(row, 1, QTableWidgetItem("1"))        # Device ID
        self.table.setItem(row, 2, QTableWidgetItem("loop_1"))   # Address Set
        self.table.setItem(row, 3, QTableWidgetItem("COM100"))    # Port
        self.table.setItem(row, 4, QTableWidgetItem("0"))        # Shutter Address
        self.table.setItem(row, 5, QTableWidgetItem("COM100"))     # Shutter Port

    def collect_data(self):
        devices = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0) is None:
                continue  # skip empty rows
            name = self.table.item(row, 0).text()
            if not name:
                continue
            try:
                device_id = int(self.table.item(row, 1).text())
            except (ValueError, AttributeError):
                device_id = 1
            address_set = self.table.item(row, 2).text() if self.table.item(row, 2) else "loop_1"
            port = self.table.item(row, 3).text() if self.table.item(row, 3) else "COM100"
            try:
                shutter_address = int(self.table.item(row, 4).text())
            except (ValueError, AttributeError):
                shutter_address = 0
            shutter_port = self.table.item(row, 5).text() if self.table.item(row, 5) else "COM100"
            devices.append({
                "name": name,
                "device_id": device_id,
                "address_set": address_set,
                "port": port,
                "shutter_address": shutter_address,
                "shutter_port": shutter_port,
            })
        return devices

    def handle_next(self):
        self.on_next(self.collect_data())

    def handle_back(self):
        # Pass the current data back to MainWindow to keep state
        self.back_callback(self.collect_data())

    def load_data(self, data):
        for device in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(device.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(str(device.get("device_id", 1))))
            self.table.setItem(row, 2, QTableWidgetItem(device.get("address_set", "loop_1")))
            self.table.setItem(row, 3, QTableWidgetItem(device.get("port", "COM100")))
            self.table.setItem(row, 4, QTableWidgetItem(str(device.get("shutter_address", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(device.get("shutter_port", "COM100")))

    def show_context_menu(self, position):
        index = self.table.indexAt(position)
        if index.isValid():
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Row")
            if menu.exec(self.table.mapToGlobal(position)) == delete_action:
                self.table.removeRow(index.row())


class BaudRateForm(QWidget):
    def __init__(self, ports, on_finish, on_back, initial_data=None):
        super().__init__()
        self.on_finish = on_finish
        self.back_callback = on_back
        self.setWindowTitle("Baud Rate Configuration")

        main_layout = QVBoxLayout(self)

        # Top Label in its own layout to keep it aligned like other steps
        top_label_layout = QHBoxLayout()
        label = QLabel("Baud Rates")
        label.setStyleSheet("font-weight: bold; font-size: 16px;")
        top_label_layout.addWidget(label)
        top_label_layout.addStretch(1)
        main_layout.addLayout(top_label_layout)

        # Spacer above input fields
        main_layout.addStretch(1)

        # Centered port input fields
        self.inputs = {}
        for port in sorted(ports):
            row = QHBoxLayout()
            row.addStretch(1)

            port_label = QLabel(f"{port} baud rate:")
            port_label.setMinimumWidth(150)

            spin = QSpinBox()
            spin.setMaximum(115200)
            spin.setMinimum(1)

            if initial_data and port in initial_data:
                spin.setValue(initial_data[port])
            else:
                spin.setValue(9600)

            row.addWidget(port_label)
            row.addWidget(spin)
            row.addStretch(1)

            main_layout.addLayout(row)
            self.inputs[port] = spin

        # Spacer below input fields
        main_layout.addStretch(1)

        # Buttons at the bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.back_callback)
        button_layout.addWidget(back_btn)

        generate_btn = QPushButton("Generate YAML")
        generate_btn.clicked.connect(self.generate_yaml)
        button_layout.addWidget(generate_btn)

        button_layout.addStretch(1)
        main_layout.addLayout(button_layout)

    def generate_yaml(self):
        baudrates = {port: spin.value() for port, spin in self.inputs.items()}
        self.on_finish(baudrates)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Device YAML Config Generator")
        self.stack = QStackedWidget()
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.stack)

        self.pressure_data = []
        self.sources_data = []
        self.baudrates = {}

        self.pressure_form = PressureForm(self.on_pressure_done)
        self.stack.addWidget(self.pressure_form)
        self.stack.setCurrentWidget(self.pressure_form)

        # Load config if exists
        self.load_config()

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "config", "hardware.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    data = yaml.safe_load(f)

                if not data or 'devices' not in data:
                    return  # no devices key, nothing to load

                devices = data['devices']

                # Clear existing data
                self.pressure_data = []
                self.sources_data = []
                self.baudrates = {}

                # Load pressure devices
                pressure_devices = devices.get('pressure', {})
                if isinstance(pressure_devices, dict):
                    for port, info in pressure_devices.items():
                        if not isinstance(info, dict):
                            continue
                        connections = info.get('connections', [])
                        for conn in connections:
                            if not isinstance(conn, dict):
                                continue
                            self.pressure_data.append({
                                "name": conn.get('name', ""),
                                "address": conn.get('address', 0),
                                "port": port
                            })
                        # Save baudrate for port
                        baud = info.get('serial', {}).get('baudrate')
                        if baud is not None:
                            self.baudrates[port] = baud

                # Load sources devices
                sources_devices = devices.get('sources', {})
                if isinstance(sources_devices, dict):
                    for port, info in sources_devices.items():
                        if not isinstance(info, dict):
                            continue
                        connections = info.get('connections', [])
                        for conn in connections:
                            if not isinstance(conn, dict):
                                continue
                            self.sources_data.append({
                                "name": conn.get('name', ""),
                                "device_id": conn.get('device_id', 1),
                                "address_set": conn.get('address_set', "loop_1"),
                                "port": port,
                                "shutter_address": 0,
                                "shutter_port": ""
                            })
                        # Save baudrate for port
                        baud = info.get('serial', {}).get('baudrate')
                        if baud is not None:
                            self.baudrates[port] = baud

                # Load shutters devices and merge into sources_data
                shutters_devices = devices.get('shutters', {})
                shutters_info = {}
                if isinstance(shutters_devices, dict):
                    for port, info in shutters_devices.items():
                        if not isinstance(info, dict):
                            continue
                        connections = info.get('connections', [])
                        for conn in connections:
                            if not isinstance(conn, dict):
                                continue
                            name = conn.get('name')
                            if name:
                                shutters_info[name] = {
                                    "shutter_address": conn.get('address', 0),
                                    "shutter_port": port
                                }
                        # Save baudrate for port
                        baud = info.get('serial', {}).get('baudrate')
                        if baud is not None:
                            self.baudrates[port] = baud

                # Merge shutters info back into sources_data by matching name
                for src in self.sources_data:
                    shutter = shutters_info.get(src['name'], {})
                    src['shutter_address'] = shutter.get('shutter_address', 0)
                    src['shutter_port'] = shutter.get('shutter_port', "")

                # Load data into pressure form
                self.pressure_form.load_data(self.pressure_data)

            except Exception as e:
                print(f"Failed to load config: {e}")


    def on_pressure_done(self, pressure_devices):
        self.pressure_data = pressure_devices
        self.sources_form = SourcesForm(
            on_next=self.on_sources_done,
            on_back=self.on_pressure_back,
            initial_data=self.sources_data
        )
        self.stack.addWidget(self.sources_form)
        self.stack.setCurrentWidget(self.sources_form)

    def on_pressure_back(self, sources_devices):
        # Called when back from Sources to Pressure
        self.sources_data = sources_devices
        self.stack.setCurrentWidget(self.pressure_form)

    def on_sources_done(self, sources_devices):
        self.sources_data = sources_devices

        unique_ports = set(d['port'] for d in self.pressure_data)
        for dev in sources_devices:
            unique_ports.add(dev['port'])
            if dev['shutter_port']:
                unique_ports.add(dev['shutter_port'])

        self.baud_form = BaudRateForm(
            ports=unique_ports,
            on_finish=self.on_baudrates_done,
            on_back=self.on_sources_back,
            initial_data=self.baudrates
        )
        self.stack.addWidget(self.baud_form)
        self.stack.setCurrentWidget(self.baud_form)

    def on_sources_back(self):
        self.stack.setCurrentWidget(self.sources_form)

    def on_baudrates_done(self, baudrates):
        self.baudrates = baudrates
        yaml_data = self.build_yaml()

        config_dir = os.path.join(os.path.dirname(__file__), "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        file_path = os.path.join(config_dir, "hardware.yaml")

        try:
            with open(file_path, 'w') as f:
                yaml.dump(yaml_data, f, sort_keys=False)
            print(f"Config saved to {file_path}")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def build_yaml(self):
        result = {'devices': {}}  # Regular dict instead of defaultdict

        # Pressure
        for dev in self.pressure_data:
            port = dev['port']
            result['devices'].setdefault('pressure', {})  # Ensure 'pressure' exists
            result['devices']['pressure'].setdefault(port, {
                'serial': {
                    'port': port,
                    'baudrate': self.baudrates.get(port, 9600)
                },
                'connections': []
            })
            result['devices']['pressure'][port]['connections'].append({
                'name': dev['name'],
                'address': dev['address']
            })

        # Sources and Shutters
        for dev in self.sources_data:
            port = dev['port']
            shutter_port = dev['shutter_port']

            # Sources
            result['devices'].setdefault('sources', {})  # Ensure 'sources' exists
            result['devices']['sources'].setdefault(port, {
                'serial': {
                    'port': port,
                    'baudrate': self.baudrates.get(port, 9600)
                },
                'connections': []
            })
            result['devices']['sources'][port]['connections'].append({
                'name': dev['name'],
                'device_id': dev['device_id'],
                'address_set': dev['address_set']
            })

            # Shutters
            if shutter_port:
                result['devices'].setdefault('shutters', {})  # Ensure 'shutters' exists
                result['devices']['shutters'].setdefault(shutter_port, {
                    'serial': {
                        'port': shutter_port,
                        'baudrate': self.baudrates.get(shutter_port, 9600)
                    },
                    'connections': []
                })
                result['devices']['shutters'][shutter_port]['connections'].append({
                    'name': dev['name'],
                    'address': dev['shutter_address']
                })

        return result
    
def start():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 500)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    start()
