from PySide6.QtCore import QMutex, Signal, QThread, QTimer
import logging
import serial

# Local imports
from lattice.devices.motor import Motor

logger = logging.getLogger(__name__)

class LoadingMotor(Motor):
    def __init__(self, name: str, address: int, ser: serial.Serial, serial_mutex: QMutex, worker_thread: QThread, gear_ratio:float=1):
        super().__init__(name, address, ser, serial_mutex, worker_thread)

        self.gear_ratio = gear_ratio
        self.max_abs_position = int(self.degrees_to_microsteps(220) * gear_ratio)
        self.has_been_homed = True # TODO: CHANGE BACK TO FALSE
        self.current_position = 0

    def home(self):
        self.send_command("V20000")
        self.send_command("f1Z1000000R", homing=True)
        self.has_been_homed = True
        self.current_position = 0

    def send_command(self, command, homing=False):
        if homing:
            # Bypass home check and polarity enforcement
            super().send_command(command)
            return

        if not self.has_been_homed:
            logger.warning("Loading motor cannot move until it has been homed.")
            return

        c = "f0" + command # Ensure polarity is correct due to homing requiring reverse
        super().send_command(c)

    def _go_to_position(self, microsteps_adjusted):
        m = microsteps_adjusted
        if m > self.max_abs_position:
            logger.warning(f"Loading motor position {m} exceeds limit of {self.max_abs_position}. Motor will move to max position.")
            m = self.max_abs_position

        if m < 0:
            logger.warning(f"Loading motor position {m} exceeds limit of 0. Motor will move to minimum position.")
            m = 0

        self.send_command(f"A{m}R")
        self.current_position = m

    def go_to_position(self, microsteps):
        m = microsteps * self.gear_ratio
        self._go_to_position(m)

    def step_clockwise_microsteps(self, microsteps):
        m = int(microsteps * self.gear_ratio)
        self._go_to_position(self.current_position + m)

    def step_counterclockwise_microsteps(self, microsteps):
        m = int(microsteps * self.gear_ratio)
        self._go_to_position(self.current_position - m)#