import sys
from PySide6.QtWidgets import QApplication
from PySide6 import QtCore
import pyqtgraph as pg
import numpy as np
import time
import logging
import os
import yaml
import serial
from pymodbus.client import ModbusSerialClient

# Local imports
from devices.shutter import Shutter
from devices.source import Source
from devices.pressure import Pressure
from utils.serial_reader import SerialReader

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

# Get the directory of this script and set other important directories
base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, 'config', 'default.yaml')
main_ui_path = os.path.join(base_dir, 'gui', 'main.ui')

# Load config file
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

uiclass, baseclass = pg.Qt.loadUiType(main_ui_path)

class MainWindow(uiclass, baseclass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.shutter_control_button_group.buttonClicked.connect(self.on_button_clicked)
        
        # Create shutter objects
        shutter_config = config['devices']['shutters']
        ser = serial.Serial(
            port=shutter_config['serial']['port'], 
            baudrate=shutter_config['serial']['baudrate']
            )
        mutex = QtCore.QMutex()
        self.shutter_reader = SerialReader(ser, mutex)
        self.shutter_reader.start()
        self.shutters = [Shutter(
            name=shutter['name'], 
            address=shutter['address'], 
            ser=ser, 
            mutex=mutex,
            ser_reader=self.shutter_reader
            ) for shutter in shutter_config['connections']]
        
        # Create source objects
        self.sources = []
        for source_config in config['devices']['sources'].values():
            client = ModbusSerialClient(
                port=source_config['serial']['port'], 
                baudrate=source_config['serial']['baudrate']
                )
            mutex = QtCore.QMutex()
            self.sources.extend([Source(
                name=device['name'],
                device_id=device['device_id'],
                address_set=device['address_set'],
                client=client,
                mutex=mutex
                ) for device in source_config['connections']])
        
        # Shutter UI control assignments
        # for i, shutter in enumerate(self.shutters):
        #     controls = self.findChild(QWidget, f"shutter_controls_{i}")
        #     controls.open_button.clicked.connect(shutter.open)
        #     controls.close_button.clicked.connect(shutter.close)

        # Data storage
        self.start_time = time.time()
        self.x_data = np.empty(0)
        self.y_data = np.empty((0, 4))

        # Plot initialization
        self.pressure_graph_widget.setXRange(0, 30)
        self.pressure_graph_widget.setYRange(-1, 1)
        self.pressure_graph_widget.enableAutoRange(axis='x', enable=False)
        self.pressure_graph_widget.enableAutoRange(axis='y', enable=False)
        self.curve1 = self.pressure_graph_widget.plot(pen=pg.mkPen('r', width=2))
        self.curve2 = self.pressure_graph_widget.plot(pen=pg.mkPen('g', width=2))
        self.curve3 = self.pressure_graph_widget.plot(pen=pg.mkPen('b', width=2))
        self.curve4 = self.pressure_graph_widget.plot(pen=pg.mkPen('y', width=2))
        self.curve1.setClipToView(True)
        self.curve2.setClipToView(True)    
        self.curve3.setClipToView(True)    
        self.curve4.setClipToView(True)                                                          

        # Set up a timer to mupdate the plot every 5 seconds
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(25)  # milliseconds
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        
    def on_button_clicked(self, button):
        id = int(button.objectName()[-1])
        if button.text() == "Closed":
            button.setText("Open")
            self.shutters[id].open()
        else:
            button.setText("Closed")
            self.shutters[id].close()

    def update_plot(self):
        # Simulate real-time data (you can replace this with sensor/API input)
        current_time = time.time() - self.start_time
        new_x = current_time
        new_y = [np.sin(new_x), np.sin(new_x + 90), np.sin(new_x + 180), np.sin(new_x + 270)] # sin wave
        # new_y = np.sin(current_time) + np.random.normal(scale=0.1)  # noisy sine wave

        # Display most recent values
        self.growth_display.setText(f"{new_y[0]:.2f}")
        self.flux_display.setText(f"{new_y[1]:.2f}")
        self.intro_display.setText(f"{new_y[2]:.2f}")
        self.thermocouple_display.setText(f"{new_y[3]:.2f}")

        # Append new data
        self.x_data = np.append(self.x_data, new_x)
        self.y_data = np.vstack([self.y_data, new_y])
        
        # Update the plot with new full dataset
        self.curve1.setData(self.x_data, self.y_data[:, 0])
        self.curve2.setData(self.x_data, self.y_data[:, 1])
        self.curve3.setData(self.x_data, self.y_data[:, 2])
        self.curve4.setData(self.x_data, self.y_data[:, 3])

        # Optional: auto-scroll x-axis
        if new_x >= 30:
            self.pressure_graph_widget.setXRange(max(0, new_x - 30), new_x)  # show last 30 seconds

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()