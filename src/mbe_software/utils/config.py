import os
import logging
import yaml
import sys
from pathlib import Path

# Local imports
from mbe_software.definitions import ROOT_DIR

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, path, default: dict):
        self._path = path
        if os.path.exists(self._path):
            with open(self._path, 'r') as f:
                self.data = yaml.safe_load(f)
        else:
            self.data = default

    def save(self):
        with self._path.open("w") as f:
            yaml.safe_dump(self.data, f)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

# Get the directory of this script and set other important directories
CONFIG_DIR = ROOT_DIR / "config"
HARDWARE_CONFIG_PATH = CONFIG_DIR / 'hardware.yaml'
THEME_CONFIG_PATH = CONFIG_DIR / 'theme.yaml'
PARAMETER_CONFIG_PATH = CONFIG_DIR / 'parameters.yaml'
ALERT_CONFIG_PATH = CONFIG_DIR / 'alerts.yaml'

# Load hardware config or defaults
HARDWARE_DEFAULT = {
    "devices": {
        "pressure": {},
        "sources": {},
        "shutters": {}
    }
}
HARDWARE_CONFIG = Config(HARDWARE_CONFIG_PATH, HARDWARE_DEFAULT)

# Load theme config or defaults
THEME_DEFAULT = {
    "source_tab": {
        "colors": []
    }
}
THEME_CONFIG = Config(THEME_CONFIG_PATH, THEME_DEFAULT)

# Load parameter config or defaults
PARAMETER_DEFAULT = {
    "sources": {
        "safety": {}
    }
}
PARAMETER_CONFIG = Config(PARAMETER_CONFIG_PATH, PARAMETER_DEFAULT)

# Load parameter config or defaults
ALERT_DEFAULT = {
    "sender": "",
    "recipients": []
}
ALERT_CONFIG = Config(ALERT_CONFIG_PATH, ALERT_DEFAULT)
    
__all__ = [
    "HARDWARE_CONFIG", 
    "THEME_CONFIG", 
    "PARAMETER_CONFIG", 
    "ALERT_CONFIG"
]