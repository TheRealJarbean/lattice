from PySide6.QtCore import QMutex, Signal, QThread, QTimer
import logging
import serial

# Local imports
from lattice.devices.motor import Motor

logger = logging.getLogger(__name__)

class SubstrateAxis(Motor):
    position_reached = Signal(int, float) # position number, degrees

    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread, gear_ratio:float=1):
        super().__init__(name, address, ser, serial_mutex, worker_thread)

        self.gear_ratio = gear_ratio
        self.current_pos = -1
        self.positions_deg = []
        self.running = False

        # Connect worker signals
        self.worker.new_serial_data.connect(self.check_for_pos)
    
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
        logger.debug(f"Substrate axis moving to position {next_pos}")
        self._go_to_position_deg.emit(next_pos, self.positions_deg[next_pos])

    def degrees_to_microsteps(self, deg: float):
        # 1 rotation = 360 degrees = 51200 microsteps
        return int(deg * 51200 / 360)

    def rpm_to_microsteps_per_second(self, rpm: float):
        # 1 rpm = 1 rotation / 60 seconds =  51200 microsteps / 60 seconds
        return int(rpm * 51200 / 60)

    def go_to_position_deg(self, pos_number:int, deg:float):
        microsteps = int(self.degrees_to_microsteps(deg) * self.gear_ratio)
        cmd = f"A{microsteps}p{pos_number}R"
        self.send_command(cmd)

    def check_for_pos(self, res:str):
        logger.debug(f"Got a res: {res}")
        try:
            if (current_pos := int(res[-2])):
                self.on_pos_reached(current_pos)
        except ValueError:
            pass

    def on_pos_reached(self, pos_number:int):
        logger.debug(f"Substrate Axis reached position {pos_number} | {self.positions_deg[pos_number]} deg")
        QTimer.singleShot(1000, self.go_to_next_pos)