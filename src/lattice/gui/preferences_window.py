from typing import Callable
from PySide6.QtGui import (
    QValidator
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
    QApplication
    )
import logging
import sys

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
        self.settings_to_inputs_map: dict[str, Callable] = {} 

        self.setWindowTitle("Preferences")
        self.resize(400, 300)
        main_layout = QVBoxLayout(self)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # General tab
        self.general_tab = QWidget()
        self.tabs.addTab(self.general_tab, "General")
        general_layout = QFormLayout(self.general_tab)

        spinbox = ScientificDoubleSpinBox()
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setDecimals(6)
        spinbox.setRange(0, 10000000)
        spinbox.setValue(config.PREFERENCES["pressure_warning_threshold"])
        self.settings_to_inputs_map["pressure_warning_threshold"] = lambda: spinbox.value()
        general_layout.addRow("Pressure Email Warning Threshold", spinbox)

        checkbox = QCheckBox()
        checkbox.setChecked(config.PREFERENCES["display_time_as_local_time"])
        self.settings_to_inputs_map["display_time_as_local_time"] = lambda: checkbox.isChecked()
        general_layout.addRow("Display Time as Local Time:", checkbox)

        # Apply and cancel buttons
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.apply_button)

        main_layout.addLayout(buttons_layout)

    def apply_settings(self):
        for setting, getter in self.settings_to_inputs_map.items():
            value = getter()
            if config.PREFERENCES[setting] != value:
                config.PREFERENCES[setting] = value
                print(f"Setting {setting} to {getter()}")

        config.PREFERENCES.save()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PreferencesWindow()
    window.show()
    sys.exit(app.exec())