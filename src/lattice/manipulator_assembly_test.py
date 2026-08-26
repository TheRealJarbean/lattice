import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QStackedWidget, QHeaderView, QMenu, QSpinBox, QMainWindow, QGridLayout, QLineEdit, QSplitter, QDoubleSpinBox, QFrame
)
from PySide6.QtCore import Qt, QThread, QMutex, Slot
import yaml
import serial
import logging

from lattice.devices import SubstrateAxis, Motor

logger = logging.getLogger(__name__)

class HLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

class VLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)

class AxisControls(QWidget):
    def __init__(self, motor_address:int, motor_thread:QThread, serial_port:str, parent=None):
        super().__init__(parent)
        self.current_pos_microsteps = -1
        self.max_pos_microsteps = 25600
        self.min_pos_microsteps = 0
        
        try:
            ser = serial.Serial(
                port=serial_port, 
                baudrate=9600,
                timeout=0.1
                )
        except serial.SerialException as e:
            logger.error(f"Unable to open serial port {serial_port}: {e}")
            return
        ser_mutex = QMutex()
        self.motor = Motor(
            name=f"Axis {motor_address} Motor",
            address=motor_address,
            ser=ser,
            serial_mutex=ser_mutex,
            worker_thread=motor_thread
        )

        self.holding_torque_input = QSpinBox(minimum=0, maximum=50)
        holding_torque_set_button = QPushButton("SET")
        holding_torque_set_button.clicked.connect(self.set_holding_torque)

        zero_button = QPushButton("ZERO POS")
        zero_button.clicked.connect(self.zero)

        self.jog_size_deg_input = QDoubleSpinBox(minimum=0)
        self.jog_speed_input_rpm = QDoubleSpinBox(minimum=0)
        jog_positive_button = QPushButton("JOG CW")
        jog_positive_button.clicked.connect(self.jog_positive)
        jog_negative_button = QPushButton("JOG CCW")
        jog_negative_button.clicked.connect(self.jog_negative)

        # Layout widgets
        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel(f"{self.motor.name}", alignment=Qt.AlignmentFlag.AlignHCenter))
        main_layout.addStretch()

        layout = QGridLayout()
        layout.addWidget(QLabel("Holding Torque:"), 0, 0)
        layout.addWidget(self.holding_torque_input, 0, 1)
        layout.addWidget(holding_torque_set_button, 0, 2)

        layout.addWidget(zero_button, 1, 2)

        layout.addWidget(QLabel("Jog Step Size (deg)"), 2, 1)
        layout.addWidget(self.jog_size_deg_input, 2, 2)

        layout.addWidget(QLabel("Jog Velocity (RPM)"), 3, 1)
        layout.addWidget(self.jog_speed_input_rpm, 3, 2)

        layout.addWidget(jog_positive_button, 4, 1)
        layout.addWidget(jog_negative_button, 4, 2)

        main_layout.addLayout(layout)
        main_layout.addStretch()

        self.setLayout(main_layout)


    def set_holding_torque(self):
        self.motor.set_holding_torque(self.holding_torque_input.value())

    def zero(self):
        self.current_pos_microsteps = 0
        self.motor.zero()

    def jog_positive(self):
        if self.current_pos_microsteps < 0:
            logger.error("Zero motor before attempting to jog")
        
        step_size_deg = self.jog_size_deg_input.value()
        new_pos_microsteps = min(int(step_size_deg * 51200 / 360) + self.current_pos_microsteps, self.max_pos_microsteps)
        velocity = int(self.jog_speed_input_rpm.value() * 51200 / 60)
        cmd = f"V{velocity}A{new_pos_microsteps}R"
        logger.debug(cmd)
        self.motor.send_command(cmd)
        self.current_pos_microsteps = new_pos_microsteps

    def jog_negative(self):
        if self.current_pos_microsteps < 0:
            logger.error("Zero motor before attempting to jog")
        
        step_size_deg = self.jog_size_deg_input.value()
        new_pos_microsteps = max(self.current_pos_microsteps - int(step_size_deg * 51200 / 360), self.min_pos_microsteps)
        velocity = int(self.jog_speed_input_rpm.value() * 51200 / 60)
        cmd = f"V{velocity}A{new_pos_microsteps}R"
        logger.debug(cmd)
        self.motor.send_command(cmd)
        self.current_pos_microsteps = new_pos_microsteps
        

class ManipulatorTesterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manipulator Tester")
        logger.debug("Initializing...")
        main_widget = QWidget()

        ###################
        # HARDWARE CONFIG #
        ###################

        self.motor_thread = QThread()

        ser = serial.Serial(
            port="COM7", 
            baudrate=9600,
            timeout=0.1
            )
        ser_mutex = QMutex()
        self.substrate_axis = SubstrateAxis(
            name="SubstrateAxis",
            address=2,
            ser=ser,
            serial_mutex=ser_mutex,
            worker_thread=self.motor_thread,
            gear_ratio=1
        )
        axis_a = AxisControls(
            motor_address=1,
            motor_thread=self.motor_thread,
            serial_port="COM8",
            parent=main_widget
        )

        #############
        # UI CONFIG #
        #############

        main_layout = QHBoxLayout()

        substrate_layout = self.substrate_setup()
        main_layout.addStretch()
        main_layout.addLayout(substrate_layout)
        main_layout.addStretch()
        main_layout.addWidget(VLine())
        main_layout.addStretch()
        main_layout.addWidget(axis_a)
        main_layout.addStretch()

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        self.motor_thread.start()

    def substrate_setup(self):

        layout = QVBoxLayout()
        layout.addWidget(QLabel("SUBSTRATE ROTATION", alignment=Qt.AlignmentFlag.AlignHCenter))

        config_layout = QGridLayout()
        config_layout.addWidget(QLabel("RHEED Photo Angles:"), 0, 0)
        self.angles_input = QLineEdit()
        config_layout.addWidget(self.angles_input, 0, 1)
        self.angles_input_set = QPushButton("SET")
        self.angles_input_set.clicked.connect(self.set_substrate_angles)

        config_layout.addWidget(self.angles_input_set, 0, 2)

        layout.addStretch()
        layout.addLayout(config_layout)

        running_layout = QGridLayout()
        running_layout.addWidget(QLabel("RPM:"), 0, 0)
        self.rpm_input = QDoubleSpinBox()
        running_layout.addWidget(self.rpm_input, 0, 1)

        layout.addLayout(running_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        self.home_button = QPushButton("HOME")
        self.home_button.clicked.connect(self.substrate_axis.home)
        self.start_button = QPushButton("START")
        self.start_button.clicked.connect(self.substrate_axis.start)
        self.stop_button = QPushButton("STOP")
        self.stop_button.clicked.connect(self.substrate_axis.stop)
        buttons_layout.addWidget(self.home_button)
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)
        layout.addStretch()

        return layout
    
    @Slot()
    def set_substrate_angles(self):
        raw = self.angles_input.text().split(',')
        angles = [float(s.strip()) for s in raw]
        self.substrate_axis.set_positions_deg(angles)