from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QMainWindow,
    QApplication
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
        self.camera_preview_1 = CameraPreview(0, width=480, height=270)
        self.camera_preview_2 = CameraPreview(1, width=480, height=270)
        layout.addWidget(self.camera_preview_1)
        layout.addWidget(self.camera_preview_2)
        self.setLayout(layout)

def start():
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setCentralWidget(CamerasTab())
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start()