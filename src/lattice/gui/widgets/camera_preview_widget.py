import sys

from lattice.devices.camera import Camera
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QApplication, QMainWindow, QVBoxLayout, QSizePolicy, QRubberBand

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

        self.rubber_band = QRubberBand(
            QRubberBand.Shape.Rectangle, self
        )

        self.selection_origin = QPoint()
        self.zoom_rect = None

    def switch_camera(self, source: int | str):
        self.camera.change_source(source)

    def update_image(self, image):
        self.current_pixmap = QPixmap.fromImage(image)
        self.update_preview()

    def update_preview(self):
        if self.current_pixmap is None:
            return

        pixmap = self.current_pixmap

        if self.zoom_rect is not None:
            pixmap = pixmap.copy(self.zoom_rect)

        self.setPixmap(
            pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview()

    def closeEvent(self, event):
        self.camera.stop()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selection_origin = event.position().toPoint()
            self.rubber_band.setGeometry(
                QRect(self.selection_origin, self.selection_origin)
            )
            self.rubber_band.show()


    def mouseMoveEvent(self, event):
        if self.rubber_band.isVisible():
            rect = QRect(
                self.selection_origin,
                event.position().toPoint()
            ).normalized()

            self.rubber_band.setGeometry(rect)


    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.rubber_band.hide()

            selection = self.rubber_band.geometry()

            if selection.width() < 10 or selection.height() < 10:
                return

            self.zoom_rect = self.widget_rect_to_image_rect(selection)
            self.update_preview()


    def widget_rect_to_image_rect(self, rect):
        """Convert widget coordinates into original image coordinates."""

        if self.current_pixmap is None:
            return None

        image = self.current_pixmap

        scaled = image.size().scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio
        )

        # Position of the displayed image inside the QLabel
        offset_x = (self.width() - scaled.width()) / 2
        offset_y = (self.height() - scaled.height()) / 2

        x = (rect.x() - offset_x) * image.width() / scaled.width()
        y = (rect.y() - offset_y) * image.height() / scaled.height()

        width = rect.width() * image.width() / scaled.width()
        height = rect.height() * image.height() / scaled.height()

        image_rect = QRect(
            round(x), round(y),
            round(width), round(height)
        )

        return image_rect.intersected(image.rect())


    def reset_zoom(self):
        self.zoom_rect = None
        self.update_preview()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    preview = CameraPreview(640, 480)
    window = QMainWindow()
    window.setCentralWidget(preview)
    window.show()

    sys.exit(app.exec())