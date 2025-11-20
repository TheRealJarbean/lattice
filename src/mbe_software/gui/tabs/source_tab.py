from PySide6.QtWidgets import QWidget
import logging

# Local imports
from mbe_software.devices.source import Source

logger = logging.getLogger(__name__)

class SourceTab(QWidget):
    def __init__(self, sources: list[Source]):
        super.__init__()