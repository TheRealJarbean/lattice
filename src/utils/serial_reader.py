from PySide6.QtCore import QObject, Signal, QMutex, QTimer
import serial
import logging

logger = logging.getLogger(__name__)

class SerialReader(QObject):
    data_received = Signal(str)
    
    def __init__(self, ser: serial.Serial, mutex: QMutex):
        super().__init__()
        self.ser = ser
        self.mutex = mutex
        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self.read)
        
    def read(self):
        self.mutex.lock()
        if not self.ser.is_open:
            logger.debug(f"Serial port {self.ser.port} is not connected, restart required")
            self.read_timer.stop()
            self.mutex.unlock()
            return
        
        try:
            if self.ser.in_waiting:
                try:
                    raw_data = self.ser.readline(self.ser.in_waiting)
                    if raw_data:
                        message = raw_data.decode('utf-8', errors='ignore').strip()
                        self.data_received.emit(message)
                except Exception as e:
                    print(f"Serial read error: {e}")
        except serial.SerialException as e:
            logger.error(e)
        finally:
            self.mutex.unlock()
    
    def start(self):
        if not self.read_timer.isActive():
            logger.debug("Starting reader!")
            self.read_timer.start(20)
    
    def stop(self):
        if self.read_timer.isActive():
            self.read_timer.stop()