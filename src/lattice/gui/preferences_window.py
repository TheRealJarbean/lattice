from typing import Callable
from PySide6.QtCore import (
    Qt
)
from PySide6.QtGui import (
    QValidator,
    QRegularExpressionValidator
)
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QDoubleSpinBox,
    QAbstractSpinBox,
    QCheckBox,
    QHBoxLayout,
    QPushButton,
    QApplication,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QGridLayout,
    QFrame
    )
import logging
import sys
import keyring

# Local imports
import lattice.utils.config as config

logger = logging.getLogger(__name__)

class ScientificDoubleSpinBox(QDoubleSpinBox):
    def textFromValue(self, value: float) -> str:
        return f"{value:.6g}"  # allows scientific format

    def valueFromText(self, text: str) -> float:
        try:
            return float(text)
        except ValueError:
            return 0.0

    def validate(self, text, pos):
        try:
            float(text)
            return (QValidator.Acceptable, text, pos)
        except ValueError:
            if all(c in "-.eE1234567890" for c in text) or text == "":
                return (QValidator.Intermediate, text, pos)
            return (QValidator.Invalid, text, pos)

class PreferencesWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Key: setting name, Value: getter method
        # ex. "is_box_checked", lambda: box.isChecked()
        self.preferences_to_inputs_map: dict[str, Callable] = {}
        self.alerts_to_inputs_map: dict[str, Callable] = {} 

        self.setWindowTitle("Preferences")
        self.resize(400, 500)
        main_layout = QVBoxLayout(self)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        ###############
        # General tab #
        ###############

        self.general_tab = QWidget()
        self.tabs.addTab(self.general_tab, "General")
        general_layout = QFormLayout(self.general_tab)

        # Pressure alert threshold
        spinbox = ScientificDoubleSpinBox(value=config.PREFERENCES["pressure_warning_threshold"])
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setDecimals(6)
        spinbox.setRange(0, 10000000)
        self.preferences_to_inputs_map["pressure_warning_threshold"] = lambda: spinbox.value()
        general_layout.addRow("Pressure Email Warning Threshold", spinbox)
        
        # Display time as local time
        checkbox = QCheckBox()
        checkbox.setChecked(config.PREFERENCES["display_time_as_local_time"])
        self.preferences_to_inputs_map["display_time_as_local_time"] = lambda: checkbox.isChecked()
        general_layout.addRow("Display Time as Local Time", checkbox)

        ####################
        # Email Alerts tab #
        ####################
        self.alerts_tab = QWidget()
        self.tabs.addTab(self.alerts_tab, "Email Alerts")
        alerts_layout = QVBoxLayout(self.alerts_tab)

        # Instructions
        instructions = QLabel(
            """
            For gmail:
            <ol>
            <li>Navigate to <a href="https://myaccount.google.com/apppasswords">https://myaccount.google.com/apppasswords</a></li>
            <li>Enter the password below and click update*, this will store
               the password in the system keyring and associate it with the
               sender email.</li>
            <li>Restart the app to authenticate and activate alerts.</li
            </ol>
            *Click the apply button to update the sender email
            """
        )
        instructions.setTextFormat(Qt.TextFormat.RichText)
        instructions.setWordWrap(True)
        alerts_layout.addWidget(instructions)

        # Sender
        sender = QLineEdit(config.ALERT_CONFIG['sender'])
        sender.setPlaceholderText("sender@cooldomain.com")
        self.alerts_to_inputs_map['sender'] = lambda: sender.text()
        sender.setValidator(QRegularExpressionValidator(r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+"))

        # App password
        self.app_password_input = QLineEdit()
        update_button = QPushButton("Update")
        update_button.clicked.connect(self.update_app_password)

        widget = QWidget()
        alerts_layout.addWidget(widget)
        grid = QGridLayout(widget)
        grid.addWidget(QLabel("Sender"), 0, 0)
        grid.addWidget(sender, 0, 1, 1, 2)
        grid.addWidget(QLabel("App Password"), 1, 0)
        grid.addWidget(self.app_password_input, 1, 1)
        grid.addWidget(update_button, 1, 2)

        # Horizontal line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        alerts_layout.addWidget(line)

        # Recipients
        alerts_layout.addWidget(QLabel("Recipients"))
        recipients = QPlainTextEdit(',\n'.join(config.ALERT_CONFIG['recipients']))
        recipients.setPlaceholderText("someone@cooldomain.com,\nsomeone.else@cooldomain.com")
        self.alerts_to_inputs_map['recipients'] = lambda: [r for r in recipients.toPlainText().replace('\n', '').replace(' ', '').strip().split(',')]
        alerts_layout.addWidget(recipients)

        #############
        # Finish up #
        #############

        # Apply and cancel buttons
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.apply_button)

        main_layout.addLayout(buttons_layout)

    def apply_settings(self):
        for setting, getter in self.preferences_to_inputs_map.items():
            value = getter()
            if config.PREFERENCES[setting] != value:
                config.PREFERENCES[setting] = value
                print(f"Setting {setting} to {getter()}")

        for setting, getter in self.alerts_to_inputs_map.items():
            value = getter()
            if config.ALERT_CONFIG[setting] != value:
                config.ALERT_CONFIG[setting] = value
                print(f"Setting {setting} to {getter()}")

        config.PREFERENCES.save()
        config.ALERT_CONFIG.save()

    def update_app_password(self):
        """
        The password that is stored is a Google account **app password**. The **app password** is generated once by logging in
        to the account as normal, and navigating to the settings page linked below.

        # NOTES
            - DO NOT SAVE OR COMMIT THE APP PASSWORD.

        # LINKS
        Manage App Passwords - https://myaccount.google.com/apppasswords
        """
        sender = config.ALERT_CONFIG['sender']
        password = self.app_password_input.text()
        keyring.set_password('lattice', sender, password)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PreferencesWindow()
    window.show()
    sys.exit(app.exec())