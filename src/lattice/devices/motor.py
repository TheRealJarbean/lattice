from PySide6.QtCore import QMutex, QObject, Signal, QThread, Slot, QTimer
import logging
import serial
import time

logger = logging.getLogger(__name__)

class Motor(QObject):
    _send_command = Signal(str) # Command
    new_serial_data = Signal(str) # Data

    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread):
        super().__init__()

        self.enabled = True
        self.in_motion = False
        self.gear_ratio = 1

        # Create command buffer
        self.command_buffer = []
        self.command_timer = QTimer(self)
        self.command_timer.timeout.connect(self._send_next_command)
        self.command_timer.start(50)

        # Create worker, can be overridden by child classes
        # to add different worker functionality
        self.worker = MotorWorker(name, address, ser, serial_mutex)

        # Set class attributes
        self.name = name
        self.address = address

        # Connect signals
        self._send_command.connect(self.worker._send_command)
        self.worker.new_serial_data.connect(self._new_serial_data)
        self.worker.in_motion_changed.connect(self._update_in_motion)

        # Move worker to its own thread
        self.worker.moveToThread(worker_thread)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def home(self):
        logger.debug(f"Homing motor {self.name}")
        self.send_command("Z1000000R")

    def zero(self):
        self.send_command("z0R")

    def set_holding_torque(self, holding_torque_percent:int):
        if not 0 <= holding_torque_percent <= 50:
            logger.error(f"Holding torque {holding_torque_percent} outside of supported range (0-50)")
        self.send_command(f"m{holding_torque_percent}R")

    def go_to_position(self, microsteps:int):
        m = int(microsteps * self.gear_ratio)
        self.send_command(f"A{m}R")

    def go_to_position_deg(self, degrees:float):
        self.go_to_position(self.degrees_to_microsteps(degrees))

    def degrees_to_microsteps(self, deg: float):
            # 1 rotation = 360 degrees = 51200 microsteps
            return int(deg * 51200 / 360)
    
    def rpm_to_microsteps_per_second(self, rpm: float):
        # 1 rpm = 1 rotation / 60 seconds =  51200 microsteps / 60 seconds
        return int(rpm * 51200 / 60)

    def set_speed_microsteps_per_second(self, speed):
        s = int(speed * self.gear_ratio)
        self.send_command(f"V{s}R")

    def set_speed_rpm(self, rpm):
        self.set_speed_microsteps_per_second(self.rpm_to_microsteps_per_second(rpm))

    def step_clockwise_microsteps(self, microsteps):
        m = int(microsteps * self.gear_ratio)
        self.send_command(f"P{m}R")

    def step_counterclockwise_microsteps(self, microsteps):
        m = int(microsteps * self.gear_ratio)
        self.send_command(f"D{m}R")

    def step_clockwise_degrees(self, deg):
        self.step_clockwise_microsteps(self.degrees_to_microsteps(deg))

    def step_counterclockwise_degrees(self, deg):
        self.step_counterclockwise_microsteps(self.degrees_to_microsteps(deg))



    def send_command(self, command: str):
        """
        Only include the commands themselves.
        Command prefix (/[address]) and line endings are added automatically.
        """
        self.command_buffer.append(command)

    def _send_next_command(self):
        if not self.enabled:
            return

        if self.in_motion:
            return

        if len(self.command_buffer) == 0:
            return

        self.in_motion = True
        command = self.command_buffer.pop(0)
        logger.debug(f"Sending command {command}")
        self._send_command.emit(command)

    @Slot(str)
    def _new_serial_data(self, data):
        self.new_serial_data.emit(data)

    @Slot(bool)
    def _update_in_motion(self, in_motion):
        self.in_motion = in_motion

class MotorWorker(QObject):
    new_serial_data = Signal(str) # data

    # whether the motor is in motion or not
    # should only ever emit false as the motor controller will set its
    # internal value to true before requesting a command run to prevent
    # race conditions
    in_motion_changed = Signal(bool)

    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex):
        super().__init__()
        
        self.name = name
        self.address = address
        self.ser = ser
        self.serial_mutex = serial_mutex
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

        self.in_motion_changed.emit(False)

        time.sleep(0.1)

    @Slot(str)
    def send_command(self, command):
        self.data_mutex.lock()
        address = self.address
        self.data_mutex.unlock()
        
        self._send_command(f'/{address}{command}')