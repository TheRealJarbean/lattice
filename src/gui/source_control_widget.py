import sys
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QColorDialog, QHBoxLayout, QApplication
)
from PySide6.QtGui import QColor, QPainter, QBrush
from PySide6.QtCore import Qt


class ColorCircle(QLabel):
    def __init__(self, color=QColor(0, 0, 0), parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.color = color
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        new_color = QColorDialog.getColor(self.color, self, "Select Color")
        if new_color.isValid():
            self.color = new_color
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.black)
        diameter = min(self.width(), self.height()) - 2
        painter.drawEllipse(1, 1, diameter, diameter)


class SourceControlWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create widgets
        self.label = QLabel("Label:")
        self.circle = ColorCircle(QColor("blue"))
        self.input_setpoint = QLineEdit()
        self.input_ramp_rate = QLineEdit()
        self.set_button = QPushButton("Set")
        self.display_temp = QLineEdit()
        self.display_ramp_rate = QLineEdit()
        self.display_watts = QLineEdit()
        self.pid_button = QPushButton("PID")
        self.safety_button = QPushButton("Safety Rate Limit")
        
        # Change widget settings
        self.label.setFixedWidth(100)
        
        for display in [self.display_temp, self.display_ramp_rate, self.display_watts]:
            display.setReadOnly(True)
            display.setStyleSheet("""
                QLineEdit {
                    background-color: #e0e0e0;
                }
            """)
        
        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Add widgets to layout
        layout.addWidget(self.label)
        layout.addWidget(self.circle)
        layout.addWidget(self.input_setpoint)
        layout.addWidget(self.input_ramp_rate)
        layout.addWidget(self.set_button)
        layout.addWidget(self.display_temp)
        layout.addWidget(self.display_ramp_rate)
        layout.addWidget(self.display_watts)
        layout.addWidget(self.pid_button)
        layout.addWidget(self.safety_button)

        self.setLayout(layout)
        
    def set_color(self, color: QColor):
        self.circle.color = color

# Run as standalone app for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    widget = SourceControlWidget()
    layout.addWidget(widget)
    window.setLayout(layout)
    window.setWindowTitle("Source Control Widget")
    window.show()
    sys.exit(app.exec())