# Base class for all devices using serial I/O, defines common communication parameters
from PySide6.QtCore import QObject, QTimer
import serial
import logging

logger = logging.getLogger(__name__)

class SerialWorker(QObject):
    def __init__(self, port: str, baudrate: int = 9600, monitor_func=None):
        super().__init__()
        self.port = port
        self.monitor_func = monitor_func
        self.baudrate = baudrate
        self.ser = None

        # Open the serial connection
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout = 0.1, write_timeout=1)
        except Exception as e:
            print(f"Error occurred when opening serial port: {e}")

        # Set up timer for checking received data
        self.timer = QTimer()
        self.timer.setInterval(200)  # Poll every 200 ms
        self.timer.timeout.connect(self.check_serial_data)

    def start_monitor(self):
        if not self.timer.isActive():
            self.timer.start()

    def stop_monitor(self):
        if self.timer.isActive():
            self.stop()

    def check_serial_data(self):
        try:
            if self.ser.in_waiting:
                data = self.ser.readline().decode(errors='ignore').strip()
                if data:
                    self.monitor_func(data)
                    logger.debug(f"{self.port} I: {data}")
        except Exception as e:
            print(f"Error occurred in serial monitoring: {e}")

    def send(self, msg):
        """Send a message to the serial port."""
        if self.ser and self.ser.is_open:
            try:
                # Add a newline or protocol-specific ending if needed
                self.ser.write(msg.encode('utf-8'))
                logger.debug(f"{self.port} O: {msg}")
            except Exception as e:
                print(f"Error in sending serial data on port {self.port}: {e}")

    def finish(self):
        if self.ser and self.ser.is_open:
                self.ser.close()