from PySide6.QtWidgets import (
    QLabel,
    QDial,
)
from PySide6.QtCore import (
    Qt,
    QPointF
)
from PySide6.QtGui import (
    QFont,
    QPainter,
    QPen
)
import logging
import math

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

        self.angle = 0

        self.valueChanged.connect(self.update_label)
        self.valueChanged.connect(self.update_indicator)

    def paintEvent(self, event):
        # Let Qt draw the normal dial first
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Center of the dial
        center = QPointF(self.width() / 2, self.height() / 2)

        # Radius for the indicator
        radius = min(self.width(), self.height()) / 2 - 8

        # Convert dial value -> angle
        # Example: dial ranges from 0 to 360 degrees
        angle = self.value()

        # Qt's 0° points to the right, while we want 0° at the top
        radians = math.radians(self.angle - 90)

        end = QPointF(
            center.x() + radius * math.cos(radians),
            center.y() + radius * math.sin(radians)
        )

        pen = QPen(Qt.GlobalColor.green)
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.setPen(pen)
        painter.drawLine(center, end)

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

    def update_indicator(self, value):
        self.angle = value