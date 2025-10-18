from PySide6.QtCore import QMutex, QObject, Signal, QMutexLocker
import time
import logging
import serial

# Local imports
from utils.serial_reader import SerialReader

logger = logging.getLogger(__name__)

class Shutter(QObject):
    is_open = Signal(bool)
    
    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, ser_reader: SerialReader):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.serial_mutex = serial_mutex
        self.enabled = True
        self.data_mutex = QMutex()
        
        ser_reader.data_received.connect(self._handle_ser_message)
        
    def _handle_ser_message(self, msg: str):
        # TODO: Implement response handling
        logger.debug(msg)
        
    def send_command(self, cmd):
        """Send a message to the serial port."""
        self.serial_mutex.lock()
        if self.ser and self.ser.is_open:
            try:
                # Add a newline or protocol-specific ending if needed
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                time.sleep(0.01)
                logger.debug(f"{self.ser.port} O: {cmd}")
            except Exception as e:
                logger.error(f"Error in sending serial data on port {self.ser.port}: {e}")
        self.serial_mutex.unlock()
        
    def enable(self):
        with QMutexLocker(self.data_mutex):
            self.enabled = True
            
    def disable(self):
        with QMutexLocker(self.data_mutex):
            self.enabled = False

    def reset(self):
        with QMutexLocker(self.data_mutex):
            if not self.enabled:
                return
        
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e0R')
        self.is_open.emit(False)

    def open(self):
        with QMutexLocker(self.data_mutex):
            if not self.enabled:
                return
            
        logger.debug(f"Opening shutter {self.address} ({self.name})")
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e7R')
        self.is_open.emit(True)

    def close(self):
        with QMutexLocker(self.data_mutex):
            if not self.enabled:
                return
            
        logger.debug(f"Closing shutter {self.address} ({self.name})")
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e8R')
        self.is_open.emit(False)