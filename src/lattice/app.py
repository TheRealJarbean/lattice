import sys
from PySide6.QtWidgets import (
    QApplication, QMenu, QMainWindow, QTabWidget
)
from PySide6.QtCore import Qt, QMutex, QEvent, QObject, QThread
from PySide6.QtGui import QAction
import logging
import os
import serial
from pathlib import Path
from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus import pymodbus_apply_logging_config

# Local imports
import lattice.utils.config as config
from lattice.devices import Shutter, Source, PressureGauge
from lattice.gui import *
from lattice.utils import EmailAlert

# Set the log level based on env variable when program is run
# Determines which logging statements are printed to console
# Only level used at time of writing is DEBUG
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}
# Disable pymodbus logging in favor of own logging
pymodbus_apply_logging_config(level=logging.CRITICAL)

logging.basicConfig(level=LOG_LEVEL_MAP[LOG_LEVEL])
logger = logging.getLogger(__name__)

# Clear focus from focusable widgets when clicking elsewhere on the screen
class FocusClearingFilter(QObject):
    def eventFilter(self, obj, event):
        # On mouse click
        if event.type() == QEvent.MouseButtonPress:
            widget = QApplication.widgetAt(event.globalPos())
            if widget is None or widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
                focused_widget = QApplication.focusWidget()
                if focused_widget is not None:
                    focused_widget.clearFocus()
                    
        return super().eventFilter(obj, event)
CLEAR_FOCUS_FILTER = FocusClearingFilter()

class MainAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Change default window size
        self.resize(1400, 900)
        
        # Configure email alerts
        self.alert = EmailAlert(config.ALERT_CONFIG['recipients'])
        
        # Apply focus clearing filter
        QApplication.instance().installEventFilter(CLEAR_FOCUS_FILTER)
        
        ##################
        # PRESSURE SETUP #
        ##################
        
        self.pressure_gauges: list[PressureGauge] = []

        # Populate pressure gauge list from config file
        for pressure_config in config.HARDWARE_CONFIG['devices']['pressure'].values():
            ser = serial.Serial(
                port=pressure_config['serial']['port'], 
                baudrate=pressure_config['serial']['baudrate'],
                timeout=0.1
                )
            
            mutex = QMutex()
            
            for gauge in pressure_config['connections']:
                self.pressure_gauges.append(PressureGauge(
                    name=gauge['name'], 
                    address=gauge['address'],
                    ser=ser,
                    serial_mutex=mutex
                    ))
        
        # Move pressure gauges to dedicated thread
        self.pressure_thread = QThread()
        for gauge in self.pressure_gauges:
            gauge.moveToThread(self.pressure_thread)

        # Start the pressure thread event loop
        self.pressure_thread.start()
        
        ################
        # SOURCE SETUP #
        ################
        
        self.sources: list[Source] = []
        
        if config.PARAMETER_CONFIG['sources']['safety'] is None:
            config.PARAMETER_CONFIG['sources']['safety'] = {}
        safety_settings = config.PARAMETER_CONFIG['sources']['safety']
        for source_config in config.HARDWARE_CONFIG['devices']['sources'].values():
            logger.debug(source_config)
            logger.debug(source_config['serial']['port'])
            client = ModbusClient(
                port=source_config['serial']['port'], 
                baudrate=source_config['serial']['baudrate'],
                timeout=0.1
                )
            mutex = QMutex()
            
            for device in source_config['connections']:
                self.sources.append(Source(
                    name=device['name'],
                    device_id=device['device_id'],
                    address_set=device['address_set'],
                    safety_settings=safety_settings.get(device['name'], {}),
                    client=client,
                    serial_mutex=mutex
                    ))
        
        # Move sources to dedicated thread
        self.source_thread = QThread()
        for source in self.sources:
            source.moveToThread(self.source_thread)

        # Start the source thread event loop
        self.source_thread.start()
        
        #################
        # SHUTTER SETUP #
        #################
        
        self.shutters: list[Shutter] = []
        
        for shutter_config in config.HARDWARE_CONFIG['devices']['shutters'].values():
            ser = serial.Serial(
                port=shutter_config['serial']['port'], 
                baudrate=shutter_config['serial']['baudrate'],
                timeout=0.1
                )
            
            serial_mutex = QMutex()
            
            self.shutters.extend([Shutter(
                name=shutter['name'], 
                address=shutter['address'], 
                ser=ser, 
                serial_mutex=serial_mutex
                ) for shutter in shutter_config['connections']])
        
        # Move shutters to dedicated thread
        self.shutter_thread = QThread()
        for shutter in self.shutters:
            shutter.moveToThread(self.shutter_thread)

        # Start the shutter thread event loop
        self.shutter_thread.start()
        
        ##############
        # GUI CONFIG #
        ##############

        self.pressure_tab = PressureTab(self.pressure_gauges)
        self.sources_tab = SourceTab(self.sources)
        self.shutter_tab = ShutterTab(self.shutters)

        self.recipe_tab = RecipeTab(
            gauges=self.pressure_gauges, 
            sources=self.sources, 
            shutters=self.shutters
            )
        
        self.diagnostics_tab = DiagnosticsTab(
            gauges=self.pressure_gauges,
            sources=self.sources,
            shutters=self.shutters
            )
        
        # Set tab bar context menu
        tab_widget = QTabWidget()
        tab_widget.addTab(self.pressure_tab, "Pressure")
        tab_widget.addTab(self.sources_tab, "Sources")
        tab_widget.addTab(self.shutter_tab, "Shutters")
        tab_widget.addTab(self.recipe_tab, "Recipe")
        tab_widget.addTab(self.diagnostics_tab, "Diagnostics")
        tab_widget.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        tab_widget.tabBar().customContextMenuRequested.connect(self.on_tab_context_menu)

        self.setCentralWidget(tab_widget)
    
    def on_tab_context_menu(self, point):
        tab_index = self.tab_widget.tabBar().tabAt(point)
        logger.debug(tab_index)
        
        if tab_index < 0:
            return # Didn't click a tab
        
        menu = QMenu()
        popout = QAction("Pop out tab", self)
        # Discard unneeded "checked" parameter and pass index
        popout.triggered.connect(lambda _, idx=tab_index: self.pop_out_tab(idx))
        menu.addAction(popout)
        
        # Show menu at global position
        menu.exec(self.tab_widget.tabBar().mapToGlobal(point))
    
    def pop_out_tab(self, tab_index):
        tab = self.tab_widget.widget(tab_index)
        tab_text = self.tab_widget.tabText(tab_index)
        logger.debug(f"Stored tab info {(tab_index, tab, tab_text)}")
        
        # Remove tab to re-parent it
        self.tab_widget.removeTab(tab_index)

        # Change tab to a window
        tab.setWindowFlags(Qt.Window)
        tab.setParent(None)
        tab.setWindowTitle(tab_text)
        
        # Place back in main window on closing popout
        def on_close(event):
            tab.setWindowFlags(Qt.Widget)
            self.tab_widget.addTab(tab, tab.windowTitle())
            
        tab.closeEvent = on_close
            
        # Show the popped out tab
        tab.show()

def start():
    app = QApplication(sys.argv)# 
    window = MainAppWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    start()