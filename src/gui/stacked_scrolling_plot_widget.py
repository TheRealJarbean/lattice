from PySide6.QtWidgets import QApplication, QWidget, QGraphicsWidget
from PySide6.QtGui import QPainter
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
    def __init__(self, names: list[str], data: list[deque[(float, float)]], colors: list[str], use_scientific=True):
        super().__init__()
        
        if len(colors) < len(data):
            logger.error("Length of colors does not match length of data!")
            return

        # Store references to data and colors
        self.names = names
        self.data = data
        self.colors = colors
        
        # Create curves
        self.curves = [
            pg.PlotCurveItem(pen=pg.mkPen(self.colors[i], width=2))
            for i in range(len(data))
        ]
        
        # Set starting row
        row = 0
        
        # Create combined plot and add to layout
        self.combined_plot = self.addPlot(row=row, col=0)
        row+= 1
        
        # Change combined plot settings
        if use_scientific:
            self.combined_plot.setAxisItems({
                'left': ScientificAxis('left'),
            })
        self.combined_plot.setAxisItems({
            'bottom': TimeAxis('bottom')
        })
        self.combined_plot.setClipToView(True)
        self.combined_plot.setAutoVisible(x=True, y=True)
        
        # Create stacked plots and add to layout with delimiters
        self.stacked_plots = []
        self.delimiters = []
        for i in range(len(self.curves)):
            self.stacked_plots.append(self.addPlot(row=row, col=0))
            row += 1
            
        # Add dummy plot to stacked plot for shared x axis
        self.stacked_x_axis_plot = self.addPlot(row=row, col=0)
        self.stacked_x_axis_plot.setAxisItems({'bottom': TimeAxis('bottom')})
        self.stacked_x_axis_plot.hideAxis('left')
        self.stacked_x_axis_plot.setFixedHeight(20)
            
        # Change stacked plot settings
        for i, plot in enumerate(self.stacked_plots):
            plot.setClipToView(True)
            plot.setAutoVisible(x=True, y=True)
            if use_scientific:
                plot.setAxisItems({'left': ScientificAxis('left')})
            
            # Hide and link x axes
            plot.getAxis('bottom').setTicks([])
            plot.getAxis('bottom').setStyle(showValues=False)
            plot.setXLink(self.stacked_x_axis_plot)
        
        # Show combined by default
        self.is_stacked = True
        self._update_plot_display()
        
        # Create cursor tracking lines and labels
        self.cursor_lines = []
        self.cursor_labels = []
        
        for plot in [self.combined_plot] + self.stacked_plots:
            line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('y', width=1))
            label = pg.TextItem(color="y")

            plot.addItem(line, ignoreBounds=True)
            plot.addItem(label, ignoreBounds=True)

            line.hide()
            label.hide()

            self.cursor_lines.append(line)
            self.cursor_labels.append(label)
        
        # Connect mouse tracking
        self.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
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
                self.combined_plot.setXRange(max(0, max_time - time_delta), time_delta)
                self.stacked_plots[0].setXRange(max(0, max_time - time_delta), time_delta)
                
            # Keep cursor line at last known mouse pos
            if self._last_mouse_scene_pos is not None:
                # Update cursor position as if the mouse moved
                self._update_cursor_from_scene_pos(self._last_mouse_scene_pos)
    
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
        
    def _on_mouse_moved(self, pos):
        self._last_mouse_scene_pos = pos
        self._update_cursor_from_scene_pos(pos)
        
    def _update_cursor_from_scene_pos(self, pos):
        """Track mouse location and show cursor line in the active plot."""
        
        # Determine active plots depending on mode
        if self.is_stacked:
            active_plots = self.stacked_plots
            offset = 1  # because index 0 is combined_plot
        else:
            active_plots = [self.combined_plot]
            offset = 0

        # Hide everything first
        for line, label in zip(self.cursor_lines, self.cursor_labels):
            line.hide()
            label.hide()

        # Find the plot currently under the mouse
        target_index = None
        target_vb = None

        for i, plot in enumerate(active_plots):
            if plot.vb.sceneBoundingRect().contains(pos):
                target_index = i + offset  # adjust index for combined plot
                target_vb = plot.vb
                break

        if target_vb is None:
            return

        # Convert scene → data coords
        mouse_point = target_vb.mapSceneToView(pos)
        x = mouse_point.x()

        # Update line + label in the correct plot
        line = self.cursor_lines[target_index]
        label = self.cursor_labels[target_index]

        line.setPos(x)
        line.show()

        # Label at top of plot
        (_, _), (ymin, ymax) = target_vb.viewRange()
        label.setText(f"x = {x:.3f}")
        label.setPos(x, ymax)
        label.show()

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
    data = [deque(maxlen=200) for _ in range(n_signals)]

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