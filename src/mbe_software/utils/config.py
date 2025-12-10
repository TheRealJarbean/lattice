import os
import logging
import yaml
from importlib import resources

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, path, default: dict):
        self._path = path
        with path.open("r") as f:
            if os.path.exists(_hardware_config_path):
                with open(_hardware_config_path, 'r') as f:
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
_config_dir = resources.files("mbe_software.config")
_hardware_config_path = Config(_config_dir / 'hardware.yaml')
_theme_config_path = Config(_config_dir / 'theme.yaml')
_parameter_config_path = Config(_config_dir / 'parameters.yaml')
_alert_config_path = Config(_config_dir / 'alerts.yaml')

# Load hardware config or defaults
_hardware_default = {
    "devices": {
        "pressure": {},
        "sources": {},
        "shutters": {}
    }
}
HARDWARE_CONFIG = Config(_hardware_config_path, _hardware_default)

# Load theme config or defaults
_theme_default = {
    "source_tab": {
        "colors": []
    }
}
THEME_CONFIG = Config(_theme_config_path, _theme_default)

# Load parameter config or defaults
_parameter_default = {
    "sources": {
        "safety": {}
    }
}
PARAMETER_CONFIG = Config(_parameter_config_path, _parameter_default)

# Load parameter config or defaults
_alert_default = {
    "sender": "",
    "recipients": []
}
ALERT_CONFIG = Config(_alert_config_path, _alert_default)
    
__all__ = [
    "HARDWARE_CONFIG", 
    "THEME_CONFIG", 
    "PARAMETER_CONFIG", 
    "ALERT_CONFIG"
]