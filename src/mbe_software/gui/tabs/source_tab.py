from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QThread
import logging

# Local imports
from mbe_software.devices.source import Source

logger = logging.getLogger(__name__)

class SourceTab(QWidget):
    def __init__(self, sources: list[Source]):
        super.__init__()
        
        ##########
        # CONFIG #
        ##########
        
        # Create dict for accessing sources by name
        self.source_dict = {source.name: source for source in self.sources}
        
        # Create thread
        self.source_thread = QThread()
        for source in self.sources:
            source.moveToThread(self.source_thread)

        # Initialize source data object
        self.source_process_variable_data = []
        self.source_working_setpoint_data = []
        for _ in range(len(self.sources)):
            self.source_process_variable_data.append(deque(maxlen=7200)) # 3 hours of data at default polling rate of 500ms
            self.source_working_setpoint_data.append(deque(maxlen=7200))

        # Connect source process variable and working setpoint changes to data handling
        for i in range(len(self.sources)):
            self.sources[i].process_variable_changed.connect(partial(self.on_new_source_process_variable, i))
            self.sources[i].working_setpoint_changed.connect(partial(self.on_new_source_working_setpoint, i))
            
        ##############
        # GUI CONFIG #
        ##############
        
        # Create the source control widgets
        self.source_controls_layout = getattr(self, "source_controls", None)
        self.source_controls: list[SourceControlWidget] = []
    
        while len(theme_config['source_tab']['colors']) < len(self.sources):
            theme_config['source_tab']['colors'].append("FFFFFF")
        
        colors = theme_config['source_tab']['colors']
            
        for i in range(len(self.sources)):
            color = "FFFFFF" # Default color
            if 0 <= i < len(colors):
                color = colors[i]
            controls = SourceControlWidget(color=f"#{color}")
            self.source_controls.append(controls)
            self.source_controls_layout.addWidget(controls)
        
        # Apply per-control widget config and connections
        for i, controls in enumerate(self.source_controls):
            # Set source name labels
            controls.label.setText(self.sources[i].get_name())
            
            # Connect color change methods
            controls.circle.color_changed.connect(partial(self.on_source_color_change, i))
            
            # Assign modals to PID and Safe Rate Limit buttons
            controls.pid_button.clicked.connect(partial(self.open_pid_input_modal, i))
            controls.safety_button.clicked.connect(partial(self.open_safe_rate_limit_input_modal, i))

            # Connect set buttons
            controls.set_setpoint_button.clicked.connect(partial(self.on_source_setpoint_set_clicked, i))
            controls.set_rate_limit_button.clicked.connect(partial(self.on_source_rate_limit_set_clicked, i))
            
            # Connect working setpoint plot checkboxes
            controls.plot_working_setpoint.stateChanged.connect(
                lambda state, i=i: self.source_working_setpoint_curves[i].setVisible(bool(state))
                )
            
            # Connect variable displays
            self.sources[i].process_variable_changed.connect(
                lambda pv, c=controls: c.display_temp.setText(f"{pv:.2f} C")
            )
            self.sources[i].setpoint_changed.connect(
                lambda sp, c=controls: c.display_setpoint.setText(f"{sp:.2f} C")
            )
            self.sources[i].working_setpoint_changed.connect(
                lambda wsp, c=controls: c.display_working_setpoint.setText(f"{wsp:.2f} C")
            )
            self.sources[i].rate_limit_changed.connect(
                lambda rate, c=controls: c.display_rate_limit.setText(f"{rate:.2f} C/s") # Convert form /min to /s
            )
            
            # TODO: Connect extra display for power depending on mg_bulk and mg_cracker needs
            
        # Configure source data plot
        self.source_graph_widget.plotItem.setAxisItems({'bottom': TimeAxis('bottom')})
        self.source_graph_widget.enableAutoRange(axis='x', enable=False)
        self.source_graph_widget.enableAutoRange(axis='y', enable=True)
        self.source_graph_widget.setXRange(0, 30)
        
        # Create curves
        self.source_process_variable_curves: list[pg.PlotCurveItem] = []
        self.source_working_setpoint_curves: list[pg.PlotCurveItem] = []
        for controls in self.source_controls:
            self.source_process_variable_curves.append(self.source_graph_widget.plot(pen=pg.mkPen(controls.circle.color, width=2)))
            self.source_working_setpoint_curves.append(self.source_graph_widget.plot(pen=pg.mkPen(controls.circle.color, width=2, style=Qt.DashLine)))
        
        # Clip rendered data to only what is currently visible
        for curve in self.source_process_variable_curves + self.source_working_setpoint_curves:
            curve.setClipToView(True)
        
        # Hide working setpoint curves by default
        for curve in self.source_working_setpoint_curves:
            curve.setVisible(False)
            
        # Add cursor tracking line
        self.source_cursor_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('y', width=1))
        self.source_cursor_label = pg.TextItem(color="y")

        self.source_graph_widget.plotItem.addItem(self.source_cursor_line, ignoreBounds=True)
        self.source_graph_widget.plotItem.addItem(self.source_cursor_label, ignoreBounds=True)

        self.source_cursor_line.hide()
        self.source_cursor_label.hide()
        
        # Connect mouse tracking
        self._last_mouse_scene_pos = None
        self.source_graph_widget.scene().sigMouseMoved.connect(self._on_source_mouse_moved)
            
        # Start timer to update source data plot
        self.source_plot_update_timer = QTimer()
        self.source_plot_update_timer.timeout.connect(self.update_source_plot)
        self.source_plot_update_timer.start(20)