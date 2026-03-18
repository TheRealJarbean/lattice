import sys
import traceback
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QRadioButton,
    QPushButton,
    QLabel,
    QMessageBox
)
from PySide6.QtCore import Qt

# Local imports
from lattice.app import MainAppWindow
from lattice.configurator import ConfiguratorWindow

class ModeChooser(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lattice Launcher")
        self.setFixedSize(380, 180)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.radio_main = QRadioButton("Start Lattice")
        self.radio_config = QRadioButton("Open Device Configuration")
        self.radio_main.setChecked(True)

        layout.addSpacing(10)
        layout.addWidget(self.radio_main)
        layout.addWidget(self.radio_config)
        layout.addStretch()

        btn_launch = QPushButton("Start")
        btn_launch.setDefault(True)
        btn_launch.clicked.connect(self.accept)
        layout.addWidget(btn_launch)

        self.setLayout(layout)

    def chosen_mode(self):
        if self.radio_config.isChecked():
            return "config"
        return "main"


def start():
    try:
        app = QApplication(sys.argv)

        chooser = ModeChooser()
        if chooser.exec() != QDialog.Accepted:
            sys.exit(0)  # user closed dialog → exit

        mode = chooser.chosen_mode()
        if mode == "main":
            window = MainAppWindow()
        else:
            window = ConfiguratorWindow()
        window.show()

        sys.exit(app.exec())
    
    except Exception as e:
        print("Something went wrong and Lattice Launcher failed to start:")
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    start()