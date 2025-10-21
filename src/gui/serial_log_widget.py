import sys
from collections import deque
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QComboBox,
    QPlainTextEdit,
    QLineEdit,
    QPushButton,
    QToolButton,
    QStyle,
    QApplication,
    QHBoxLayout,
    QVBoxLayout
)
from PySide6.QtGui import QFont

class SerialLogWidget(QWidget):
    send_command = Signal(str)
    
    def __init__(self, app: QApplication, name: str, device_names: list[str], parent=None):
        super().__init__(parent)
        
        # Create data attributes
        self.data = {name: deque(maxlen=200) for name in device_names}
        
        # Create widgets
        self.name_label = QLabel(name)
        self.selection = QComboBox()
        self.log = QPlainTextEdit()
        self.input = QLineEdit()
        self.send_button = QPushButton("Send")
        self.clear_button = QToolButton()
        
        # Create font
        name_font = QFont()
        name_font.setPointSize(14)
        name_font.setBold(True)
        
        # Change widget settings
        self.name_label.setFont(name_font)
        self.selection.addItems(device_names)
        
        # Add icon to clear button
        icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
        self.clear_button.setIcon(icon)
        
        # Connect signals
        self.send_button.clicked.connect(lambda: self.send_command.emit(self.input.text()))
        self.clear_button.clicked.connect(self.clear)
        self.selection.currentIndexChanged.connect(self.change_log)
        
        # Build layouts
        self.top_layout = QHBoxLayout()
        self.top_layout.addWidget(self.name_label)
        self.top_layout.addWidget(self.selection)
        
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addWidget(self.input)
        self.bottom_layout.addWidget(self.send_button)
        self.bottom_layout.addWidget(self.clear_button)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(2)
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.log)
        self.main_layout.addLayout(self.bottom_layout)
        
        self.setLayout(self.main_layout)
        
    def clear(self):
        key = self.selection.currentText()
        self.data[key].clear()
        self.log.clear()
    
    @Slot(str, str) # key, data
    def append_data(self, key, data):
        self.data[key].append(data)
        
        if key == self.selection.currentText():
            # Store current scroll bar position
            current_scroll_pos = self.log.verticalScrollBar().value()
            autoscroll = current_scroll_pos == self.log.verticalScrollBar().maximum()
            
            # Add data to log
            self.log.setPlainText('\n'.join(self.data[key]))
            
            # Keep scrolling down if scroll bar was at bottom before
            if autoscroll:
                self.log.verticalScrollBar().setValue(
                    self.log.verticalScrollBar().maximum()
                )
                return
            
            self.log.verticalScrollBar().setValue(current_scroll_pos)
            
    def change_log(self):
        key = self.selection.currentText()
        self.log.setPlainText('\n'.join(self.data[key]))
        self.log.verticalScrollBar().setValue(
            self.log.verticalScrollBar().maximum()
        )
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    
    layout.addWidget(SerialLogWidget(app, "Shutters", ["Shutter 1", "Shutter 2"]))
    
    window.setLayout(layout)
    window.setWindowTitle("Pressure Control Widget")
    window.show()
    sys.exit(app.exec())