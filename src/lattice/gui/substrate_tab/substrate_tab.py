from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QFrame
)
from PySide6.QtCore import (
    QLine
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

logger = logging.getLogger(__name__)

class SubstrateTab(QWidget):
    def __init__(self):
        super().__init__()

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
        layout.addLayout(self.jogging)

        self.setLayout(layout)

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