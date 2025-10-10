from PySide6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QGridLayout, 
    QDoubleSpinBox,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QApplication,
    QWidget
    )
import logging
import sys

logger = logging.getLogger(__name__)

class InputModalWidget(QDialog):
    def __init__(self, labels, defaults=None, window_title=""):
        super().__init__()
        self.setWindowTitle(window_title)
        self.setModal(True) # Prevent main window interaction until closed
        
        # Main vertical layout
        main_layout = QVBoxLayout()
        
        # Grid layout for spinboxes, max 3 per row
        input_layout = QGridLayout()
        input_layout.setSpacing(10)
        
        # Create spinboxes + labels and add to layout
        self.spin_boxes = {}
        for i, label_text in enumerate(labels):
            label = QLabel(label_text)
            spin_box = QDoubleSpinBox()
            spin_box.setFixedWidth(100)
            spin_box.setStyleSheet("QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0; }") # Hide arrows
            spin_box.setDecimals(2)
            spin_box.setRange(0, 10000)
            input_layout.addWidget(label, i, 0)
            input_layout.addWidget(spin_box, i, 1)
            self.spin_boxes[label_text] = spin_box
            
        # Horizontal layout for buttons
        button_layout = QHBoxLayout()
        submit_button = QPushButton("Submit")
        cancel_button = QPushButton("Cancel")
        button_layout.addStretch()  # Center buttons
        button_layout.addWidget(submit_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        
        # Connect buttons to logic
        # Accept and reject are QDialog signals
        submit_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        # Add both layouts to main layout
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
    def get_values(self):
        return {key: spin_box.value() for key, spin_box in self.spin_boxes.items()}
    
# Run as standalone app for testing
if __name__ == "__main__":
    def open_modal():
        labels = ['First', 'Middle', 'Last']
        input_modal = InputModalWidget(labels, 'Test Modal')
        if input_modal.exec():
            logger.debug("Submitted:", input_modal.get_values())
        else:
            logger.debug("Cancelled")
    
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QHBoxLayout()
    test_button = QPushButton("Open Modal")
    test_button.clicked.connect(open_modal)
    layout.addWidget(test_button)
    window.setLayout(layout)
    window.setWindowTitle("Source Control Widget")
    window.show()
    sys.exit(app.exec())