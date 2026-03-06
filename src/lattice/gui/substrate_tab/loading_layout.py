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

class LoadingLayout(QVBoxLayout):
    def __init__(self):
        super().__init__()
        
        big_font = QFont()
        big_font.setPointSize(20)
        big_font.setBold(True)

        #################################
        # CONFIGURE AND LAY OUT WIDGETS #
        #################################

        # Panel label
        self.panel_label = QLabel("LOADING/UNLOADING")
        self.panel_label.setFont(big_font)
        self.addWidget(self.panel_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Angle display dial
        self.addSpacing(10)
        self.angle_dial = AngleDial(read_only=True)
        self.angle_dial.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.addWidget(self.angle_dial)

        # Stop buttons
        self.stop_button = QPushButton("STOP")
        self.stop_button.setFixedWidth(100)
        self.stop_button.setStyleSheet(RED_BUTTON_STYLE)

        # Add Start and stop buttons to layout
        self.addSpacing(10)
        self.addWidget(self.stop_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Load/unload stop Angles
        self.load_angle = QSpinBox(minimum=0, maximum=359)
        self.growth_angle = QSpinBox(minimum=0, maximum=359)
        self.flux_angle = QSpinBox(minimum=0, maximum=359)
        
        for spinbox in [self.load_angle, self.growth_angle, self.flux_angle]:
            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.load_go_button = QPushButton("GO")
        self.growth_go_button = QPushButton("GO")
        self.flux_go_button = QPushButton("GO")

        for button in [self.load_go_button, self.growth_go_button, self.flux_go_button]:
            button.setStyleSheet(GREEN_BUTTON_STYLE)

        # Add load/unload stop angles to layout
        self.addSpacing(10)
        grid = QGridLayout()
        # Load/unload row
        grid.addWidget(QLabel("Load/Unload"), 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.load_angle, 0, 2)
        grid.addWidget(QLabel('\u00B0'), 0, 3)
        grid.addWidget(self.load_go_button, 0, 5)
        # Growth row
        grid.addWidget(QLabel("Growth"), 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.growth_angle, 1, 2)
        grid.addWidget(QLabel('\u00B0'), 1, 3)
        grid.addWidget(self.growth_go_button, 1, 5)
        # Flux row
        grid.addWidget(QLabel("Flux"), 2, 1, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.flux_angle, 2, 2)
        grid.addWidget(QLabel('\u00B0'), 2, 3)
        grid.addWidget(self.flux_go_button, 2, 5)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnMinimumWidth(4, 20)
        grid.setColumnStretch(6, 1)
        self.addLayout(grid) 

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
        
    layout.addLayout(LoadingLayout())
    
    window.setLayout(layout)
    window.setWindowTitle("Substrate Tab Widget")
    window.show()
    sys.exit(app.exec())