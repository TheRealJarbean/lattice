from PySide6.QtCore import QMutex, QObject, Signal, QThread, Slot, QTimer
import logging
import serial

# Local imports
from lattice.devices.motor import Motor, MotorWorker

logger = logging.getLogger(__name__)

class Shutter(Motor):
    # Internal signals
    _open = Signal()
    _close = Signal()
    _clear_open_closed_buffer = Signal()
    
    # External signals
    is_open_changed = Signal(bool) # State
   
    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread):
        super().__init__(name, address, ser, serial_mutex, worker_thread)

        self._open.connect(self.worker.open)
        self._close.connect(self.worker.close)
        self._clear_open_closed_buffer.connect(self.worker.clear_open_close_buffer)
        self.worker.is_open_changed.connect(self._is_open_changed)

    def create_worker(self, name, address, ser, serial_mutex):
        return ShutterWorker(name, address, ser, serial_mutex)

    def open(self):
        self._open.emit()

    def close(self):
        self._close.emit()

    def clear_open_close_buffer(self):
        self._clear_open_closed_buffer.emit()

    @Slot(bool)
    def _is_open_changed(self, is_open: bool):
        self.is_open_changed.emit(is_open)

class ShutterWorker(MotorWorker):
    is_open_changed = Signal(bool) # is_open
    
    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex):
        super().__init__(name, address, ser, serial_mutex)

        self.open_close_buffer = []
        self.open_close_timer = QTimer(self)
        self.open_close_timer.timeout.connect(self._execute_open_close)
        self.open_close_timer.start(50)

    @Slot()
    def open(self):
        self.data_mutex.lock()
        self.open_close_buffer.append(True)
        self.data_mutex.unlock()

    @Slot()
    def close(self):
        self.data_mutex.lock()
        self.open_close_buffer.append(False)
        self.data_mutex.unlock()

    def _execute_open_close(self):
        self.data_mutex.lock()
        enabled = self.enabled
        address = self.address
        name = self.name
        self.data_mutex.unlock()

        if not enabled:
            return
        
        if self.open_close_buffer:
            open = self.open_close_buffer.pop(0)

            if open:
                logger.debug(f"Opening shutter {address} ({name})")
                self._send_command(f'/{address}TR')
                self._send_command(f'/{address}e7R')
                self.is_open_changed.emit(True)
                return
            
            logger.debug(f"Closing shutter {address} ({name})")
            self._send_command(f'/{address}TR')
            self._send_command(f'/{address}e8R')
            self.is_open_changed.emit(False)

    def reset(self):
        self.data_mutex.lock()
        enabled = self.enabled
        address = self.address
        self.data_mutex.unlock()
        
        if not enabled:
            return
        
        self.in_motion_changed.emit(True)
        self._send_command(f'/{address}TR')
        self._send_command(f'/{address}e0R')
        self.in_motion_changed.emit(False)
        self.is_open_changed.emit(False)

    @Slot()
    def clear_open_close_buffer(self):
        self.open_close_buffer = []

class VirtualShutterWorker(ShutterWorker):
    """
    Mimicks real shutter functionality for testing, sends no commands
    """

    def __init__(self, name: str, address: int):
        super().__init__()
        self.name = name
        self.address = address
        self.enabled = True
        self.data_mutex = QMutex()

    @Slot(str) 
    def _send_command(self, cmd):
        pass

    @Slot() 
    def enable(self):
        self.data_mutex.lock()
        self.enabled = True
        self.data_mutex.unlock()
            
    @Slot()
    def disable(self):
        self.data_mutex.lock()
        self.enabled = False
        self.data_mutex.unlock()

    def reset(self):
        self.data_mutex.lock()
        enabled = self.enabled
        self.data_mutex.unlock()
        
        if not enabled:
            return
        
        self.is_open_changed.emit(self, False)

    @Slot()
    def open(self):
        self.data_mutex.lock()
        enabled = self.enabled
        self.data_mutex.unlock()
        
        if not enabled:
            return
        
        self.is_open_changed.emit(self, True)

    @Slot()
    def close(self):
        self.data_mutex.lock()
        enabled = self.enabled
        self.data_mutex.unlock()
        
        if not enabled:
            return
        
        self.is_open_changed.emit(self, False)
        
    @Slot()
    def send_custom_command(self, command):
        pass