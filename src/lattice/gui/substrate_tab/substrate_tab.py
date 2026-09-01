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
from lattice.devices import DEVICES, LoadingMotor, SubstrateMotor

logger = logging.getLogger(__name__)

class SubstrateTab(QWidget):
    def __init__(self):
        super().__init__()
        self.substrate_motor = DEVICES.substrate_motor
        self.loading_motor = DEVICES.loading_motor

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
        self.rotation.speed_button.clicked.connect(lambda: self.set_substrate_motor_speed(int(self.rotation.speed_input.text())))
        self.rotation.start_button.clicked.connect(lambda: self.substrate_motor.send_command(f"P0V{self.substrate_rotation_speed}R"))
        self.rotation.stop_button.clicked.connect(lambda: self.substrate_motor.send_command("TR"))

        # Jogging
        self.jogging.increment_cw_button.clicked.connect(lambda: self.step_motor(clockwise=True))
        self.jogging.increment_ccw_button.clicked.connect(lambda: self.step_motor(clockwise=False))
        self.jogging.home_button.clicked.connect(lambda: self.home_motor(self.get_selected_motor()))
        self.jogging.continuous_stop_button.clicked.connect(lambda: self.get_selected_motor().send_command("TR"))
        # TODO: Continuous jogging
        
        self.loading_motor.new_serial_data.connect(lambda data: print(data))

    def loading_go(self, angle):
        self.loading_motor.go_to_position_deg(angle)

    def set_rheed_angles(self, input: str):
        if input == "":
            self.substrate_motor.set_positions_deg([])
            return
        
        positions_str = input.split(',')
        positions = [int(pos) for pos in positions_str]
        self.substrate_motor.set_positions_deg(positions)

    def set_substrate_motor_speed(self, rpm):
        self.substrate_motor.set_speed_rpm(rpm)

    def step_motor(self, clockwise=True):
        # Loading/unloading
        motor = self.get_selected_motor()

        if self.jogging.increment_units.currentText() == "Degrees":
            deg = self.jogging.increment_input.value()
            if deg == 0:
                return

            if clockwise:
                motor.step_clockwise_degrees(deg)
                return

            motor.step_counterclockwise_degrees(deg)
            return

        # Microsteps
        msteps = self.jogging.increment_input.value()
        if msteps == 0:
            return

        if clockwise:
            motor.step_clockwise_microsteps(msteps)
            return

        motor.step_counterclockwise_microsteps(msteps)

    def get_selected_motor(self) -> LoadingMotor|SubstrateMotor:
        if self.jogging.toggle_switch.isChecked():
            print("LOADING MOTOR SELECTED")
            return self.loading_motor

        return self.substrate_motor

    def synchronize_loading_motor_position(self):
        # TODO: Connect this to new_serial data and do it
        pass

    def home_motor(self, motor:SubstrateMotor|LoadingMotor):
        motor.home()