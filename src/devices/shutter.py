from PySide6.QtCore import QMutex, QObject, Signal
import time
import logging
import serial

# Local imports
from utils.serial_reader import SerialReader

logger = logging.getLogger(__name__)

class Shutter(QObject):
    is_open = Signal(bool)
    
    def __init__(self, name: str, address: int, ser: serial.Serial, mutex: QMutex, ser_reader: SerialReader):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.mutex = mutex
        
        ser_reader.data_received.connect(self._handle_ser_message)
        
    def _handle_ser_message(self, msg: str):
        # TODO: Implement response handling
        logger.debug(msg)
        
    def send_command(self, cmd):
        """Send a message to the serial port."""
        self.mutex.lock()
        if self.ser and self.ser.is_open:
            try:
                # Add a newline or protocol-specific ending if needed
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                time.sleep(0.01)
                logger.debug(f"{self.ser.port} O: {cmd}")
            except Exception as e:
                logger.error(f"Error in sending serial data on port {self.ser.port}: {e}")
        self.mutex.unlock()

    def reset(self):
        address = self.address
        self.send_command(f'/{address}TR')
        self.send_command(f'/{address}e0R')
        self.is_open.emit(False)

    def open(self):
        logger.debug(f"Opening shutter {self.address} ({self.name})")
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e7R')
        self.is_open.emit(True)

    def close(self):
        logger.debug(f"Closing shutter {self.address} ({self.name})")
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e8R')
        self.is_open.emit(False)