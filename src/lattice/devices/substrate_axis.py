from PySide6.QtCore import QMutex, QObject, Signal, QThread, Slot, QTimer, QCoreApplication
import logging
import serial
import sys
import time

# Local imports
from lattice.devices.motor import Motor, MotorWorker

logger = logging.getLogger(__name__)

class SubstrateAxis(Motor):
    _go_to_position_deg = Signal(int, float) # position number, degrees
    _set_velocity = Signal(int) #
    position_reached = Signal(int, float) # position number, degrees

    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread, gear_ratio:float=1):
        self.gear_ratio = gear_ratio
        super().__init__(name, address, ser, serial_mutex, worker_thread)
        self.current_pos = -1
        self.running = False
        self.positions_deg = []

        # Connect worker signals
        self.worker.position_reached.connect(self.on_pos_reached)

        # Connect own signals
        self._go_to_position_deg.connect(self.worker.go_to_position_deg)

    def create_worker(self, name, address, ser, serial_mutex):
        return SubstrateAxisWorker(name, address, ser, serial_mutex, self.gear_ratio)
    
    def set_positions_deg(self, positions_deg:list[float]):
        self.positions_deg = positions_deg
    
    def start(self):
        if self.running:
            return
        
        # Assume motor is homed
        self.current_pos = -1
        self.running = True
        self.go_to_next_pos()
    
    def stop(self):
        if not self.running:
            return
        
        self.running = False
    
    def go_to_next_pos(self):
        if not self.running:
            return
        
        next_pos = self.current_pos + 1 if -1 <= self.current_pos + 1 <= len(self.positions_deg) else 0
        logger.debug(next_pos)
        self._go_to_position_deg.emit(next_pos, self.positions_deg[next_pos])

    @Slot(int)
    def on_pos_reached(self, pos_number:int):
        logger.debug(f"Substrate Axis reached position {pos_number} | {self.positions_deg[pos_number]} deg")
        QTimer.singleShot(1000, self.go_to_next_pos)


class SubstrateAxisWorker(MotorWorker):
    position_reached = Signal(int) # position number

    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, gear_ratio:float=1):
        super().__init__(name, address, ser, serial_mutex)
        self.gear_ratio = gear_ratio
        self.new_serial_data.connect(self.check_for_pos)

    def degrees_to_microsteps(self, deg: float):
        # 1 rotation = 360 degrees = 51200 microsteps
        return int(deg * 51200 / 360)
    
    def rpm_to_microsteps_per_second(self, rpm: float):
        # 1 rpm = 1 rotation / 60 seconds =  51200 microsteps / 60 seconds
        return int(rpm * 51200 / 60)
    
    @Slot(str)
    def check_for_pos(self, res:str):
        logger.debug(f"Got a res: {res}")
        try:
            if (current_pos := int(res[-2])):
                self.position_reached.emit(current_pos)
        except ValueError:
            pass

    @Slot(int, float)
    def go_to_position_deg(self, pos_number:int, deg:float):
        microsteps = int(self.degrees_to_microsteps(deg) * self.gear_ratio)
        cmd = f"A{microsteps}p{pos_number}R"
        self.send_custom_command(cmd)