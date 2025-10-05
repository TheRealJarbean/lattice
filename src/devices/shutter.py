from PySide6.QtCore import QThread, QMutex, Signal
import time
import logging
import serial

# Local imports
from utils.serial_reader import SerialReader

logger = logging.getLogger(__name__)

class Shutter(QThread):
    def __init__(self, name: str, address: int, ser: serial.Serial, mutex: QMutex, ser_reader: SerialReader):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.mutex = mutex
        self.is_open = Signal(bool)
        
        ser_reader.data_received.connect(self._handle_ser_message)
        
    def run(self):
        """Invoked automatically when self.start() is called in the main thread"""
        self._is_running = True
        while self._is_running:
            pass
            # Do some stuff like poll shutter state
    
    def stop(self):
        self._is_running = False
        
    def _handle_ser_message(self, msg: str):
        # TODO: Implement response handling
        logger.debug(msg)
    
    def poll_status(self):
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

    def reset(self):
        address = self.address
        self.send_command(f'/{address}TR')
        time.sleep(0.02)
        self.send_command(f'/{address}e0R')
        self.is_open = False

    def open(self):
        logger.debug(f"Opening shutter {self.address} ({self.name})")
        self.send_command(f'/{self.address}TR')
        time.sleep(0.02)
        self.send_command(f'/{self.address}e7R')
        self.is_open = True

    def close(self):
        logger.debug(f"Closing shutter {self.address} ({self.name})")
        self.send_command(f'/{self.address}TR')
        time.sleep(0.02)
        self.send_command(f'/{self.address}e8R')
        self.is_open = False