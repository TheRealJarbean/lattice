import os
import logging
import yaml
import platform
from pathlib import Path

# Local imports
from lattice.definitions import ROOT_DIR

logger = logging.getLogger(__name__)

APP_NAME = 'lattice'

class Config:
    def __init__(self, filename: str, default: dict):
        self._path = self.get_config_file(filename)
        if os.path.exists(self._path):
            with open(self._path, 'r') as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data is not None:
                    self.data = yaml_data
                    return
        
        self.data = default

        # Create file
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

# Load hardware config or defaults
HARDWARE_DEFAULT = {
    "devices": {
        "pressure": {},
        "sources": {},
        "shutters": {}
    }
}
HARDWARE_CONFIG = Config('hardware.yaml', HARDWARE_DEFAULT)

# Load theme config or defaults
THEME_DEFAULT = {
    "source_tab": {
        "colors": []
    }
}
THEME_CONFIG = Config('theme.yaml', THEME_DEFAULT)

# Load parameter config or defaults
PARAMETER_DEFAULT = {
    "sources": {
        "safety": {}
    }
}
PARAMETER_CONFIG = Config('parameters.yaml', PARAMETER_DEFAULT)

# Load parameter config or defaults
ALERT_DEFAULT = {
    "sender": "",
    "recipients": []
}
ALERT_CONFIG = Config('alerts.yaml', ALERT_DEFAULT)
    
__all__ = [
    "HARDWARE_CONFIG", 
    "THEME_CONFIG", 
    "PARAMETER_CONFIG", 
    "ALERT_CONFIG"
]