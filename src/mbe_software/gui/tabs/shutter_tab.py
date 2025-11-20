from PySide6.QtWidgets import QWidget
import logging

# Local imports
from mbe_software.devices.shutter import Shutter

logger = logging.getLogger(__name__)

class ShutterTab(QWidget):
    def __init__(self, shutters: list[Shutter]):
        super.__init__()