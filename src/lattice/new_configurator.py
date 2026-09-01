import sys
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QRadioButton,
    QPushButton,
    QLabel,
    QMessageBox,
    QWidget,
    QMainWindow
)
from PySide6.QtCore import Qt
import os

# Local imports
from lattice.utils import AppConfig

class ConfiguratorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        config = AppConfig.HARDWARE
        print(config)
        self.setWindowTitle("Device Configurator")

def start():
    app = QApplication(sys.argv)

    window = ConfiguratorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    start()