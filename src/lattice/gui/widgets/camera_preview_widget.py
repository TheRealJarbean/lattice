import sys

from lattice.devices.camera import Camera
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QApplication, QMainWindow, QVBoxLayout, QSizePolicy

class CameraPreview(QLabel):
    def __init__(self, source:int|str, width:int=None, height:int=None):
        super().__init__()

        # self.setFixedSize(width, height)
        if width and height:
            self.setMinimumSize(width, height)

        self.aspect_ratio = 16 / 9 # Width to height

        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        self.camera = Camera(source)
        self.camera.frameReady.connect(self.update_image)
        self.camera.start()

        self.current_pixmap = None

    def switch_camera(self, source:int|str):
        self.camera.change_source(source)

    def update_image(self, image):
        self.current_pixmap = QPixmap.fromImage(image)
        self.update_preview()

    def update_preview(self):
        if self.current_pixmap:
            self.setPixmap(
                self.current_pixmap.scaled(
                    self.width(),
                    self.width() * (1 / self.aspect_ratio),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

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