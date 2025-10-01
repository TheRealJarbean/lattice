from pymodbus.client.serial import ModbusSerialClient as ModbusClient
import logging

logger = logging.getLogger(__name__)

addresses = {
    "loop_1_pid_td" : 33474
}

class Source:
    # TODO: Figure out addresses of these values (using itools?)
    modbus_addresses = {
        "setpoint" : 1,
        "ramp_rate" : 2
    }
    
    def __init__(self, id, client: ModbusClient):
        self.client = client
        self.id = id
        self.setpoint = 0.0
        self.ramp_rate = 0.0
        self.safe_ramp_rate = 0.0
        self.safe_rr_from = 0.0
        self.safe_rr_to = 0.0

    def monitor(self):
        pass
    
    def get_setpoint(self):
        res = self.client.read_holding_registers(address=self.modbus_addresses['setpoint'], count=1, device_id=self.id)
        return res.registers[int(1)]
    
    def get_ramp_rate(self):
        res = self.client.read_holding_registers(address=self.modbus_addresses['ramp_rate'], count=1, device_id=self.id)
        return res.registers[int(1)]

    def set_setpoint(self, setpoint, limit=200):
        if setpoint > 200:
            setpoint = 200
        self.client.write_register(address=self.modbus_addresses['setpoint'], device_id=self.id, value=setpoint)
        self.setpoint = setpoint

    def set_ramp_rate(self, ramp_rate):
        self.client.write_register(address=self.modbus_addresses['ramp_rate'], device_id=self.id, value=ramp_rate)
        self.ramp_rate = ramp_rate

    def set_ramp_rate_safety(self, safe_ramp_rate, safe_rr_from, safe_rr_to):
        self.safe_ramp_rate = safe_ramp_rate
        self.safe_rr_from = safe_rr_from
        self.safe_rr_to = safe_rr_to