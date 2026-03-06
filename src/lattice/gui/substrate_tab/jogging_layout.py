from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QApplication,
    QLabel,
    QPushButton,
    QSpinBox,
    QAbstractSpinBox,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox
)
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QFont,
)
import logging
import sys

# Local imports
from lattice.definitions import ROOT_DIR

logger = logging.getLogger(__name__)

ASSETS_DIR = ROOT_DIR / "gui" / "assets"

TOGGLE_SWITCH_STYLE = (f"""
    QCheckBox {{
        spacing: 0px;
    }}

    QCheckBox::indicator {{
        width: 60px;
        height: 60px;
    }}                 

    QCheckBox::indicator:unchecked {{
        image: url({ASSETS_DIR / 'switch_left_dark.png'});
    }}
                    
    QCheckBox::indicator:checked {{
        image: url({ASSETS_DIR / 'switch_right_dark.png'});
    }}
""")

RED_BUTTON_STYLE = """
    QPushButton {
        background-color: rgb(200, 0, 0);
    }

    QPushButton:pressed {
        background-color: rgb(150, 0, 0);
    }

    QPushButton:disabled {
        background-color: rgb(100, 0, 0);
    }
"""

GREEN_BUTTON_STYLE = """
    QPushButton {
        background-color: rgb(0, 200, 0);
    }

    QPushButton:pressed {
        background-color: rgb(0, 150, 0);
    }

    QPushButton:disabled {
        background-color: rgb(0, 100, 0);
    }
"""

class JoggingLayout(QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        big_font = QFont()
        big_font.setPointSize(20)
        big_font.setBold(True)

        #################################
        # CONFIGURE AND LAY OUT WIDGETS #
        #################################

        # Panel label
        self.panel_label = QLabel("JOGGING")
        self.panel_label.setFont(big_font)
        self.panel_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.addWidget(self.panel_label)

        # Toggle switch
        self.toggle_switch = QCheckBox()
        self.toggle_switch.setStyleSheet(TOGGLE_SWITCH_STYLE)

        # Add toggle switch to layout
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        row.addWidget(QLabel("Substrate Rotation"))
        row.addWidget(self.toggle_switch)
        row.addWidget(QLabel("Loading/Unloading"))
        self.addLayout(row)
        self.addStretch(1)

        # Incremental controls
        self.increment_units = QComboBox()
        self.increment_units.addItem("Degrees")
        self.increment_units.addItem("Steps")

        self.increment_input = QSpinBox()
        self.increment_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.increment_input.setFixedWidth(62) # Lines up with continuous controls

        self.increment_ccw_button = QPushButton("Step CCW")
        self.increment_cw_button = QPushButton("Step CW")

        # Add Incremental controls to layout
        self.addWidget(QLabel("Incremental"), alignment=Qt.AlignmentFlag.AlignLeft)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        row.addWidget(self.increment_units)
        row.addWidget(self.increment_input)
        row.addSpacing(10)
        row.addWidget(self.increment_ccw_button)
        row.addWidget(self.increment_cw_button)
        self.addLayout(row)

        # Continuous controls
        self.continuous_speed_input = QDoubleSpinBox(minimum=0.5, maximum=1)
        self.continuous_speed_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.continuous_speed_input.setFixedWidth(50)

        self.continuous_start_ccw_button = QPushButton("Start CCW")
        self.continuous_start_cw_button = QPushButton("Start CW")

        self.continuous_stop_button = QPushButton("STOP")
        self.continuous_stop_button.setStyleSheet(RED_BUTTON_STYLE)

        self.home_button = QPushButton("HOME")
        self.home_button.setStyleSheet(GREEN_BUTTON_STYLE)

        # Add continuous controls to layout
        self.addSpacing(20)
        self.addWidget(QLabel("Continuous"), alignment=Qt.AlignmentFlag.AlignLeft)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        row.addWidget(QLabel("Speed (RPM)"))
        row.addWidget(self.continuous_speed_input)
        row.addSpacing(10)
        row.addWidget(self.continuous_start_ccw_button)
        row.addWidget(self.continuous_start_cw_button)
        row.addWidget(self.continuous_stop_button)
        row.addWidget(self.home_button)
        self.addLayout(row)

        ###################
        # CONNECT SIGNALS #
        ###################

        # Set up signals to implicitly enable/disable start buttons for continuous
        def enable_continuous(enable: bool):
            self.continuous_speed_input.setEnabled(enable)
            self.continuous_start_ccw_button.setEnabled(enable)
            self.continuous_start_cw_button.setEnabled(enable)
            self.continuous_stop_button.setEnabled(enable)
            self.home_button.setEnabled(enable)

        self.continuous_start_ccw_button.clicked.connect(lambda: enable_continuous(False))
        self.continuous_start_cw_button.clicked.connect(lambda: enable_continuous(False))
        self.continuous_stop_button.clicked.connect(lambda: enable_continuous(True))
        self.toggle_switch.stateChanged.connect(lambda state: enable_continuous(False) if state==2 else enable_continuous(True))

        # Change limits and clear when units change
        def on_units_change(units: str):
            self.increment_input.setValue(0)

            if units == "Degrees":
                self.increment_input.setMinimum(0)
                self.increment_input.setMaximum(20)
                return

            if units == "Steps":
                self.increment_input.setMinimum(0)
                self.increment_input.setMaximum(1000)
                return
            
        self.increment_units.currentTextChanged.connect(on_units_change)

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
        
    jogging_layout = JoggingLayout()
    layout.addLayout(jogging_layout)
    
    window.setLayout(layout)
    window.setWindowTitle("Substrate Tab Widget")
    window.show()
    sys.exit(app.exec())