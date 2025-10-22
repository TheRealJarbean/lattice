from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsLineItem, QGraphicsWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QPainter
import pyqtgraph as pg
import numpy as np

class ScientificAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [f"{v:+.2e}" for v in values]

class HorizontalLineWidget(QGraphicsWidget):
    def __init__(self, width=1, color='w', parent=None):
        super().__init__(parent)
        self.pen = pg.mkPen(color)
        self.pen.setWidth(width)
        self.setMinimumHeight(width)
        self.setPreferredHeight(width)
        self.setMaximumHeight(width)

    def paint(self, painter: QPainter, option, widget=None):
        rect = self.boundingRect()
        y = rect.height() / 2
        painter.setPen(self.pen)
        painter.drawLine(rect.left(), y, rect.right(), y)


class StackedPlot(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stacked Signals - Fixed Axis Alignment")

        # Sample data
        self.x = np.linspace(0, 10, 1000)
        self.y_data = [
            np.sin(self.x),
            0.5 * np.cos(self.x * 2),
            2 * np.sin(self.x * 3 + 1)
        ]
        self.colors = ['r', 'g', 'b']

        # Create a central GraphicsLayoutWidget
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.setCentralWidget(self.plot_layout)

        self.plots = []
        self.curves = []
        self.left_axes = []
        self.row=0

        # Create stacked plot
        for i, y in enumerate(self.y_data):
            line = HorizontalLineWidget(width=1, color='w')
            self.plot_layout.addItem(line, row=self.row, col=0)
            self.row += 1
            p = self.plot_layout.addPlot(row=self.row, col=0)
            self.row += 1
            p.setMenuEnabled(False)
            p.setMouseEnabled(x=True, y=True)
            p.showAxis('bottom', show=(i == len(self.y_data) - 1))  # Only bottom plot shows X-axis
            p.setLabel('left', f"Signal {i+1}")
            p.setYRange(np.min(y), np.max(y), padding=0.1)
            p.setAxisItems({'left': ScientificAxis('left')})

            curve = p.plot(self.x, y, pen=self.colors[i])

            self.plots.append(p)
            self.curves.append(curve)

            if i > 0:
                # Link X axes
                p.setXLink(self.plots[0])
                
            
        print(self.plot_layout.items())

if __name__ == '__main__':
    app = QApplication([])
    win = StackedPlot()
    win.show()
    app.exec()