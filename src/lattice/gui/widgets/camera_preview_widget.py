import sys

from lattice.devices.camera import Camera
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QApplication, QMainWindow, QVBoxLayout, QSizePolicy

class CameraPreview(QLabel):
    def __init__(self, source: int | str, width: int = None, height: int = None):
        super().__init__()

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.setContentsMargins(0, 0, 0, 0)
        self.setMargin(0)
        self.setIndent(0)

        self.aspect_ratio = 16 / 9

        if width and height:
            self.setMinimumSize(width, height)

        self.camera = Camera(source)
        self.camera.frame_ready.connect(self.update_image)
        self.camera.start()

        self.current_pixmap = None

    def switch_camera(self, source: int | str):
        self.camera.change_source(source)

    def update_image(self, image):
        self.current_pixmap = QPixmap.fromImage(image)
        self.update_preview()

    def update_preview(self):
        if self.current_pixmap and not self.current_pixmap.isNull():
            scaled = self.current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview()

    def closeEvent(self, event):
        self.camera.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    preview = CameraPreview(640, 480)
    window = QMainWindow()
    window.setCentralWidget(preview)
    window.show()

    sys.exit(app.exec())