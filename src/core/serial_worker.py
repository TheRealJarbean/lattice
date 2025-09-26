# Base class for all devices using serial I/O, defines common communication parameters
from PySide6.QtCore import QObject, Slot, Signal
import serial
import time

class SerialWorker(QObject):
    response_received = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()

    def __init__(self, port: str, baudrate: int = 9600):
        super().__init__()
        self._running = False
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    @Slot()
    def start_worker(self):
        """Start the serial connection and event loop"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout = 0.1)
            self._running = True
            while self._running:
                if self.ser.in_waiting:
                    data = self.ser.readline().decode(errors='ignore').strip()
                    if data:
                        self.response_received.emit(data)
                time.sleep(0.01) # Prevent CPU hogging
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.finished.emit()

    @Slot()
    def send_message(self, msg):
        """Send a message to the serial port."""
        if self.ser and self.ser.is_open:
            try:
                # Add a newline or protocol-specific ending if needed
                self.ser.write(msg.encode('utf-8'))
            except Exception as e:
                self.error_occurred.emit(f"Send error: {e}")

    @Slot()
    def stop_worker(self):
        """Stop the worker thread gracefully."""
        self._running = False