import cv2

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class Camera(QThread):
    frameReady = Signal(QImage)

    def __init__(self, source: int|str):
        super().__init__()
        self.running = True
        self.source = source

    def run(self):
        cap = cv2.VideoCapture(self.source)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            # OpenCV BGR -> Qt RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w, ch = frame.shape
            image = QImage(
                frame.data,
                w,
                h,
                ch * w,
                QImage.Format_RGB888
            )

            self.frameReady.emit(image)

        cap.release()

    def stop(self):
        self.running = False
        self.wait()