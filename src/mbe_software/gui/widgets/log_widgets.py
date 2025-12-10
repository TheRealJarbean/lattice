import sys
from collections import deque
from PySide6.QtCore import Signal, Slot, Qt
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
    QVBoxLayout,
    QAbstractSpinBox,
    QSpinBox,
    QDoubleSpinBox
)
from PySide6.QtGui import QFont

class SerialLogWidget(QWidget):
    send_command = Signal(str, str) # Name, command
    
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
        
        # Create fonts
        name_font = QFont()
        name_font.setPointSize(14)
        name_font.setBold(True)
        
        log_font = QFont()
        log_font.setPointSize(12) 
        log_font.setStyleHint(QFont.StyleHint.Monospace) # In case consolas is unavailable
        log_font.setFamily("Consolas")
        
        # Change widget settings
        self.name_label.setFont(name_font)
        self.selection.addItems(device_names)
        self.log.setFont(log_font)
        
        # Add icon to clear button
        icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
        self.clear_button.setIcon(icon)
        
        # Connect signals
        self.send_button.clicked.connect(
            lambda: self.send_command.emit(self.selection.currentText(), self.input.text())
        )
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
            # Store current scrollbar position
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
        
class ModbusLogWidget(SerialLogWidget):
    read_modbus = Signal(str, int) # Name, modbus address
    write_modbus = Signal(str, int, float) # Name, modbus address, value
    
    def __init__(self, app: QApplication, name: str, device_names: list[str], parent=None):
        super().__init__(app, name, device_names, parent)
        
        # Add widgets
        # Add a little artificial spacing to labels for style
        self.address_label = QLabel("Address: ")
        self.address_input = QSpinBox()
        self.value_label = QLabel("  Value: ")
        self.value_input = QDoubleSpinBox()
        self.read_button = QPushButton("Read")
        self.write_button = QPushButton("Write")
        
        # Change widget settings
        for spin_box in [self.address_input, self.value_input]:
            spin_box.setMaximum(100000)
            spin_box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin_box.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.address_input.setValue(35578)
        self.value_input.setValue(0.0)
        
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Connect buttons
        self.read_button.clicked.connect(
            lambda: self.read_modbus.emit(self.selection.currentText(), self.address_input.value())
        )
        self.write_button.clicked.connect(
            lambda: self.write_modbus.emit(self.selection.currentText(), self.address_input.value(), self.value_input.value())
        )
        
        # Remove default input widget and send button
        for widget in [self.input, self.send_button]:
            self.bottom_layout.removeWidget(widget)
            widget.setParent(None)
        
        # Append new widgets to left side of layout
        self.bottom_layout.insertWidget(0, self.write_button)
        self.bottom_layout.insertWidget(0, self.read_button)
        self.bottom_layout.insertWidget(0, self.value_input, stretch=1)
        self.bottom_layout.insertWidget(0, self.value_label)
        self.bottom_layout.insertWidget(0, self.address_input, stretch=1)
        self.bottom_layout.insertWidget(0, self.address_label)
        
        # Update the layouts
        self.bottom_layout.update()
        self.main_layout.update()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    
    layout.addWidget(SerialLogWidget(app, "Shutters", ["Shutter 1", "Shutter 2"]))
    layout.addWidget(ModbusLogWidget(app, "Sources", ["Source 1", "Source 2"]))
    
    window.setLayout(layout)
    window.setWindowTitle("Pressure Control Widget")
    window.show()
    sys.exit(app.exec())