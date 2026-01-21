from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtCore import QThread, QTimer, Signal
import logging
import time

# Local imports
from lattice.devices.shutter import Shutter
from lattice.gui.widgets import ShutterControlWidget
from .ui_shutter_tab import Ui_ShutterTab

logger = logging.getLogger(__name__)

class ShutterTab(QWidget, Ui_ShutterTab):
    open_shutter = Signal(Shutter)
    close_shutter = Signal(Shutter)
    send_command = Signal(Shutter, str) # Shutter reference, command

    def __init__(self, shutters: list[Shutter]):
        super().__init__()
        self.setupUi(self)
        
        self.shutters = shutters

        #########
        # SETUP #
        #########
            
        # The on_shutter_state_change function will handle any gui
        # changes that need to be made based on shutter state
        # The index of the shutter is baked to the connection in for reference later
        for i, shutter in enumerate(self.shutters):
            shutter.is_open_changed.connect(self.on_state_change)
            self.open_shutter.connect(shutter.open)
            self.close_shutter.connect(shutter.close)
            self.send_command.connect(shutter.send_custom_command)
        
        self.current_step = 0
        self.loop_step_timer = QTimer()
        self.loop_step_timer.setSingleShot(True)
        self.loop_step_timer.timeout.connect(self._trigger_next_step)
        
        # The two QElapsed timers remain accurate even if the program or system lags
        self.loop_time_elapsed_ms = 0
        self.step_time_elapsed_ms = 0
        self.loop_stopwatch_update_timer = QTimer()
        self.loop_stopwatch_update_timer.timeout.connect(self.update_loop_timers)

        ###################
        # CONTROLS CONFIG #
        ###################
        
        # Create shutter control widgets
        controls_layout = getattr(self, "shutter_controls_layout", None)
        self.control_widgets: list[ShutterControlWidget] = []
        for shutter in self.shutters:
            widget = ShutterControlWidget(shutter.name, 6)
            self.control_widgets.append(widget)
            controls_layout.addWidget(widget)
            
        # Connect shutter controls displays and buttons
        for i, controls in enumerate(self.control_widgets):
            # Connect control buttons and set property
            controls.control_button.clicked.connect(self.on_control_button_click)
            controls.control_button.setProperty('idx', i)
            
            # Connect output buttons and set property
            controls.output_button.clicked.connect(self.on_output_button_click)
            controls.output_button.setProperty('idx', i)
            
            # Connect state buttons and set property
            for button in controls.step_state_buttons:
                button.clicked.connect(self.on_step_state_button_clicked)
                button.setProperty('idx', i)
            
        # Connect shutter disable all button
        control_off_all_button = getattr(self, "shutter_control_off_all")
        control_off_all_button.clicked.connect(self.on_control_off_all_click)
                
        # Connect start/stop button to logic
        loop_toggle_button = getattr(self, "shutter_loop_toggle")
        loop_toggle_button.clicked.connect(self.on_toggle_loop_button_click)

        # Connect state time inputs
        num_states = 6
        for i in range(num_states):
            widget = getattr(self, f"state_time_{i}", None)
            if widget:
                widget.valueChanged.connect()

    def on_toggle_loop_button_click(self):
        button = self.sender()
        self.current_step = 0
        
        step_display = getattr(self, "shutter_current_step", None)
        step_display.setText("0")
        loop_count_display = getattr(self, "shutter_loop_count", None)
        loop_count_display.setProperty("loop_count", 0)
        loop_count_display.setText("0")
        
        # If loop is already running
        if self.loop_step_timer.isActive():
            self.loop_step_timer.stop()
            self.loop_stopwatch_update_timer.stop()
            self.reset_loop_timers()
            button.setText("Start")
            button.setStyleSheet("""
                font: 48pt "Segoe UI";
                background-color: rgb(0, 255, 0);
                """)
            return
        
        # If loop is not running
        # TODO: Disable shutter loop GUI
        button.setText("Stop")
        button.setStyleSheet("""
            font: 48pt "Segoe UI";
            background-color: rgb(255, 0, 0);
            """)
        self.loop_start_time = time.monotonic()
        self.loop_stopwatch_update_timer.start(100)
        self._trigger_next_step()
        
    def _trigger_next_step(self):
        step = self.current_step
        
        # Increment loop count
        if step == 0:
            loop_count_display = getattr(self, "shutter_loop_count", None)
            count = loop_count_display.property("loop_count")
            loop_count_display.setProperty("loop_count", count + 1)
            loop_count_display.setText(f"{count + 1}")
        
        # Display current step
        step_display = getattr(self, "shutter_current_step", None)
        step_display.setText(f"{step + 1}") # Match user-facing number, not index
        
        # Store step start time
        self.step_start_time = time.monotonic()
        
        logger.debug(f"Triggering shutter loop step {step + 1}")
        
        
        for i, controls in enumerate(self.control_widgets):
            is_open = controls.step_state_buttons[step].property("is_open")
            if is_open:
                self.open_shutter.emit(self.shutters[i])
            else:
                self.close_shutter.emit(self.shutters[i])
        
        # Display elapsed time for state
        time_input_widget = getattr(self, f"step_time_{step + 1}", None)
        state_time = int(time_input_widget.value() * 1000) # Sec to ms
        logger.debug(f"State time is {state_time}")
        
        # Increment step and check if max step has been reached
        max_step_input_widget = getattr(self, "max_loop_step", None)
        max_step = max_step_input_widget.value() - 1 # Indexing starts at 0, user-facing count starts at 1
        if self.current_step < max_step:
            self.current_step += 1
        else:
            self.current_step = 0
        
        # Start timer to trigger next step
        if self.loop_step_timer.isActive():
            self.loop_step_timer.stop()
        self.loop_step_timer.start(state_time)
        
    def update_loop_timers(self):
        loop_seconds = time.monotonic() - self.loop_start_time
        step_seconds = time.monotonic() - self.step_start_time
        
        loop_timer = getattr(self, "shutter_loop_time_elapsed", None)
        step_timer = getattr(self, "shutter_loop_time_in_step", None)
        
        loop_timer.setText(f"{loop_seconds:04.1f} s")
        step_timer.setText(f"{step_seconds:04.1f} s")
        
    def reset_loop_timers(self):
        loop_timer = getattr(self, "shutter_loop_time_elapsed", None)
        step_timer = getattr(self, "shutter_loop_time_in_step", None)
        
        loop_timer.setText(f"{0:04.1f} s")
        step_timer.setText(f"{0:04.1f} s")
        
    def on_step_state_button_clicked(self):
        button = self.sender()
        is_open = button.property('is_open')
            
        if is_open:
            button.setText("Closed")
            button.setProperty("is_open", False)
        else:
            button.setText("Open")
            button.setProperty("is_open", True)
        
        # Refresh button style
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
            
    def on_control_button_click(self):
        button: QPushButton = self.sender()
        is_on = button.property("is_on")
        idx = button.property("idx")
            
        if is_on:
            button.setText("OFF")
            button.setProperty("is_on", False)
            self.shutters[idx].disable()
        else:
            button.setText("ON")
            button.setProperty("is_on", True)
            self.shutters[idx].enable()
        
        # Refresh button style
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
    
    def on_control_off_all_click(self):
        for shutter in self.shutters:
            shutter.disable()
            
        for controls in self.control_widgets:
            button = controls.control_button
            button.setProperty('is_on', False)
            button.setText("OFF")
            
            # Refresh button style
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
            
    def on_output_button_click(self):
        button: QPushButton = self.sender()
        is_open = button.property("is_open")
        idx = button.property("idx")
            
        if is_open:
            self.close_shutter.emit(self.shutters[idx])
        else:
            self.open_shutter.emit(self.shutters[idx])
            
        # Refresh button style
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
        
    def on_state_change(self, shutter: Shutter, is_open):
        for idx, s in enumerate(self.shutters):
            if s is not shutter:
                continue
            
            button = self.control_widgets[idx].output_button
            button.setText("Open" if is_open else "Closed")
            button.setProperty('is_open', is_open)
        
            # Refresh button style
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()