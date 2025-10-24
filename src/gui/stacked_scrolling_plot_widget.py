from PySide6.QtWidgets import QApplication, QWidget, QGraphicsWidget
from PySide6.QtGui import QPainter
import pyqtgraph as pg
import numpy as np
import logging
from collections import deque

logger = logging.getLogger(__name__)

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


class StackedScrollingPlotWidget(QWidget):
    def __init__(self, names: list[str], data: list[deque[(float, float)]], colors: list[str]):
        super().__init__()
        
        if len(colors) < len(data):
            logger.error("Length of colors does not match length of data!")
            return

        # Store references to data and colors
        self.names = names
        self.data = data
        self.colors = colors

        # Create a GraphicsLayoutWidget
        self.layout = pg.GraphicsLayoutWidget()
        row = 0
        
        # Create curves
        self.curves = [
            pg.PlotCurveItem(pen=pg.mkPen(self.colors[i], width=2))
            for i in range(len(data))
        ]
        
        # Create combined plot and add to layout
        self.combined_plot = self.layout.addPlot(row=row, col=0)
        row+= 1
        
        # Change combined plot settings
        self.combined_plot.setAxisItems({'left': ScientificAxis('left')})
        
        # Create stacked plots and add to layout with delimiters
        self.stacked_plots = []
        self.delimiters = []
        for _ in self.curves:
            line = HorizontalLineWidget(width=1, color='w')
            self.delimiters.append(line)
            self.layout.addItem(line, row=row, col=0)
            row += 1
            
            self.stacked_plots.append(self.layout.addPlot(row=row, col=0))
            row += 1
            
        # Change stacked plot settings
        for i, plot in enumerate(self.stacked_plots):
            plot.setAxisItems({'left': ScientificAxis('left')})
            plot.setClipToView(True)
            plot.showAxis('bottom', show=(i == len(self.stacked_plots) - 1))
            
            if i > 0:
                # Link X axes
                plot.setXLink(self.stacked_plots[0])
        
        # Show combined by default
        self.show_combined()
        
    def update_data(self, time_delta: int = None):
        # Update the plot with new full dataset
        max_time = 0 # To scale x axis later
        for i in range(len(self.data)):
            if self.data[i]:
                timestamps, values = zip(*self.data[i])
                if timestamps[-1] > max_time:
                    max_time = timestamps[-1]
                self.curves[i].setData(
                    np.array(timestamps),
                    np.array(values)
                )

        # Optional: auto-scroll x-axis
        if time_delta:
            # Show last time_delta seconds
            if max_time >= time_delta:
                self.combined_plot.setXRange(max(0, max_time - time_delta), max_time)
                self.stacked_plots[0].setXRange(max(0, max_time - time_delta), max_time)
            else:
                self.stacked_plots[0].setXRange(max(0, max_time - time_delta), time_delta)
    
    def _update_plot_display(self):
        # Show stacked
        if self.is_stacked:
            self.combined_plot.hide()
        
            for i in range(len(self.stacked_plots)):
                self.stacked_plots[i].show()
                self.delimiters[i].show()
                
            # Add curves to stacked plots
            for i, curve in enumerate(self.curves):
                self.combined_plot.removeItem(curve)
                self.stacked_plots[i].addItem(curve)
                
            return
        
        # Show combined
        self.combined_plot.show()
        
        for i in range(len(self.stacked_plots)):
            self.stacked_plots[i].hide()
            self.delimiters[i].hide()
            
        # Add curves to combined plot
        for i, curve in enumerate(self.curves):
            self.stacked_plots[i].removeItem(curve)
            self.combined_plot.addItem(curve)
    
    def show_stacked(self):
        self.is_stacked = True
        self._update_plot_display()
        
    def show_combined(self):
        self.is_stacked = False
        self._update_plot_display()
        
        
        

if __name__ == '__main__':
    """
    AI GENERATED CODE WARNING
    """
    
    import sys
    from PySide6.QtWidgets import (
        QApplication, QVBoxLayout, QPushButton, QWidget, QHBoxLayout
    )
    from PySide6.QtCore import QTimer
    import random

    app = QApplication(sys.argv)

    # ---- Sample Data ----
    n_signals = 3
    names = [f"Signal {i+1}" for i in range(n_signals)]
    colors = ['r', 'g', 'c']
    data = [deque(maxlen=200) for _ in range(n_signals)]

    # ---- Main Widget ----
    main_widget = QWidget()
    main_layout = QVBoxLayout(main_widget)

    # Create instance of your plotting widget
    plot_widget = StackedScrollingPlotWidget(names, data, colors)
    plot_widget.show_combined()  # start in combined mode
    main_layout.addWidget(plot_widget.layout)

    # ---- Buttons to switch modes ----
    button_layout = QHBoxLayout()
    btn_split = QPushButton("Split Plots")
    btn_combine = QPushButton("Combine Plots")
    button_layout.addWidget(btn_split)
    button_layout.addWidget(btn_combine)
    main_layout.addLayout(button_layout)

    # ---- Connect buttons ----
    btn_split.clicked.connect(plot_widget.show_stacked)
    btn_combine.clicked.connect(plot_widget.show_combined)

    # ---- Data update simulation ----
    t = 0
    def update_data():
        global t
        t += 0.1
        for i in range(n_signals):
            val = random.uniform(-1, 1) * (i + 1)
            data[i].append((t, val))
        plot_widget.update_data(time_delta=10)

    timer = QTimer()
    timer.timeout.connect(update_data)
    timer.start(100)  # every 100 ms

    # ---- Show window ----
    main_widget.resize(800, 600)
    main_widget.setWindowTitle("SplitScrollingPlotWidget Preview")
    main_widget.show()

    sys.exit(app.exec())