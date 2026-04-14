import os
import logging
import yaml
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = 'lattice'

class Config:
    def __init__(self, filename: str, default: dict):
        self._path = self.get_config_file(filename)
        self.data = None
        if os.path.exists(self._path):
            with open(self._path, 'r') as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data is not None:
                    self.data = yaml_data

        if self.data is None:
            self.data = default
            self.save()
            return

        def copy_missing_keys(dict1, dict2):
            for key in dict1.keys():
                if key not in dict2.keys():
                    dict2[key] = dict1[key]
                    continue

                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    if dict1[key]:
                        copy_missing_keys(dict1[key], dict2[key])

        copy_missing_keys(default, self.data)
        self.save()

    def save(self):
        # Ensure parent "config" directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with self._path.open("w") as f:
            yaml.safe_dump(self.data, f)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __str__(self):
        return self.data.__str__()

    def get_config_dir(self):
        system = platform.system()

        if system == "Windows":
            return Path.home() / "AppData" / "Roaming" / APP_NAME
        elif system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / APP_NAME
        else:  # Linux
            return Path.home() / ".config" / APP_NAME

    def get_config_file(self, filename: str):
        return self.get_config_dir() / filename
    
class AppConfig:
    PREFERENCES_DEFAULT = {
        "pressure_warning_threshold": 1e-5,
        "display_time_as_local_time": True,
    }
    PREFERENCES = Config('preferences.yaml', PREFERENCES_DEFAULT)

    # Load hardware config or defaults
    HARDWARE_DEFAULT = {
        "devices": {
            "pressure": {},
            "sources": {},
            "shutters": {}
        }
    }
    HARDWARE = Config('hardware.yaml', HARDWARE_DEFAULT)

    # Load theme config or defaults
    THEME_DEFAULT = {
        "source_tab": {
            "colors": []
        }
    }
    THEME = Config('theme.yaml', THEME_DEFAULT)

    # Load parameter config or defaults
    PARAMETER_DEFAULT = {
        "sources": {
            "safety": {}
        }
    }
    PARAMETER = Config('parameters.yaml', PARAMETER_DEFAULT)

    # Load parameter config or defaults
    ALERT_DEFAULT = {
        "sender": "",
        "recipients": []
    }
    ALERT = Config('alerts.yaml', ALERT_DEFAULT)