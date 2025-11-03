from PySide6.QtCore import Signal, QMutex, QMutexLocker, QObject, Slot, QTimer
import time
import serial
import re
import logging

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
    new_serial_data = Signal(str, str) # Name, data

    def __init__(self, name, address, ser: serial.Serial, serial_mutex: QMutex):
        super().__init__()
        self.name = name
        self.address = address
        self.ser = ser
        self.pressure = 0.0
        self.rate_per_second = 0.0
        self.is_on = False
        self.ser_buffer = ""
        
        self.serial_mutex = serial_mutex
        self.data_mutex = QMutex()
        
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll)
        
    def send_command(self, cmd) -> str:
        """Send a message to the serial port."""
        self.serial_mutex.lock()
        try:
            if self.ser and self.ser.is_open:
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                
                self.data_mutex.lock()
                self.new_serial_data.emit(self.name, f"O: {cmd}")
                self.data_mutex.unlock()
                
                response = self.ser.readline()
                if response:
                    message = response.decode('utf-8', errors='ignore').strip()
                    return message
                
                return None

        except Exception as e:
            self.data_mutex.lock()
            logger.error(f"Error in sending serial data on port {self.ser.port}: {e}")
            self.data_mutex.unlock()
        finally:
            self.serial_mutex.unlock()
    
    def toggle_on_off(self):
        self.data_mutex.lock()
        is_on = self.is_on
        address = self.address
        name = self.name
        self.data_mutex.unlock()

        if is_on:
            logger.debug(f"Turning off gauge {name}")
            self.send_command(f'#0030{address}')
            self.send_command(f'#0030{address}')
            self.send_command(f'#0030{address}')

            self.data_mutex.lock()
            self.is_on = False
            self.data_mutex.unlock()

            self.is_on_changed.emit(False)
            return
        
        self.data_mutex.lock()
        self.is_on = True
        self.data_mutex.unlock()
        
        logger.debug(f"Turning on gauge {name}")
        self.is_on_changed.emit(True)
        self.send_command(f'#0031{address}')
        self.send_command(f'#0031{address}')
        self.send_command(f'#0031{address}')

    def update_rate(self):
        self.data_mutex.lock()
        new_rate = (self.rate_per_second + self.pressures) / 2
        self.rate_per_second = new_rate
        self.rate_changed.emit(new_rate)
        self.data_mutex.unlock()
    
    def start_polling(self, interval_ms: int):
        self.data_mutex.lock()
        logger.debug(f"Starting polling for gauge {self.name}")
        if not self.poll_timer.isActive():
            self.poll_timer.start(interval_ms)
        self.data_mutex.unlock()
    
    def stop_polling(self):
        self.data_mutex.lock()
        if self.poll_timer.isActive():
            self.poll_timer.stop()
        self.data_mutex.unlock()

    def poll(self):
        if not self.is_on:
            return
        
        self.data_mutex.lock()
        address = self.address
        self.data_mutex.unlock()

        # Command sent multiple times to force clear device buffer
        self.send_command(f'#0002{address}')
        self.send_command(f'#0002{address}')
        self.send_command(f'#0002{address}')
        res = self.send_command(f'#0002{address}')
        self.data_mutex.lock()
        self.new_serial_data.emit(self.name, f"I: {res}")
        self.data_mutex.unlock()
        
        res = res[1:] # trim leading >
        # Scientific notation regex
        if re.search("^[+\-]?(\d+\.\d*|\d*\.\d+|\d+)([eE][+\-]\d+)?", res):
            try:
                value = float(res)
                self.pressure_changed.emit(value)
                if value > 0:
                    self.data_mutex.lock()
                    if not self.is_on:
                        self.is_on = True
                        self.is_on_changed.emit(True)
                    self.data_mutex.unlock()
                else:
                    self.data_mutex.lock()
                    if not self.is_on:
                        self.is_on = False
                        self.is_on_changed.emit(False)
                    self.data_mutex.unlock()

            except Exception as e:
                logger.debug(f"Error in converting pressure gauge data to value: {res}")
        
    def send_custom_command(self, command):
        self.data_mutex.lock()
        address = self.address
        name = self.name
        self.data_mutex.unlock()
        
        logger.debug(f"Sending custom gauge command to {address} ({name}): {command}")
        self.send_command(f'#{command}{address}')