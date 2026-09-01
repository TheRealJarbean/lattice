from PySide6.QtWidgets import (
    QApplication, QMenu, QMainWindow, QTabWidget
)
from PySide6.QtCore import Qt, QMutex, QEvent, QObject, QThread
import serial
import logging
from pymodbus.client import ModbusSerialClient as ModbusClient

# Local imports
from lattice.devices import (
    Motor,
    Shutter,
    SubstrateMotor,
    PressureGauge,
    Camera,
    Source,
    LoadingMotor
)
from lattice.utils.config import AppConfig

logger = logging.getLogger(__name__)

LOADING_MOTOR_GEAR_RATIO = 45
SUBSTRATE_MOTOR_GEAR_RATIO = 40

class DeviceManager():
    def initialize(self, simulate_devices=False):
        ##################
        # PRESSURE SETUP #
        ##################
        
        self.pressure_gauges: list[PressureGauge] = []
        self.pressure_thread = QThread()

        # Populate pressure gauge list from config file
        for pressure_config in AppConfig.HARDWARE['devices']['pressure'].values():
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
                    serial_mutex=mutex,
                    worker_thread=self.pressure_thread,
                    ))

        # Start the pressure thread event loop
        self.pressure_thread.start()

        ################
        # SOURCE SETUP #
        ################
        
        self.sources: list[Source] = []
        self.source_thread = QThread()
        
        if AppConfig.PARAMETER['sources']['safety'] is None:
            AppConfig.PARAMETER['sources']['safety'] = {}
        safety_settings = AppConfig.PARAMETER['sources']['safety']
        for source_config in AppConfig.HARDWARE['devices']['sources'].values():
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
                    serial_mutex=mutex,
                    worker_thread=self.source_thread
                    ))

        # Start the source thread event loop
        self.source_thread.start()

        #################
        # SHUTTER SETUP #
        #################
        
        self.shutters: list[Shutter] = []
        self.shutter_thread = QThread()
        
        for shutter_config in AppConfig.HARDWARE['devices']['shutters'].values():
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
                serial_mutex=serial_mutex,
                worker_thread=self.shutter_thread,
                ) for shutter in shutter_config['connections']])
            
        # Start the shutter thread event loop
        self.shutter_thread.start()

        ###################
        # SUBSTRATE SETUP #
        ###################

        # TODO: Get from config file rather than hardcode
        self.substrate_thread = QThread()

        ser = serial.Serial(
            port=None,
            baudrate=9600,
            timeout=0.1
        )

        serial_mutex = QMutex()

        self.substrate_motor = SubstrateMotor(
            name="Substrate",
            address=1,
            ser=ser,
            serial_mutex=serial_mutex,
            worker_thread=self.substrate_thread,
            gear_ratio=SUBSTRATE_MOTOR_GEAR_RATIO
        )
            
        # Start the shutter thread event loop
        self.substrate_thread.start()

        self.loading_thread = QThread()
        
        ser = serial.Serial(
            port=None,
            baudrate=9600,
            timeout=0.1
        )

        serial_mutex = QMutex()

        self.loading_motor = LoadingMotor(
            name="Loading",
            address=1,
            ser=ser,
            serial_mutex=serial_mutex,
            worker_thread=self.loading_thread,
            gear_ratio=LOADING_MOTOR_GEAR_RATIO
        )
            
        # Start the shutter thread event loop
        self.loading_thread.start()