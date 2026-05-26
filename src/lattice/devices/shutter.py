from PySide6.QtCore import QMutex, QObject, Signal, QThread, Slot, QTimer
import logging
import serial

logger = logging.getLogger(__name__)

class Shutter(QObject):
    # Internal signals
    _open = Signal()
    _close = Signal()
    _send_command = Signal(str) # Command
    _enable = Signal()
    _disable = Signal()
    _clear_open_closed_buffer = Signal()
    
    # External signals
    is_open_changed = Signal(bool) # State
    new_serial_data = Signal(str) # Data
   

    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread):
        super().__init__()

        self.name = name
        self.address = address
        self.worker = ShutterWorker(name, address, ser, serial_mutex)

        self._open.connect(self.worker.open)
        self._close.connect(self.worker.close)
        self._enable.connect(self.worker.enable)
        self._disable.connect(self.worker.disable)
        self._send_command.connect(self.worker.send_custom_command)
        self._clear_open_closed_buffer.connect(self.worker.clear_open_close_buffer)
        self.worker.is_open_changed.connect(self._is_open_changed)
        self.worker.new_serial_data.connect(self._new_serial_data)

        self.worker.moveToThread(worker_thread)

    def open(self):
        self._open.emit()

    def close(self):
        self._close.emit()

    def clear_open_close_buffer(self):
        self._clear_open_closed_buffer.emit()

    def enable(self):
        self._enable.emit()

    def disable(self):
        self._disable.emit()

    def send_command(self, command: str):
        self._send_command.emit(command)

    @Slot(bool)
    def _is_open_changed(self, is_open: bool):
        self.is_open_changed.emit(is_open)

    @Slot(str)
    def _new_serial_data(self, data):
        self.new_serial_data.emit(data)

class ShutterWorker(QObject):
    is_open_changed = Signal(bool) # is_open
    new_serial_data = Signal(str) # data
    in_motion_changed = Signal(bool) # State
    
    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.serial_mutex = serial_mutex
        self.enabled = True
        self.data_mutex = QMutex()

        self.open_close_buffer = []
        self.open_close_timer = QTimer(self)
        self.open_close_timer.timeout.connect(self._execute_open_close)
        self.open_close_timer.start(50)

    @Slot(str) 
    def send_command(self, cmd):
        """Send a message to the serial port."""
        self.serial_mutex.lock()
        
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                
                self.data_mutex.lock()
                self.new_serial_data.emit(f"O: {cmd}")
                self.data_mutex.unlock()
                
                res = self.ser.readline()
                if res:
                    message = res.decode('utf-8', errors='ignore').strip()
                    self.data_mutex.lock()
                    self.new_serial_data.emit(f"I: {message}")
                    self.data_mutex.unlock()
                    
            except Exception as e:
                self.data_mutex.lock()
                logger.error(f"Error in sending serial data on port {self.ser.port}: {e}")
                self.data_mutex.unlock()
                
        self.serial_mutex.unlock()

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
        address = self.address
        self.data_mutex.unlock()
        
        if not enabled:
            return
        
        self.in_motion_changed.emit(True)
        self.send_command(f'/{address}TR')
        self.send_command(f'/{address}e0R')
        self.in_motion_changed.emit(False)
        self.is_open_changed.emit(False)

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
                self.send_command(f'/{address}TR')
                self.send_command(f'/{address}e7R')
                self.is_open_changed.emit(True)
                return
            
            logger.debug(f"Closing shutter {address} ({name})")
            self.send_command(f'/{address}TR')
            self.send_command(f'/{address}e8R')
            self.is_open_changed.emit(False)

    @Slot()
    def clear_open_close_buffer(self):
        self.open_close_buffer = []
        
    @Slot()
    def send_custom_command(self, command):
        self.data_mutex.lock()
        enabled = self.enabled
        address = self.address
        name = self.name
        self.data_mutex.unlock()
        
        if not enabled:
            return
        
        logger.debug(f"Sending custom shutter command to {address} ({name}): {command}")
        self.send_command(f'/{address}{command}')


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
    def send_command(self, cmd):
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