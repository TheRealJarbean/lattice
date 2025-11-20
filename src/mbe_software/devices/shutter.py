from PySide6.QtCore import QMutex, QObject, Signal, QMutexLocker, Slot
import time
import logging
import serial

logger = logging.getLogger(__name__)

class Shutter(QObject):
    is_open_changed = Signal(object, bool) # Reference to self, is_open
    new_serial_data = Signal(str, str) # Name, data
    
    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.serial_mutex = serial_mutex
        self.enabled = True
        self.data_mutex = QMutex()
        
    def send_command(self, cmd):
        """Send a message to the serial port."""
        self.serial_mutex.lock()
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                
                self.data_mutex.lock()
                self.new_serial_data.emit(self.name, f"O: {cmd}")
                self.data_mutex.unlock()
                
                res = self.ser.readline()
                if res:
                    message = res.decode('utf-8', errors='ignore').strip()
                    self.data_mutex.lock()
                    self.new_serial_data.emit(self.name, f"I: {message}")
                    self.data_mutex.unlock()
                    
            except Exception as e:
                self.data_mutex.lock()
                logger.error(f"Error in sending serial data on port {self.ser.port}: {e}")
                self.data_mutex.unlock()
                
        self.serial_mutex.unlock()
        
    def enable(self):
        self.data_mutex.lock()
        self.enabled = True
        self.data_mutex.unlock()
            
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
        
        self.send_command(f'/{address}TR')
        self.send_command(f'/{address}e0R')
        self.is_open_changed.emit(self, False)

    @Slot()
    def open(self, shutter=None):
        """
        DO NOT CALL THIS METHOD DIRECTLY FROM MAIN THREAD
        """
        if shutter is not self:
            return

        self.data_mutex.lock()
        enabled = self.enabled
        address = self.address
        name = self.name
        self.data_mutex.unlock()
        
        if not enabled:
            return
            
        logger.debug(f"Opening shutter {address} ({name})")
        self.send_command(f'/{address}TR')
        self.send_command(f'/{address}e7R')
        self.is_open_changed.emit(self, True)

    @Slot()
    def close(self, shutter=None):
        """
        DO NOT CALL THIS METHOD DIRECTLY FROM MAIN THREAD
        """
        if shutter is not self:
            return
        
        self.data_mutex.lock()
        enabled = self.enabled
        address = self.address
        name = self.name
        self.data_mutex.unlock()
        
        if not enabled:
            return
            
        logger.debug(f"Closing shutter {address} ({name})")
        self.send_command(f'/{address}TR')
        self.send_command(f'/{address}e8R')
        self.is_open_changed.emit(self, False)
        
    @Slot()
    def send_custom_command(self, command, shutter=None):
        """
        DO NOT CALL THIS METHOD DIRECTLY FROM MAIN THREAD
        """
        if shutter is not self:
            return
        
        self.data_mutex.lock()
        enabled = self.enabled
        address = self.address
        name = self.name
        self.data_mutex.unlock()
        
        if not enabled:
            return
        
        logger.debug(f"Sending custom shutter command to {address} ({name}): {command}")
        self.send_command(f'/{address}{command}')