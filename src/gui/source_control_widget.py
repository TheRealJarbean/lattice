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
from PySide6.QtGui import QColor, QPainter, QBrush, QFont
from PySide6.QtCore import Qt, Signal

class ColorCircle(QLabel):
    color_changed = Signal(str)
    
    def __init__(self, color: str, parent=None):
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
        input_widgets: list[QDoubleSpinBox] = [] # Temporary to iterate in settings
        display_widgets: list[QLineEdit] = [] # Temporary to iterate in settings
        self.label = QLabel("Label:")
        self.circle = ColorCircle(color)
        self.input_setpoint = QDoubleSpinBox()
        self.set_setpoint_button = QPushButton("Set")
        self.input_rate_limit = QDoubleSpinBox()
        self.set_rate_limit_button = QPushButton("Set")
        self.display_temp = QLineEdit()
        self.display_setpoint = QLineEdit()
        self.display_rate_limit = QLineEdit()
        self.display_volts = QLineEdit()
        self.display_amps = QLineEdit()
        self.display_watts = QLineEdit()
        self.pid_button = QPushButton("PID")
        self.safety_button = QPushButton("Safety")
        
        input_widgets.append(self.input_setpoint)
        input_widgets.append(self.input_rate_limit)
        display_widgets.append(self.display_temp)
        display_widgets.append(self.display_setpoint)
        display_widgets.append(self.display_rate_limit)
        display_widgets.append(self.display_volts)
        display_widgets.append(self.display_amps)
        display_widgets.append(self.display_watts)
        
        # Change widget settings
        self.label.setFixedWidth(100)
        
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        
        for spin_box in input_widgets:
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
            spin_box.setFont(font)
            spin_box.setMinimumWidth(100)
        
        for display in display_widgets:
            display.setReadOnly(True)
            display.setAlignment(Qt.AlignmentFlag.AlignRight)
            display.setStyleSheet("""
                QLineEdit {
                    background-color: #e0e0e0;
                }
            """)
            display.setFont(font)
            
        for display in [
            self.display_temp,
            self.display_setpoint,
            self.display_rate_limit
            ]:
            display.setMinimumWidth(100)
            
        for display in [
            self.display_volts,
            self.display_amps,
            self.display_watts
            ]:
            display.setFixedWidth(50)
        
        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Add widgets to layout
        layout.addWidget(self.label)
        layout.addWidget(self.circle)
        layout.addWidget(self.input_setpoint, stretch=1)
        layout.addWidget(self.set_setpoint_button)
        layout.addWidget(self.input_rate_limit, stretch=1)
        layout.addWidget(self.set_rate_limit_button)
        layout.addWidget(self.display_temp, stretch=1)
        layout.addWidget(self.display_setpoint, stretch=1)
        layout.addWidget(self.display_rate_limit, stretch=1)
        layout.addWidget(self.display_volts)
        layout.addWidget(self.display_amps)
        layout.addWidget(self.display_watts)
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