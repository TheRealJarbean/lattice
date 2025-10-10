from PySide6.QtWidgets import QMainWindow
import logging

logger = logging.getLogger(__name__)

class PopoutTabWindow(QMainWindow):
    def __init__(self, widget, title):
        super().__init__()
        self.setWindowTitle(title)
        self.setCentralWidget(widget)
        self.show()