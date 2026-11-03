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
        baudrates = AppConfig.HARDWARE['baudrates']

        ##################
        # PRESSURE SETUP #
        ##################
        
        self.pressure_gauges: list[PressureGauge] = []
        self.pressure_thread = QThread()

        # Populate pressure gauge list from config file
        used_ports_map = {}
        for gauge_config in AppConfig.HARDWARE['devices']['pressure_gauges']:
            port = gauge_config['port']
            if gauge_config['port'] in used_ports_map.keys():
                ser = used_ports_map[port]
            else:
                ser = serial.Serial(
                    port=port, 
                    baudrate=baudrates[port],
                    timeout=0.1
                    )
                used_ports_map[port] = ser
            
            mutex = QMutex()
            
            self.pressure_gauges.append(PressureGauge(
                name=gauge_config['name'], 
                address=gauge_config['address'],
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
        port_client_map = {}
        for source_config in AppConfig.HARDWARE['devices']['sources']:
            port = source_config['port']
            if port in port_client_map.keys():
                client = port_client_map[port]
            else:
                client = ModbusClient(
                    port=port, 
                    baudrate=baudrates[port],
                    timeout=0.1
                    )
                port_client_map[port] = client
            mutex = QMutex()
            
            self.sources.append(Source(
                name=source_config['name'],
                device_id=source_config['device_id'],
                address_set=source_config['address_set'],
                safety_settings=safety_settings.get(source_config['name'], {}),
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

        used_ports_map = {}
        for shutter_config in AppConfig.HARDWARE['devices']['shutters']:
            port = shutter_config['port']
            if port in used_ports_map.keys():
                ser = used_ports_map[port]
            else:
                ser = serial.Serial(
                    port=port, 
                    baudrate=baudrates[port],
                    timeout=0.1
                    )
                used_ports_map[port] = ser
            
            serial_mutex = QMutex()
            
            self.shutters.append(Shutter(
                name=shutter_config['name'], 
                address=shutter_config['address'], 
                ser=ser, 
                serial_mutex=serial_mutex,
                worker_thread=self.shutter_thread,
                ))
            
        # Start the shutter thread event loop
        self.shutter_thread.start()

        ###################
        # SUBSTRATE SETUP #
        ###################

        substrate_config = AppConfig.HARDWARE['devices']['substrate_motor']
        self.substrate_thread = QThread()

        port = substrate_config['port']
        ser = serial.Serial(
            port=port,
            baudrate=baudrates[port],
            timeout=0.1
        )

        serial_mutex = QMutex()

        self.substrate_motor = SubstrateMotor(
            name="Substrate",
            address=substrate_config['address'],
            ser=ser,
            serial_mutex=serial_mutex,
            worker_thread=self.substrate_thread,
            gear_ratio=SUBSTRATE_MOTOR_GEAR_RATIO
        )
            
        # Start the shutter thread event loop
        self.substrate_thread.start()

        loading_config = AppConfig.HARDWARE['devices']['loading_motor']
        self.loading_thread = QThread()

        port = loading_config['port']
        ser = serial.Serial(
            port=port,
            baudrate=baudrates[port],
            timeout=0.1
        )

        serial_mutex = QMutex()

        self.loading_motor = LoadingMotor(
            name="Loading",
            address=loading_config['address'],
            ser=ser,
            serial_mutex=serial_mutex,
            worker_thread=self.loading_thread,
            gear_ratio=LOADING_MOTOR_GEAR_RATIO
        )
            
        # Start the shutter thread event loop
        self.loading_thread.start()