from PySide6.QtCore import Signal, QMutex, QObject
import time
import serial
import logging

# Local imports
from utils.serial_reader import SerialReader

logger = logging.getLogger(__name__)

class Pressure(QObject):
    """
    Pressure sensors currently use COM6
    Sensor names appear to be T1 I1 I2 and I3
    Appears to request updates periodically, wait 25ms for a response, and wait 10ms to loop
    """
    pressure_changed = Signal(float)
    rate_changed = Signal(float)
    is_on_changed = Signal(bool)

    def __init__(self, name, address, ser: serial.Serial, mutex: QMutex, ser_reader: SerialReader):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.pressure = 0.0
        self.rate_per_second = 0.0
        self.is_on = False
        
        ser_reader.data_received.connect(self._handle_ser_message)
        
    def _handle_ser_message(self):
        # TODO: Implement response handling
        pass
        
    def send_command(self, cmd):
        """Send a message to the serial port."""
        self.mutex.lock()
        if self.ser and self.ser.is_open:
            try:
                # Add a newline or protocol-specific ending if needed
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                logger.debug(f"{self.port} O: {cmd}")
            except Exception as e:
                print(f"Error in sending serial data on port {self.port}: {e}")
        self.mutex.unlock()
        
    def turn_on(self):
        # TODO: Verify this command is correct
        self.send_command(f'#0031{self.address}')
        self.is_on_changed.emit(True)
        
    def turn_off(self):
        # TODO: Verify this command is correct
        self.send_command(f'##0030{self.address}')
        self.is_on_changed.emit(False)

    def update_rate(self):
        new_rate = (self.rate_per_second + self.pressures) / 2
        self.rate_per_second = new_rate
        self.rate_changed.emit(new_rate)

    def _poll(self):
        # TODO: Revise this
        # This replicates the sequence structure of LabVIEW, but shouldn't be necessary to run commands sequentially like this
        
        self.send_command(f'#0032{self.address}')
        time.sleep(0.03)
        if self.is_on:
            self.send_command(f'#0031{self.address}')
        else:
            self.send_command(f'##0030{self.address}')
        time.sleep(0.03)
        self.send(f'#000F')
        time.sleep(0.08)