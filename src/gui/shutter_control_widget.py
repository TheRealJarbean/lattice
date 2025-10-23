import logging
import sys
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QHBoxLayout, 
    QApplication,
    QSizePolicy,
    QSpacerItem,
    QLineEdit,
    QVBoxLayout
)
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)

BUTTON_STYLE = """
    QPushButton[is_on='true'], QPushButton[is_open='true'] {
        background-color: rgb(0, 255, 0);
        border: 1px solid black;
    }
    
    QPushButton[is_on='false'], QPushButton[is_open='false'] {
        background-color: rgb(255, 0, 0);
        border: 1px solid black;
    }
"""

NAME_DISPLAY_STYLE = """
    background-color: rgb(224, 224, 224);
    color: rgb(0, 0, 0);
"""

class ShutterControlWidget(QWidget):
    def __init__(self, name: str, num_steps: int, parent=None):
        super().__init__(parent)

        # Create widgets
        self.control_button = QPushButton("ON")
        self.output_button = QPushButton("Closed")
        self.name_display = QLineEdit()
        self.step_state_buttons = [QPushButton("Closed") for _ in range(num_steps)]
        
        all_widgets: list[QWidget] = [
            self.control_button,
            self.output_button,
            self.name_display,
            *self.step_state_buttons
        ]
        
        # Create fonts
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        
        # Change widget settings
        for widget in all_widgets:
            widget.setFont(font)
            widget.setFixedWidth(75)
            widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
            
        self.name_display.setFixedWidth(125)
        self.name_display.setStyleSheet(NAME_DISPLAY_STYLE)
        self.name_display.setEnabled(False)
        self.name_display.setText(name)
        
        # Set button properties
        self.output_button.setProperty('is_open', False)
        self.control_button.setProperty('is_on', True)
        for button in self.step_state_buttons:
            button.setProperty('is_open', False)
            
        # Apply button stylesheets
        self.output_button.setStyleSheet(BUTTON_STYLE)
        self.control_button.setStyleSheet(BUTTON_STYLE)
        for button in self.step_state_buttons:
            button.setStyleSheet(BUTTON_STYLE)
        
        # Create step_button_layout
        step_button_layout = QHBoxLayout()
        step_button_layout.setSpacing(8)
        step_button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add buttons to step_button_layout
        for button in self.step_state_buttons:
            step_button_layout.addWidget(button)
        
        # Create main layout
        layout = QHBoxLayout()
        layout.setSpacing(50)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add widgets to layout
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addWidget(self.control_button)
        layout.addWidget(self.output_button)
        layout.addWidget(self.name_display)
        layout.addLayout(step_button_layout)
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.setLayout(layout)

# Run as standalone app for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout()
    layout.setSpacing(0)
    
    layout.addWidget(ShutterControlWidget("Gallium", 6))
    layout.addWidget(ShutterControlWidget("Indium", 6))
    
    window.setLayout(layout)
    window.setWindowTitle("Shutter Control Widget")
    window.show()
    sys.exit(app.exec())