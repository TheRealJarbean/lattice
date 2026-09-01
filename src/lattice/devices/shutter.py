from PySide6.QtCore import QMutex, Signal, QThread
import logging
import serial

# Local imports
from lattice.devices.motor import Motor

logger = logging.getLogger(__name__)

class Shutter(Motor):
    # External signals
    is_open_changed = Signal(bool) # State
   
    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread):
        super().__init__(name, address, ser, serial_mutex, worker_thread)

    def open(self):
        logger.debug(f"Opening shutter {self.address} ({self.name})")
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e7R')
        self.is_open_changed.emit(True)

    def close(self):
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e8R')
        self.is_open_changed.emit(False)

    def reset(self):
        self.send_command(f'/{self.address}TR')
        self.send_command(f'/{self.address}e0R')
        self.is_open_changed.emit(False)