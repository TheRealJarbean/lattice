import sys
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QWidget, 
    QLabel, 
    QPushButton,
    QHBoxLayout, 
    QApplication,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout
)
from PySide6.QtGui import QFont, QColor

class PressureControlWidget(QWidget):
    def __init__(self, name: str, color: QColor, parent=None):
        super().__init__(parent)
        self.color = color.name()
        
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), color)
        self.setPalette(palette)

        # Create widgets
        self.name_label = QLabel(name)
        self.power_toggle_button = QPushButton("Turn On")
        self.rate_label = QLabel("Rate (/sec)")
        self.rate_display = QLabel("0.0")
        self.pressure_display = QLabel("0.0")
        
        # Create fonts
        name_font = QFont()
        name_font.setPointSize(14)
        name_font.setBold(True)
        
        rate_font = QFont()
        rate_font.setPointSize(10)
        rate_font.setBold(True)
        
        # Change widget settings
        self.name_label.setFont(name_font)
        self.rate_label.setFont(rate_font)
        
        self.rate_display.setMinimumWidth(100)
        self.rate_display.setContentsMargins(2, 2, 2, 2)
        self.rate_display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.rate_display.setStyleSheet("""
            color: rgb(255, 255, 255);
            font: 12pt "Consolas";
            background-color: rgb(0, 0, 0);
            border-color: rgb(0, 0, 0);
            """)
        
        self.pressure_display.setContentsMargins(2, 2, 2, 2)
        self.pressure_display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.pressure_display.setStyleSheet("""
            background-color: rgb(0, 0, 0);
            font: 30pt "Consolas";
            color: rgb(255, 255, 255);
            border-color: rgb(0, 0, 0);
            """)
        
        # Create sub-horizontal layout
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.power_toggle_button)
        h_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        h_layout.addWidget(self.rate_label)
        h_layout.addWidget(self.rate_display)
        
        # Create main layout
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Add widgets to layout
        layout.addWidget(self.name_label)
        layout.addLayout(h_layout)
        layout.addWidget(self.pressure_display)

        self.setLayout(layout)
        
    @Slot(float)
    def format_and_display_pressure(self, pressure):
        self.pressure_display.setText(f"{pressure:.2e}")
        
    @Slot(float)
    def format_and_display_rate(self, rate):
        self.rate_display.setText(f"{rate:.2e}")
        
    @Slot(float)
    def update_on_off_text(self, is_on):
        self.power_toggle_button.setText("Turn Off" if is_on else "Turn On")

# Run as standalone app for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    
    num_gauges = 3
    color = QColor(100, 150, 255)
    for i in range(num_gauges):
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        widget = PressureControlWidget(f"Gauge {i + 1}", color)
        layout.addWidget(widget)
    layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
    
    window.setLayout(layout)
    window.setWindowTitle("Pressure Control Widget")
    window.show()
    sys.exit(app.exec())