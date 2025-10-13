import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, 
    QLabel, 
    QLineEdit, 
    QPushButton,
    QColorDialog, 
    QHBoxLayout, 
    QApplication,
    QDoubleSpinBox,
    QSizePolicy
)
from PySide6.QtGui import QColor, QPainter, QBrush
from PySide6.QtCore import Qt, Signal


class ColorCircle(QLabel):
    color_changed = Signal(str)
    
    def __init__(self, color=QColor(0, 0, 0), parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.color = color
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        new_color = QColorDialog.getColor(self.color, self, "Select Color")
        if new_color.isValid():
            self.color = new_color
            self.color_changed.emit(new_color.name())
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.black)
        diameter = min(self.width(), self.height()) - 2
        painter.drawEllipse(1, 1, diameter, diameter)


class SourceControlWidget(QWidget):
    def __init__(self, color: QColor=QColor("blue"), parent=None):
        super().__init__(parent)

        # Create widgets
        self.label = QLabel("Label:")
        self.circle = ColorCircle(color)
        self.input_setpoint = QDoubleSpinBox()
        self.input_rate_limit = QDoubleSpinBox()
        self.set_button = QPushButton("Set")
        self.display_temp = QLineEdit()
        self.display_setpoint = QLineEdit()
        self.display_rate_limit = QLineEdit()
        self.pid_button = QPushButton("PID")
        self.safety_button = QPushButton("Safety Rate Limit")
        
        # Change widget settings
        self.label.setFixedWidth(100)
        
        for spin_box in [self.input_setpoint, self.input_rate_limit]:
            spin_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            spin_box.lineEdit().setAlignment(Qt.AlignmentFlag.AlignRight)
            spin_box.setStyleSheet("""
                QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { 
                    width: 0; 
                }
                
                QDoubleSpinBox {
                    border: 1px solid #000000;
                }
            """) # Remove arrows and add border
            spin_box.setDecimals(2)
            spin_box.setRange(0, 10000)
        
        for display in [self.display_temp, self.display_setpoint, self.display_rate_limit]:
            display.setReadOnly(True)
            display.setAlignment(Qt.AlignmentFlag.AlignRight)
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
        layout.addWidget(self.input_setpoint, stretch=1)
        layout.addWidget(self.input_rate_limit, stretch=1)
        layout.addWidget(self.set_button)
        layout.addWidget(self.display_temp, stretch=1)
        layout.addWidget(self.display_setpoint, stretch=1)
        layout.addWidget(self.display_rate_limit, stretch=1)
        layout.addWidget(self.pid_button)
        layout.addWidget(self.safety_button)

        self.setLayout(layout)

# Run as standalone app for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    widget = SourceControlWidget()
    widget.display_temp.setText("200.00 C")
    widget.display_setpoint.setText("300.00 C")
    widget.display_rate_limit.setText("10.00 C/s")
    layout.addWidget(widget)
    window.setLayout(layout)
    window.setWindowTitle("Source Control Widget")
    window.show()
    sys.exit(app.exec())