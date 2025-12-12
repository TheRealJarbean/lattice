from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QThread
import pyqtgraph as pg
import numpy as np
import logging
from collections import deque

logger = logging.getLogger(__name__)

# Custom axis for scientific notation in plots
class ScientificAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [f"{v:+.2e}" for v in values]
    
# Custom axis for time in plots
class TimeAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        def format_time(total_seconds):
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return [format_time(int(v)) for v in values]

class StackedScrollingPlotWidget(pg.GraphicsLayoutWidget):
    def __init__(self, names: list[str], data_dict: list[deque[(float, float)]], colors: list[str]):
        super().__init__()
        
        if len(colors) < len(data_dict):
            logger.error("Length of colors does not match length of data!")
            return

        # Store references to data and colors
        self.names = names
        self.data_dict = data_dict
        self.colors = colors
        
        # Create curves
        self.curves = [
            pg.PlotCurveItem(pen=pg.mkPen(self.colors[i], width=2))
            for i in range(len(data_dict))
        ]
        
        # Set starting row
        row = 0
        
        # Create combined plot and add to layout
        self.combined_plot = self.addPlot(row=row, col=0)
        row+= 1
        
        # Change combined plot settings
        self.combined_plot.setAxisItems({
            'left': ScientificAxis('left'),
            'bottom': TimeAxis('bottom')
        })
        self.combined_plot.setClipToView(True)
        self.combined_plot.setAutoVisible(x=True, y=True)
        
        # Create stacked plots and add to layout with delimiters
        self.stacked_plots = []
        self.delimiters = []
        for _ in range(len(self.curves)):
            self.stacked_plots.append(self.addPlot(row=row, col=0))
            row += 1
            
        # Add dummy plot to stacked plot for shared x axis
        self.stacked_x_axis_plot = self.addPlot(row=row, col=0)
        self.stacked_x_axis_plot.setAxisItems({'bottom': TimeAxis('bottom')})
        self.stacked_x_axis_plot.hideAxis('left')
        self.stacked_x_axis_plot.setFixedHeight(20)
            
        # Change stacked plot settings
        for plot in self.stacked_plots:
            plot.setClipToView(True)
            plot.setAutoVisible(x=True, y=True)
            plot.setAxisItems({'left': ScientificAxis('left')})
            
            # Hide and link x axes
            plot.getAxis('bottom').setTicks([])
            plot.getAxis('bottom').setStyle(showValues=False)
            plot.setXLink(self.stacked_x_axis_plot)
        
        # Show combined by default
        self.is_stacked = False
        self._update_plot_display()
        
    def update_data(self, time_delta: int = None):
        # Update the plot with new full dataset
        max_time = 0 # To scale x axis later
        for i, data in enumerate(self.data_dict.values()):
            if data:
                arr = np.array(data)
                timestamps = arr[:, 0]
                values = arr[:, 1]
                
                self.curves[i].setData(timestamps, values)
                
                if timestamps[-1] > max_time:
                    max_time = timestamps[-1]

        # Optional: auto-scroll x-axis
        if time_delta:
            # Show last time_delta seconds
            if max_time >= time_delta:
                self.combined_plot.setXRange(max(0, max_time - time_delta), max_time)
                self.stacked_plots[0].setXRange(max(0, max_time - time_delta), max_time)
            else:
                self.combined_plot.setXRange(max(0, max_time - time_delta), time_delta)
                self.stacked_plots[0].setXRange(max(0, max_time - time_delta), time_delta)
    
    def _update_plot_display(self):
        # Set visibility of combined plot
        self.combined_plot.setVisible(not self.is_stacked)
        
        # Set visiblity of stacked plots
        for plot in self.stacked_plots:
            plot.setVisible(self.is_stacked)
            
        # Set visibility of stacked x axis plot
        self.stacked_x_axis_plot.setVisible(self.is_stacked)
        
        # Assign curves to visible plot(s)
        if self.is_stacked:
            for i, curve in enumerate(self.curves):
                self.combined_plot.removeItem(curve)
                self.stacked_plots[i].addItem(curve)
            return
        
        for i, curve in enumerate(self.curves):
            self.stacked_plots[i].removeItem(curve)
            self.combined_plot.addItem(curve)
    
    def show_stacked(self):
        if self.is_stacked:
            return
        
        self.is_stacked = True
        self._update_plot_display()
        
    def show_combined(self):
        if not self.is_stacked:
            return
        
        self.is_stacked = False
        self._update_plot_display()
        
if __name__ == '__main__':
    """
    AI GENERATED CODE WARNING
    Just a simple app with random data for testing
    """
    
    import sys
    from PySide6.QtWidgets import (
        QApplication, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QLineEdit, QLabel
    )
    from PySide6.QtCore import QTimer
    import random
    import time
    from collections import deque

    app = QApplication(sys.argv)

    # ---- Sample Data ----
    n_signals = 3
    names = [f"Signal {i+1}" for i in range(n_signals)]
    colors = ['r', 'g', 'c']
    data = {i: deque(maxlen=200) for i in range(n_signals)}

    # ---- Main Widget ----
    main_widget = QWidget()
    main_layout = QVBoxLayout(main_widget)

    # Create instance of your plotting widget
    plot_widget = StackedScrollingPlotWidget(names, data, colors)
    plot_widget.show_combined()  # start in combined mode
    main_layout.addWidget(plot_widget)

    # ---- Buttons to switch modes ----
    button_layout = QHBoxLayout()
    btn_split = QPushButton("Split Plots")
    btn_combine = QPushButton("Combine Plots")
    button_layout.addWidget(btn_split)
    button_layout.addWidget(btn_combine)
    main_layout.addLayout(button_layout)

    # ---- Time delta control ----
    control_layout = QHBoxLayout()
    control_layout.addWidget(QLabel("Time window (s):"))
    time_delta_edit = QLineEdit()
    time_delta_edit.setText("10")  # default value
    time_delta_edit.setFixedWidth(60)
    control_layout.addWidget(time_delta_edit)
    main_layout.addLayout(control_layout)

    # ---- Connect buttons ----
    btn_split.clicked.connect(plot_widget.show_stacked)
    btn_combine.clicked.connect(plot_widget.show_combined)

    # ---- Data update simulation ----
    start_time = time.monotonic()
    def update_data():
        t = time.monotonic() - start_time
        # Read time_delta from the edit field
        try:
            time_delta = float(time_delta_edit.text())
        except ValueError:
            time_delta = 10  # fallback to default
        for i in range(n_signals):
            val = random.uniform(-1, 1) * (i + 1)
            data[i].append((t, val))
        plot_widget.update_data(time_delta=time_delta)

    timer = QTimer()
    timer.timeout.connect(update_data)
    timer.start(100)  # every 100 ms

    # ---- Show window ----
    main_widget.resize(800, 600)
    main_widget.setWindowTitle("SplitScrollingPlotWidget Preview")
    main_widget.show()

    sys.exit(app.exec())