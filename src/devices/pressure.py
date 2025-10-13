from PySide6.QtCore import Signal, QMutex, QObject, Slot, QTimer
import time
import serial
import logging

# Local imports
from utils.serial_reader import SerialReader

logger = logging.getLogger(__name__)

class Pressure(QObject):
    """
    Pressure sensors currently use COM6
    Sensor names appear to be T1 I1 I2 and I3
    Appears to request updates periodically, wait 25ms for a response, and wait 10ms to loop
    """
    pressure_changed = Signal(float)
    rate_changed = Signal(float)
    is_on_changed = Signal(bool)

    def __init__(self, name, address, ser: serial.Serial, mutex: QMutex, ser_reader: SerialReader):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.mutex = mutex
        self.pressure = 0.0
        self.rate_per_second = 0.0
        self.is_on = False
        
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll)
        
        ser_reader.data_received.connect(self.handle_ser_message)
        
    @Slot(str)
    def handle_ser_message(self, msg):
        # TODO: Implement response handling
        # TODO: Emit that gauge is on if response is received
        decoded_msg = int(msg, 2).to_bytes(len(msg) // 8, 'big').decode()
        logger.debug(f"Pressure gauge {self.name} received: {decoded_msg}")
        
    def send_command(self, cmd):
        """Send a message to the serial port."""
        self.mutex.lock()
        try:
            if self.ser and self.ser.is_open:
                # Add a newline or protocol-specific ending if needed
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                time.sleep(0.01)
                logger.debug(f"{self.ser.port} O: {cmd}")
        except Exception as e:
            logger.error(f"Error in sending serial data on port {self.ser.port}: {e}")
        finally:
            self.mutex.unlock()
    
    def toggle_on_off(self):
        if self.is_on:
            logger.debug(f"Turning off gauge {self.name}")
            self.send_command(f'#0030{self.address}')
            self.is_on = False
            self.is_on_changed.emit(False)
        else:
            logger.debug(f"Turning on gauge {self.name}")
            self.send_command(f'#0031{self.address}')
            self.is_on = True
            self.is_on_changed.emit(True)

    def update_rate(self):
        new_rate = (self.rate_per_second + self.pressures) / 2
        self.rate_per_second = new_rate
        self.rate_changed.emit(new_rate)
    
    def start_polling(self):
        if not self.poll_timer.isActive():
            self.poll_timer.start(20)
    
    def stop_polling(self):
        if self.poll_timer.isActive():
            self.poll_timer.stop()

    def poll(self):
        if self.is_on:
            self.send_command(f'#0032{self.address}')
            # self.send(f'#000F') TODO: Find out what this does