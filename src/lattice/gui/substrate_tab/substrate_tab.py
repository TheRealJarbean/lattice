from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QFrame
)
from PySide6.QtCore import (
    QLine,
    Qt
)
from PySide6.QtGui import (
    QFont
)
import logging
import sys

# Local imports
from lattice.gui.substrate_tab.rotation_layout import RotationLayout
from lattice.gui.substrate_tab.loading_layout import LoadingLayout
from lattice.gui.substrate_tab.jogging_layout import JoggingLayout
from lattice.gui.widgets.camera_preview_widget import CameraPreview
from lattice.devices.substrate_axis import SubstrateAxis
from lattice.devices.motor import Motor

logger = logging.getLogger(__name__)

class SubstrateTab(QWidget):
    def __init__(self, substrate_motor:SubstrateAxis=None, loading_motor:Motor=None):
        super().__init__()
        self.substrate_motor = substrate_motor
        self.loading_motor = loading_motor
        self.loading_motor_gear_ratio = 45
        self.substrate_motor_gear_ratio = 4
        self.substrate_rotation_speed = 0

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
        col = QVBoxLayout()
        col.addWidget(CameraPreview(0, width=480, height=270))
        row.addLayout(col)

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
        self.jogging.home_button.clicked.connect(lambda: self.get_selected_motor().home())
        self.jogging.continuous_stop_button.clicked.connect(lambda: self.get_selected_motor().send_command("TR"))
        # TODO: Continuous jogging

    def loading_go(self, degrees):
        self.loading_motor.send_command(f"P{self.loading_deg_to_microsteps(degrees)}")

    def loading_deg_to_microsteps(self, deg: float):
        # 1 rotation = 360 degrees = 51200 microsteps
        microsteps_unadjusted = int(deg * 51200 / 360)

        # Multiply by gear ratio
        return microsteps_unadjusted * self.loading_motor_gear_ratio

    def substrate_deg_to_microsteps(self, deg: float):
        # 1 rotation = 360 degrees = 51200 microsteps
        microsteps_unadjusted = int(deg * 51200 / 360)

        # Multiply by gear ratio
        return microsteps_unadjusted * self.substrate_motor_gear_ratio

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
        self.substrate_rotation_speed = microsteps_unadjusted * self.substrate_motor_gear_ratio

    def step_motor(self, clockwise=True):
        # Loading/unloading
        motor = self.get_selected_motor()

        if self.jogging.increment_units.currentText() == "Degrees":
            deg = self.jogging.increment_input.value()
            raw_distance = self.substrate_deg_to_microsteps(deg) if motor == self.substrate_motor else self.loading_deg_to_microsteps(deg)
        else:
            raw_distance = self.jogging.increment_input.value()

        distance = raw_distance * self.substrate_motor_gear_ratio if motor == self.substrate_motor else raw_distance * self.loading_motor_gear_ratio

        if clockwise:
            motor.send_command(f"P{distance}R")
            return

        motor.send_command(f"D{distance}R")

    def get_selected_motor(self) -> Motor|SubstrateAxis:
        if self.jogging.toggle_switch.isChecked():
            return self.loading_motor

        return self.substrate_motor

if __name__ == "__main__":
    # Override logging to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    font = QFont()
    font.setPointSize(14)
    font.setBold(True)
    app.setFont(font)

    window = QWidget()
    layout = QVBoxLayout()
        
    substrate_tab = SubstrateTab()
    layout.addWidget(substrate_tab)
    
    window.setLayout(layout)
    window.setWindowTitle("Substrate Tab Widget")
    window.show()
    sys.exit(app.exec())