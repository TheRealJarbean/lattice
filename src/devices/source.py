from pymodbus.client.serial import ModbusSerialClient as ModbusClient
import logging

logger = logging.getLogger(__name__)

addresses = {
    "loop_1_pid_td" : 33474
}

class Source:
    def __init__(self, device_id):
        self.device_id = device_id
        self.setpoint
        self.setpoint = 0.0
        self.ramp_rate = 0.0
        self.safe_ramp_rate = 0.0
        self.safe_rr_from = 0.0
        self.safe_rr_to = 0.0

class SourceManager:
    def __init__(self, port, baudrate=9600):
        self.sources = {}
        self.ser = ModbusClient(port=port, baudrate=baudrate)
        
    def add_source(self, name: str, device_id: int):
        if name in self.sources:
            logger.debug("Name already exists in source list")
            return
        
        if device_id in self.sources.values():
            logger.debug("Device id already exists in source list")
            return
        
        self.sources[name] = device_id
        
    def read_data(self, name, address, count=1):
        id = self.sources[name].id
        self.client.read_holding_registers(address=address, count=count, device_id=id)
        
    def write_data(self, name, address, value):
        id = self.sources[name].id
        self.client.write_register(address=address, device_id=id, value=value)

    def monitor(self):
        for source in self.sources:
            source.
    
    def get_setpoint(self, name):
        res = self.client.read_holding_registers(address=self.modbus_addresses['setpoint'], count=1, device_id=self.id)
        return res.registers[int(1)]
    
    def get_ramp_rate(self, name):
        res = self.client.read_holding_registers(address=self.modbus_addresses['ramp_rate'], count=1, device_id=self.id)
        return res.registers[int(1)]

    def set_setpoint(self, name, setpoint, limit=200):
        if setpoint > 200:
            setpoint = 200
        self.client.write_register(address=self.modbus_addresses['setpoint'], device_id=self.id, value=setpoint)
        self.setpoint = setpoint

    def set_ramp_rate(self, name, ramp_rate):
        self.client.write_register(address=self.modbus_addresses['ramp_rate'], device_id=self.id, value=ramp_rate)
        self.ramp_rate = ramp_rate

    def set_ramp_rate_safety(self, name, safe_ramp_rate, safe_rr_from, safe_rr_to):
        self.safe_ramp_rate = safe_ramp_rate
        self.safe_rr_from = safe_rr_from
        self.safe_rr_to = safe_rr_to