from PySide6.QtWidgets import QWidget
import logging

logger = logging.getLogger(__name__)

class DiagnosticsTab(QWidget):
    def __init__(self):
        super.__init__()