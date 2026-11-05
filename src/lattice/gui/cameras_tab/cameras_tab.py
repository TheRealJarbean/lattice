from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QMainWindow,
    QApplication,
    QVBoxLayout,
    QPushButton
)
import logging
import sys

# Local imports
from lattice.gui.widgets.camera_preview_widget import CameraPreview

logger = logging.getLogger(__name__)

class CamerasTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()

        # Camera 1
        self.camera_preview_1 = CameraPreview(0, width=480, height=270)
        self.reset_button_1 = QPushButton("Reset Zoom")
        self.reset_button_1.clicked.connect(self.camera_preview_1.reset_zoom)
        self.reset_button_1.setFixedWidth(100)

        column = QVBoxLayout()
        column.addWidget(self.camera_preview_1)
        column.addWidget(self.reset_button_1, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(column)

        # Camera 2
        self.camera_preview_2 = CameraPreview(1, width=480, height=270)
        self.reset_button_2 = QPushButton("Reset Zoom")
        self.reset_button_2.clicked.connect(self.camera_preview_2.reset_zoom)
        self.reset_button_2.setFixedWidth(100)

        column = QVBoxLayout()
        column.addWidget(self.camera_preview_2)
        column.addWidget(self.reset_button_2, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(column)

        self.setLayout(layout)

def start():
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setCentralWidget(CamerasTab())
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start()