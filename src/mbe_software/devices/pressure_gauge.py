from PySide6.QtCore import Signal, QMutex, QObject, Slot, QTimer, QThread
import time
import serial
import re
import logging

logger = logging.getLogger(__name__)

class PressureGauge(QObject):
    """
    Pressure sensors currently use COM6
    Sensor names appear to be T1 I1 I2 and I3
    Appears to request updates periodically, wait 25ms for a response, and wait 10ms to loop
    """
    pressure_changed = Signal(float, int) # Value, idx
    rate_changed = Signal(float, int) # Value, idx
    is_on_changed = Signal(bool, int) # State, idx
    new_serial_data = Signal(str, str) # Name, data

    def __init__(self, name, address, idx, ser: serial.Serial, serial_mutex: QMutex):
        super().__init__()
        self.name = name
        self.address = address
        self.idx = idx
        self.ser = ser
        self.rate_per_second = 0.0
        self.is_on = False
        self.ser_buffer = ""
        
        self.serial_mutex = serial_mutex
        self.data_mutex = QMutex()
        
        self.is_polling = False
        self.polling_interval_ms = 1000
        
    def send_command(self, cmd) -> str:
        """Send a message to the serial port."""
        self.serial_mutex.lock()
        try:
            if self.ser and self.ser.is_open:
                # Clear buffers
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                
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
            logger.exception(f"Error in sending serial data on port {self.ser.port}: {e}")
            self.data_mutex.unlock()
        finally:
            self.serial_mutex.unlock()
    
    @Slot()
    def toggle_on_off(self):
        self.data_mutex.lock()
        is_on = self.is_on
        address = self.address
        name = self.name
        self.data_mutex.unlock()

        if is_on:
            logger.debug(f"Turning off gauge {name}")
            self.send_command(f'#0030{address}')

            self.data_mutex.lock()
            self.is_on = False
            self.data_mutex.unlock()

            self.is_on_changed.emit(False, self.idx)
            self.pressure_changed.emit(0, self.idx)
            self.rate_per_second = None
            self.rate_changed.emit(0, self.idx)
            return
        
        self.data_mutex.lock()
        self.is_on = True
        self.data_mutex.unlock()
        
        logger.debug(f"Turning on gauge {name}")
        self.is_on_changed.emit(True, self.idx)
        self.send_command(f'#0031{address}')
    
    @Slot()
    def start_polling(self, gauge, polling_interval_ms: int):
        if gauge is not self:
            return
        
        self.data_mutex.lock()
        logger.debug(f"Starting polling for gauge {self.name}")
        self.polling_interval_ms = polling_interval_ms
        self.is_polling = True
        QTimer.singleShot(0, self._poll)
        self.data_mutex.unlock()
    
    @Slot()
    def stop_polling(self, gauge):
        if gauge is not self:
            return
        
        self.data_mutex.lock()
        logger.debug(f"Stopping polling for gauge {self.name}")
        self.is_polling = False
        self.data_mutex.unlock()
        
    def _poll(self):
        self.data_mutex.lock()
        is_polling = self.is_polling
        self.data_mutex.unlock()
        
        if not is_polling:
            return
        
        # Poll and ensure interval if calls are faster
        poll_start_time = time.monotonic()
        self.poll()
        elapsed_time = time.monotonic() - poll_start_time
        delay = max(self.polling_interval_ms - elapsed_time, 0)
        QTimer.singleShot(delay, self._poll)

    def poll(self):
        self.data_mutex.lock()
        address = self.address
        self.data_mutex.unlock()

        res = self.send_command(f'#0002{address}')
        if not res:
            return
        
        self.data_mutex.lock()
        self.new_serial_data.emit(self.name, f"I: {res}")
        self.data_mutex.unlock()
        
        res = res[1:] # trim leading >
        # Scientific notation regex
        if re.search("^[+\-]?(\d+\.\d*|\d*\.\d+|\d+)([eE][+\-]\d+)?", res):
            try:
                value = float(res)
                self.pressure_changed.emit(value, self.idx)
                if value > 0:
                    self.data_mutex.lock()
                    if not self.is_on:
                        self.is_on = True
                        self.is_on_changed.emit(True, self.idx)
                    self.data_mutex.unlock()
                else:
                    self.data_mutex.lock()
                    if not self.is_on:
                        self.is_on = False
                        self.is_on_changed.emit(False, self.idx)
                    self.data_mutex.unlock()
                
                # Update rate per second
                if self.rate_per_second:
                    self.rate_per_second = (self.rate_per_second + value) / 2
                else:
                    self.rate_per_second = value
                
                self.rate_changed.emit(self.rate_per_second, self.idx)
                self.update_rate = False

            except Exception as e:
                logger.debug(f"Error in converting pressure gauge data to value: {res}")
        
    def send_custom_command(self, command):
        self.data_mutex.lock()
        address = self.address
        name = self.name
        self.data_mutex.unlock()
        
        logger.debug(f"Sending custom gauge command to {address} ({name}): {command}")
        self.send_command(f'#{command}{address}')