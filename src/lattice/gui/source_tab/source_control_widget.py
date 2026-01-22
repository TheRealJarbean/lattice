import sys
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, 
    QLabel, 
    QLineEdit, 
    QPushButton,
    QColorDialog, 
    QHBoxLayout, 
    QApplication,
    QDoubleSpinBox,
    QSizePolicy,
    QCheckBox
)
from PySide6.QtGui import QColor, QPainter, QBrush, QFont

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
    set_setpoint = Signal(float)
    set_rate_limit = Signal(float)

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
        self.display_working_setpoint = QLineEdit()
        self.plot_working_setpoint = QCheckBox()
        self.display_rate_limit = QLineEdit()
        self.pid_button = QPushButton("PID")
        self.safety_button = QPushButton("Safety")
        
        input_widgets.append(self.input_setpoint)
        input_widgets.append(self.input_rate_limit)
        display_widgets.append(self.display_temp)
        display_widgets.append(self.display_setpoint)
        display_widgets.append(self.display_working_setpoint)
        display_widgets.append(self.display_rate_limit)
        
        # Create font
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        
        # Change widget settings
        self.label.setFixedWidth(100)
        self.label.setFont(font)
        
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
            display.setMinimumWidth(100)

        # Make connections
        self.set_setpoint_button.clicked.connect(
            lambda: self.set_setpoint.emit(self.input_setpoint.value())
        )

        self.set_rate_limit_button.clicked.connect(
            lambda: self.set_rate_limit.emit(self.input_rate_limit.value())
        )

        # Create working setpoint layout
        wsp_layout = QHBoxLayout()
        wsp_layout.setSpacing(10)
        
        # Add working setpoint widgets to layout
        wsp_layout.addWidget(self.display_working_setpoint, stretch=1)
        wsp_layout.addWidget(self.plot_working_setpoint)
        
        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Add widgets to layout
        layout.addWidget(self.label)
        layout.addWidget(self.circle)
        layout.addWidget(self.display_temp, stretch=1)
        layout.addWidget(self.display_setpoint, stretch=1)
        layout.addLayout(wsp_layout, stretch=1)
        layout.addWidget(self.display_rate_limit, stretch=1)
        layout.addWidget(self.input_setpoint, stretch=1)
        layout.addWidget(self.set_setpoint_button)
        layout.addWidget(self.input_rate_limit, stretch=1)
        layout.addWidget(self.set_rate_limit_button)
        layout.addWidget(self.pid_button)
        layout.addWidget(self.safety_button)

        self.setLayout(layout)

    def update_process_variable(self, process_variable):
        self.display_temp.setText(f"{process_variable:.2f} C")

    def update_setpoint(self, setpoint):
        self.display_setpoint.setText(f"{setpoint:.2f} C")

    def update_working_setpoint(self, working_setpoint):
        self.display_working_setpoint.setText(f"{working_setpoint:.2f} C")

    def update_rate_limit(self, rate_limit):
        self.display_rate_limit.setText(f"{rate_limit:.2f} C/s")

# Run as standalone app for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    widget = SourceControlWidget()
    widget.display_temp.setText("200.00 C")
    widget.display_setpoint.setText("300.00 C")
    widget.display_working_setpoint.setText("290.00 C")
    widget.display_rate_limit.setText("10.00 C/s")
    layout.addWidget(widget)
    window.setLayout(layout)
    window.setWindowTitle("Source Control Widget")
    window.show()
    sys.exit(app.exec())