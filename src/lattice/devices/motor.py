from PySide6.QtCore import QMutex, QObject, Signal, QThread, Slot, QTimer, QCoreApplication
import logging
import serial
import sys
import time

logger = logging.getLogger(__name__)

class Motor(QObject):
    _send_custom_command = Signal(str) # Command
    _enable = Signal()
    _disable = Signal()
    _home = Signal()
    _zero = Signal()
    _set_holding_torque = Signal(int) # Holding torque percent (0-50)
    new_serial_data = Signal(str) # Data

    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread):
        super().__init__()

        # Create worker, can be overridden by child classes
        # to add different worker functionality
        self.worker = self.create_worker(name, address, ser, serial_mutex)

        # Set class attributes
        self.name = name
        self.address = address

        # Connect own signals
        self._enable.connect(self.worker.enable)
        self._disable.connect(self.worker.disable)
        self._home.connect(self.worker.home)
        self._zero.connect(self.worker.zero)
        self._set_holding_torque.connect(self.worker.set_holding_torque)
        self._send_custom_command.connect(self.worker.send_custom_command)
        
        # Connect worker signals
        self.worker.new_serial_data.connect(self._new_serial_data)

        # Move worker to its own thread
        self.worker.moveToThread(worker_thread)
    
    def create_worker(self, name, address, ser, serial_mutex):
        return MotorWorker(name, address, ser, serial_mutex)

    def enable(self):
        self._enable.emit()

    def disable(self):
        self._disable.emit()

    def home(self):
        logger.debug(f"Homing motor {self.name}")
        self._home.emit()

    def zero(self):
        self._zero.emit()

    def set_holding_torque(self, holding_torque_percent:int):
        if not 0 <= holding_torque_percent <= 50:
            logger.error(f"Holding torque {holding_torque_percent} outside of supported range (0-50)")
        self._set_holding_torque.emit(holding_torque_percent)

    def send_command(self, command: str):
        logger.debug(f"Sending command {command}")
        self._send_custom_command.emit(command)

    @Slot(str)
    def _new_serial_data(self, data):
        self.new_serial_data.emit(data)

class MotorWorker(QObject):
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
         
    def _send_command(self, cmd):
        """Send a message to the serial port."""
        self.serial_mutex.lock()
        
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{cmd}\r\n".encode('utf-8'))
                
                self.data_mutex.lock()
                self.new_serial_data.emit(f"O: {cmd}")
                self.data_mutex.unlock()
                
                while (res := self.ser.readline()):
                    if res:
                        message = res.decode('utf-8', errors='ignore').strip()
                        self.new_serial_data.emit(f"I: {message}")
                        self.serial_mutex.unlock()
                        return message
                    
            except Exception as e:
                self.data_mutex.lock()
                logger.error(f"Error in sending serial data on port {self.ser.port}: {e}")
                self.data_mutex.unlock()
                
        self.serial_mutex.unlock()

        time.sleep(0.1)

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

    @Slot()
    def home(self):
        self.send_custom_command("Z1000000R")

    @Slot()
    def zero(self):
        self.send_custom_command("z0R")

    @Slot(int)
    def set_holding_torque(self, holding_torque_percent:int):
        if not 0 <= holding_torque_percent <= 50:
            logger.error(f"Holding torque {holding_torque_percent} outside of supported range (0-50)")
        self.send_custom_command(f"m{holding_torque_percent}R")

    @Slot(str)
    def send_custom_command(self, command):
        self.data_mutex.lock()
        enabled = self.enabled
        address = self.address
        name = self.name
        self.data_mutex.unlock()

        logger.debug(f"Sending custom shutter command to {address} ({name}): {command}")

        if not enabled:
            return
        
        self._send_command(f'/{address}{command}')

if __name__ == "__main__":
    app = QCoreApplication(sys.argv)

    logging.basicConfig(level=logging.DEBUG)

    ser = serial.Serial(
        port="COM7", 
        baudrate=9600,
        timeout=0.1
        )
    
    serial_mutex = QMutex()
    motor_thread = QThread()

    motor = Motor(
        name="Shutter",
        address=2,
        ser=ser,
        serial_mutex=serial_mutex,
        worker_thread=motor_thread
    )

    motor_thread.start()

    time.sleep(10)
    motor_thread.quit()
    motor_thread.wait()

    ser.close()

    app.quit()