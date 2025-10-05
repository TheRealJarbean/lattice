from PySide6.QtCore import QThread, Signal, QMutex
import serial
import logging

logger = logging.getLogger(__name__)

class SerialReader(QThread):
    data_received = Signal(str)
    
    def __init__(self, ser: serial.Serial, mutex: QMutex):
        super().__init__()
        self.ser = ser
        self.mutex = mutex
        
    def run(self):
        self._is_running = True
        while self._is_running:
            self.data_received.emit("Hello!")
            self.msleep(1000)
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
            self.msleep(10) # Let other threads run
            
    def stop(self):
        self._is_running = False