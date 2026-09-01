from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton
)
from PySide6.QtCore import (
    QLine,
    Qt,
    QMutex,
    QThread
)
from PySide6.QtGui import (
    QFont
)
import logging
import sys
import serial
import time

# Local imports
from lattice.gui.substrate_tab.rotation_layout import RotationLayout
from lattice.gui.substrate_tab.loading_layout import LoadingLayout
from lattice.gui.substrate_tab.jogging_layout import JoggingLayout
from lattice.gui.widgets.camera_preview_widget import CameraPreview
from lattice.devices.substrate_axis import SubstrateAxis
from lattice.devices.motor import Motor

logger = logging.getLogger(__name__)

LOADING_MOTOR_GEAR_RATIO = 45
SUBSTRATE_MOTOR_GEAR_RATIO = 4
MAX_LOADING_MOTOR_MICROSTEPS = (51200 / 2) * LOADING_MOTOR_GEAR_RATIO

class SubstrateTab(QWidget):
    def __init__(self, substrate_motor:SubstrateAxis=None, loading_motor:Motor=None):
        super().__init__()
        self.substrate_motor = substrate_motor
        self.loading_motor = loading_motor
        self.substrate_rotation_speed = 0
        self.loading_motor_position = 0

        layout = QVBoxLayout()

        self.loading = LoadingLayout()
        self.rotation = RotationLayout()
        self.jogging = JoggingLayout()

        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)
        left_layout.addSpacing(20)
        left_layout.addLayout(self.rotation)
        left_layout.addSpacing(20)

        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.addSpacing(20)
        right_layout.addLayout(self.loading)
        right_layout.addSpacing(20)

        row = QHBoxLayout()
        row.addWidget(left_container, stretch=1)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        row.addWidget(line)
        row.addWidget(right_container, stretch=1)
        layout.addLayout(row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        layout.addSpacing(20)

        row = QHBoxLayout()
        row.addLayout(self.jogging)

        row.addStretch()
        subrow = QHBoxLayout()
        self.camera_preview_1 = CameraPreview(0, width=480, height=270)
        self.camera_preview_2 = CameraPreview(1, width=480, height=270)
        subrow.addWidget(self.camera_preview_1)
        subrow.addWidget(self.camera_preview_2)
        row.addLayout(subrow)

        layout.addLayout(row)

        self.setLayout(layout)

        ####################
        # CONNECT CONTROLS #
        ####################

        # Loading/unloading
        self.loading.stop_button.clicked.connect(lambda: self.loading_motor.send_command("TR"))
        self.loading.load_go_button.clicked.connect(lambda: self.loading_go(self.loading.load_angle.value()))
        self.loading.growth_go_button.clicked.connect(lambda: self.loading_go(self.loading.growth_angle.value()))
        self.loading.flux_go_button.clicked.connect(lambda: self.loading_go(self.loading.flux_angle.value()))

        # Substrate rotation
        self.rotation.rheed_angles_button.clicked.connect(lambda: self.set_rheed_angles(self.rotation.rheed_angles_input.text()))
        self.rotation.speed_button.clicked.connect(lambda: self.set_substrate_motor_speed(self.rotation.speed_input.text()))
        self.rotation.start_button.clicked.connect(lambda: self.substrate_motor.send_command(f"P0V{self.substrate_rotation_speed}R"))
        self.rotation.stop_button.clicked.connect(lambda: self.substrate_motor.send_command("TR"))

        # Jogging
        self.jogging.increment_cw_button.clicked.connect(lambda: self.step_motor(clockwise=True))
        self.jogging.increment_ccw_button.clicked.connect(lambda: self.step_motor(clockwise=False))
        self.jogging.home_button.clicked.connect(lambda: self.home_motor(self.get_selected_motor()))
        self.jogging.continuous_stop_button.clicked.connect(lambda: self.get_selected_motor().send_command("TR"))
        # TODO: Continuous jogging
        
        self.loading_motor.new_serial_data.connect(lambda data: print(data))

    def loading_go(self, degrees):
        self.loading_motor.send_command(f"A{self.loading_deg_to_microsteps(degrees)}R")

    def loading_deg_to_microsteps(self, deg: float):
        print(f"DEGREES: {deg}")
        # 1 rotation = 360 degrees = 51200 microsteps
        microsteps_unadjusted = int(deg * 51200 / 360)

        # Multiply by gear ratio
        print(f"FINAL MICROSTEPS: {microsteps_unadjusted * LOADING_MOTOR_GEAR_RATIO}")
        return microsteps_unadjusted * LOADING_MOTOR_GEAR_RATIO

    def substrate_deg_to_microsteps(self, deg: float):
        # 1 rotation = 360 degrees = 51200 microsteps
        microsteps_unadjusted = int(deg * 51200 / 360)

        # Multiply by gear ratio
        return microsteps_unadjusted * SUBSTRATE_MOTOR_GEAR_RATIO

    def set_rheed_angles(self, input: str):
        if input == "":
            self.substrate_motor.set_positions_deg([])
            return
        
        positions_str = input.split(',')
        positions = [int(pos) for pos in positions_str]
        self.substrate_motor.set_positions_deg(positions)

    def set_substrate_motor_speed(self, rotations_per_min):
        # 1 rotation / min = 1/60 rotation / sec = (1/60 * 51200) microsteps / sec
        microsteps_unadjusted = int(51200/60 * rotations_per_min)

        # Adjust for gear ratio
        self.substrate_rotation_speed = microsteps_unadjusted * SUBSTRATE_MOTOR_GEAR_RATIO

    def step_motor(self, clockwise=True):
        # Loading/unloading
        motor = self.get_selected_motor()

        if self.jogging.increment_units.currentText() == "Degrees":
            deg = self.jogging.increment_input.value()
            if deg == 0:
                return
            distance = self.substrate_deg_to_microsteps(deg) if motor == self.substrate_motor else self.loading_deg_to_microsteps(deg)
        else:
            msteps = self.jogging.increment_input.value()
            if msteps == 0:
                return
            distance = msteps * SUBSTRATE_MOTOR_GEAR_RATIO if motor == self.substrate_motor else msteps * LOADING_MOTOR_GEAR_RATIO

        print(f"MAXIMUM: {MAX_LOADING_MOTOR_MICROSTEPS}")
        if clockwise:
            if motor == self.substrate_motor:
                motor.send_command(f"V20000P{distance}R")
                return

            # Loading motor
            pos = MAX_LOADING_MOTOR_MICROSTEPS
            if not (distance + self.loading_motor_position) > MAX_LOADING_MOTOR_MICROSTEPS:
                pos = distance + self.loading_motor_position

            motor.send_command(f"V20000A{int(pos)}R")
            self.loading_motor_position = pos
            return

        if motor == self.substrate_motor:
            motor.send_command(f"V20000D{distance}R")
            return

        # Loading motor
        pos = 0
        if not (self.loading_motor_position - distance) < 0:
            pos = self.loading_motor_position - distance

        motor.send_command(f"V20000A{int(pos)}R")
        self.loading_motor_position = pos

    def get_selected_motor(self) -> Motor|SubstrateAxis:
        if self.jogging.toggle_switch.isChecked():
            print("LOADING MOTOR SELECTED")
            return self.loading_motor

        return self.substrate_motor

    def synchronize_loading_motor_position(self):
        # TODO: Connect this to new_serial data and do it
        pass

    def home_motor(self, motor:SubstrateAxis|Motor):
        if motor==self.loading_motor:
            self.loading_motor_position = 0

        motor.home()

if __name__ == "__main__":
    # Override logging to DEBUG
    logging.basicConfig(level=logging.DEBUG)

    motor_thread = QThread()

    ser = serial.Serial(
        port="COM3", 
        baudrate=9600,
        timeout=0.1
        )
    
    serial_mutex = QMutex()

    loading_motor = Motor(
        name="Loading Motor",
        address=4,
        ser=ser,
        serial_mutex=serial_mutex,
        worker_thread=motor_thread
    )

    motor_thread.start()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    font = QFont()
    font.setPointSize(14)
    font.setBold(True)
    app.setFont(font)

    window = QWidget()
    layout = QVBoxLayout()
        
    substrate_tab = SubstrateTab(substrate_motor=loading_motor)
    layout.addWidget(substrate_tab)
    
    window.setLayout(layout)
    window.setWindowTitle("Substrate Tab Widget")
    window.show()
    sys.exit(app.exec())