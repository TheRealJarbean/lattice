import sys
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QApplication
)
from PySide6.QtCore import Qt

class ShutterControlWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create widgets
        self.label = QLabel("Status:")
        self.open_button = QPushButton("Open")
        self.close_button = QPushButton("Close")

        # Style buttons
        self.open_button.setStyleSheet("background-color: green; color: white;")
        self.close_button.setStyleSheet("background-color: red; color: white;")

        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # No margins around
        layout.setSpacing(0)  # No space between widgets

        layout.addWidget(self.label)
        layout.addWidget(self.open_button)
        layout.addWidget(self.close_button)

        # Align label vertically center and buttons too
        self.label.setAlignment(Qt.AlignVCenter)

        self.setLayout(layout)
        
# Run as standalone app for testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    widget = ShutterControlWidget()
    layout.addWidget(widget)
    window.setLayout(layout)
    window.setWindowTitle("Custom Row Widget")
    window.show()
    sys.exit(app.exec_())