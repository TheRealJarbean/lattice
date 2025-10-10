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
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self.read)
        
    def read(self):
        if not self.ser.is_open:
            logger.debug(f"Serial port {self.ser.port} is not connected, restart required")
            self.read_timer.stop()
            return
        
        try:
            if self.ser.in_waiting:
                self.mutex.lock()
                try:
                    raw_data = self.ser.read(self.ser.in_waiting)
                    message = raw_data.decode('utf-8', errors='ignore').strip()
                    if message:
                        self.data_received.emit(message)
                except Exception as e:
                    print(f"Serial read error: {e}")
                    self.mutex.unlock()
        except serial.SerialException as e:
            logger.error(e)
    
    def start(self):
        if not self.read_timer.isActive():
            self.read_timer.start(20)
    
    def stop(self):
        if self.read_timer.isActive():
            self.read_timer.stop()