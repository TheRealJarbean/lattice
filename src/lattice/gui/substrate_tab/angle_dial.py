from PySide6.QtWidgets import (
    QLabel,
    QDial,
)
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QFont,
)
import logging

logger = logging.getLogger(__name__)

class AngleDial(QDial):
    def __init__(self, read_only = False):
        super().__init__()
        self.read_only = read_only

        # Config
        self.setWrapping(True)
        self.setNotchesVisible(True)
        self.setMinimum(0)
        self.setMaximum(359)
        self.setNotchTarget(10)
        self.setSingleStep(1)
        self.setPageStep(5)
        self.setMinimumWidth(200)
        self.setMinimumHeight(200)
        
        # Add value label
        self.label = QLabel('0\u00B0', parent=self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.label.setFont(font)

        self.valueChanged.connect(self.update_label)

    def showEvent(self, event):
        self.label.resize(self.width(), self.height())
        self.label.move(self.rect().center() - self.label.rect().center())

    def resizeEvent(self, event):
        self.label.resize(self.width(), self.height())
        self.label.move(self.rect().center() - self.label.rect().center())
        super().resizeEvent(event)

    # Make dial readonly
    def mousePressEvent(self, event):
        if not self.read_only:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.read_only:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not self.read_only:
            super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        if not self.read_only:
            super().wheelEvent(event)

    def update_label(self, value):
        self.label.setText(f'{value}\u00B0')