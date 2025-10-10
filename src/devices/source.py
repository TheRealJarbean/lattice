from PySide6.QtCore import Signal, QMutex, QObject
from pymodbus.client.serial import ModbusSerialClient as ModbusClient
import logging

logger = logging.getLogger(__name__)

MODBUS_ADDRESSES = {
    "loop_1": {
        "setpoint": 32772,
        "setpoint_rate_limit": 32838,
        "process_variable": 32770,
        "pid_pb": 33470,
        "pid_ti": 33472,
        "pid_td": 33474
    },
    "loop_2": {
        "setpoint": 34820,
        "setpoint_rate_limit": 34886,
        "process_variable": 31818,
        "pid_pb": 35518,
        "pid_ti": 35520,
        "pid_td": 35522
    }
}

class Source(QObject):
    process_variable_changed = Signal(float)
    setpoint_changed = Signal(float)
    ramp_rate_changed = Signal(float)
    safe_ramp_rate_changed = Signal(float)
    safe_rr_from_changed = Signal(float)
    safe_rr_to_changed = Signal(float)
    pid_pb_changed = Signal(float)
    pid_ti_changed = Signal(float)
    pid_td_changed = Signal(float)
    
    def __init__(self, name, device_id, address_set, client: ModbusClient, mutex: QMutex):
        super().__init__()
        
        if address_set not in MODBUS_ADDRESSES:
            raise KeyError("Address set not valid")
        
        self.name = name
        self.id = device_id
        self.addresses = MODBUS_ADDRESSES[address_set]
        self.process_variable = 0.0
        self.setpoint = 0.0
        self.rate_limit = 0.0
        self.safe_rate_limit = 0.0
        self.safe_rate_limit_from = 0.0
        self.safe_rate_limit_to = 0.0
        self.pid_pb = 0.0
        self.pid_ti = 0.0
        self.pid_td = 0.0
        self.client = client
        self.mutex = mutex
        
    def read_data(self, key, count=1):
        self.mutex.lock()
        logger.debug(f"Reading {key} from source {self.name}")
        addresses = self.addresses
        res = self.client.read_holding_registers(address=addresses[key], count=count, device_id=self.id)
        self.mutex.unlock()
        return res.registers[int(1)]
        
    def write_data(self, key, value):
        self.mutex.lock()
        logger.debug(f"Writing {value} to {key} of source {self.name}")
        addresses = self.addresses
        self.client.write_register(address=addresses[key], device_id=self.id, value=value)
        self.mutex.unlock()
    
    def get_setpoint(self):
        return self.read_data("setpoint")
    
    def get_rate_limit(self):
        return self.read_data("setpoint_rate_limit")

    def set_setpoint(self, setpoint):
        self.write_data("setpoint", setpoint)
        self.setpoint = setpoint

    def set_rate_limit(self, ramp_rate):
        self.write_data("setpoint_rate_limit", ramp_rate)
        self.rate_limit = ramp_rate

    def set_rate_limit_safety(self, safe_ramp_rate, safe_rr_from, safe_rr_to):
        self.safe_rate_limit = safe_ramp_rate
        self.safe_rate_limit_from = safe_rr_from
        self.safe_rate_limit_to = safe_rr_to