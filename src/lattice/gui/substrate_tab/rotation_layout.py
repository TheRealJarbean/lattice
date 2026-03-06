from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QApplication,
    QLabel,
    QPushButton,
    QSpinBox,
    QAbstractSpinBox,
    QHBoxLayout,
    QSizePolicy,
    QLineEdit,
    QDial,
    QGridLayout
)
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QFont,
    QRegularExpressionValidator
)
import logging
import sys

# Local imports
from lattice.gui.substrate_tab.angle_dial import AngleDial

logger = logging.getLogger(__name__)

RED_BUTTON_STYLE = """
    QPushButton {
        background-color: rgb(200, 0, 0);
    }

    QPushButton:pressed {
        background-color: rgb(150, 0, 0);
    }
"""

GREEN_BUTTON_STYLE = """
    QPushButton {
        background-color: rgb(0, 200, 0);
    }

    QPushButton:pressed {
        background-color: rgb(0, 150, 0);
    }
"""

class RotationLayout(QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        big_font = QFont()
        big_font.setPointSize(20)
        big_font.setBold(True)

        #################################
        # CONFIGURE AND LAY OUT WIDGETS #
        #################################

        # Panel label
        self.panel_label = QLabel("SUBSTRATE ROTATION")
        self.panel_label.setFont(big_font)
        self.addWidget(self.panel_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Angle display dial
        self.addSpacing(10)
        self.angle_dial = AngleDial(read_only=True)
        self.angle_dial.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.addWidget(self.angle_dial)

        # Start and stop buttons
        self.addSpacing(10)
        self.start_button = QPushButton("START")
        self.start_button.setFixedWidth(100)
        self.start_button.setStyleSheet(GREEN_BUTTON_STYLE)

        self.stop_button = QPushButton("STOP")
        self.stop_button.setFixedWidth(100)
        self.stop_button.setStyleSheet(RED_BUTTON_STYLE)

        self.stop_angle_input = QSpinBox(minimum=0, maximum=359)
        self.stop_angle_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.stop_angle_input.setFixedWidth(50)

        # Add Start and stop buttons to layout
        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)
        left_layout.addStretch()
        left_layout.addWidget(self.start_button)

        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.addWidget(self.stop_button)
        right_layout.addWidget(self.stop_angle_input)
        right_layout.addWidget(QLabel('\u00B0'))
        right_layout.addStretch()

        row = QHBoxLayout()
        row.addWidget(left_container, stretch=1)
        row.addWidget(right_container, stretch=1)
        self.addLayout(row)

        # RHEED Stop Angles
        self.rheed_angles_input = RheedAngleInput()
        self.rheed_angles_input.setPlaceholderText("0,120,240...")

        self.rheed_angles_display = QLineEdit()
        self.rheed_angles_display.setReadOnly(True)
        
        self.rheed_angles_button = QPushButton("SET")
        self.rheed_angles_button.setFixedWidth(75)
        self.rheed_angles_button.clicked.connect(lambda: self.rheed_angles_display.setText(self.rheed_angles_input.text()))

        # Speed
        self.speed_input = QSpinBox(minimum=0, maximum=60)
        self.speed_input.setFixedWidth(50)
        self.speed_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.speed_display = QLineEdit()
        self.speed_display.setFixedWidth(50)
        self.speed_display.setReadOnly(True)

        self.speed_button = QPushButton("SET")
        self.speed_button.setFixedWidth(75)
        self.speed_button.clicked.connect(lambda: self.speed_display.setText(self.speed_input.text()))

        # Add RHEED stop angle and speed controls to layout
        self.addSpacing(10)
        grid = QGridLayout()
        # Row 0
        grid.addWidget(QLabel("RHEED Angles (\u00B0)"), 0, 1, 1, 2)
        grid.addWidget(QLabel("Speed (RPM)"), 0, 4, 1, 2)
        # Row 1
        # label = QLabel("New:")
        # grid.addWidget(label, 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.rheed_angles_input, 1, 1)
        grid.addWidget(self.rheed_angles_button, 1, 2)
        grid.addWidget(self.speed_input, 1, 4)
        grid.addWidget(self.speed_button, 1, 5)
        # Row 2
        # label = QLabel("Current:")
        # grid.addWidget(label, 2, 0, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.rheed_angles_display, 2, 1)
        grid.addWidget(self.speed_display, 2, 4)
        # Use column 3 for spacing
        grid.setColumnMinimumWidth(3, 20)

        self.addLayout(grid)

class RheedAngleInput(QLineEdit):
    def __init__(self, max_angles = 5):
        super().__init__()
        # Matches comma separated numbers between 0 and 359, leading comma accepted,
        # spaces between commmas and numbers accepted
        self.setMaxLength(100)
        number_pattern = '(0|[1-9][0-9]?|[12][0-9]{2}|3[0-5][0-9])'
        self.setValidator(QRegularExpressionValidator(regularExpression=
            f'^{number_pattern}(\\s*,\\s*{number_pattern}){{0,{max_angles-1}}}\\s*,?$'
        ))

if __name__ == "__main__":
    # Override logging to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    
    app = QApplication(sys.argv)

    font = QFont()
    font.setPointSize(14)
    font.setBold(True)
    app.setFont(font)

    window = QWidget()
    layout = QVBoxLayout()
        
    layout.addLayout(RotationLayout())
    
    window.setLayout(layout)
    window.setWindowTitle("Substrate Tab Widget")
    window.show()
    sys.exit(app.exec())