from PySide6.QtCore import Signal, QMutex, QMutexLocker, QObject, QTimer
from pymodbus.client.serial import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusException
import logging
import math

logger = logging.getLogger(__name__)

MODBUS_ADDRESSES = {
    "loop_1": {
        "setpoint": 32816,
        "setpoint_rate_limit": 32838,
        "process_variable": 32770,
        "pid_pb": 33470,
        "pid_ti": 33472,
        "pid_td": 33474
    },
    "loop_2": {
        "setpoint": 34864,
        "setpoint_rate_limit": 34886,
        "process_variable": 34818,
        "pid_pb": 35518,
        "pid_ti": 35520,
        "pid_td": 35522
    }
}

# TODO: All methods that use read_data, only emit and set new values if modbus read returns success
class Source(QObject):
    process_variable_changed = Signal(float)
    working_setpoint_changed = Signal(float)
    setpoint_changed = Signal(float)
    # This does not always match the value of "rate_limit"
    # Should also emit when the safe rate limit is applied
    # i.e. it should emit whenever the hardware rate limit changes
    rate_limit_changed = Signal(float)
    safe_rate_limit_changed = Signal(float)
    safe_rate_limit_from_changed = Signal(float)
    safe_rate_limit_to_changed = Signal(float)
    
    def __init__(self, name, device_id, address_set, safety_settings: dict, client: ModbusClient, serial_mutex: QMutex):
        super().__init__()
        
        if address_set not in MODBUS_ADDRESSES:
            raise KeyError("Address set not valid")
        
        # Set instance attributes
        self.name = name
        self.id = device_id
        self.addresses = MODBUS_ADDRESSES[address_set]
        self.working_setpoint = 0.0
        self.setpoint = 0.0
        self.rate_limit = 0.0
        self.client = client
        self.serial_mutex = serial_mutex
        self.data_mutex = QMutex()
        
        if safety_settings:
            logger.debug(f"""
                Found safety settings for source {name}:
                - rate_limit: {safety_settings['rate_limit']}
                - from: {safety_settings['from']}
                - to: {safety_settings['to']}
                """)
            self.safe_rate_limit = safety_settings['rate_limit']
            self.safe_rate_limit_from = safety_settings['from']
            self.safe_rate_limit_to = safety_settings['to']
        else:
            self.safe_rate_limit = 0.0
            self.safe_rate_limit_from = 0.0
            self.safe_rate_limit_to = 0.0
            
        # Create and connect poll timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll)
        
    def read_data(self, key, count=1):
        self.serial_mutex.lock()
        try:
            addresses = self.addresses
            res = self.client.read_holding_registers(address=addresses[key], count=count, device_id=self.id)
            
            if res.isError():
                logger.warning(f"Modbus response was error when reading {key} from source {self.id}, {self.name}: {res}")
                return None
            
            value = self.client.convert_from_registers(res.registers, self.client.DATATYPE.FLOAT32)
            return value
        
        except ModbusException as e:
            logger.error(f"Error reading {key} from source {self.id}, {self.name}: {e}")
            return None
        
        finally:
            self.serial_mutex.unlock()
        
    def write_data(self, key, value):
        self.serial_mutex.lock()
        try:
            addresses = self.addresses
            encoded_value = self.client.convert_to_registers(value, self.client.DATATYPE.FLOAT32)
            res = self.client.write_registers(address=addresses[key], values=encoded_value, device_id=self.id)
            if res.isError():
                logger.warning(f"Modbus response was error when writing {key} to source id {self.id}, {self.name}: {res}")
        
        except ModbusException as e:
            logger.error(f"Error writing {key} to source id {self.id}, {self.name}: {e}")
        
        finally:
            self.serial_mutex.unlock()
        
    def start_polling(self):
        with QMutexLocker(self.data_mutex):
            if not self.poll_timer.isActive():
                self.poll_timer.start(500)
    
    def stop_polling(self):
        with QMutexLocker(self.data_mutex):
            if self.poll_timer.isActive():
                self.poll_timer.stop()
        
    def poll(self):
        with QMutexLocker(self.data_mutex):
            logger.debug(f"Polling source id {self.id}, {self.name}")
            new_process_variable = self.read_data("process_variable", count=2)
            if not new_process_variable:
                return
            
            self.process_variable_changed.emit(self.new_process_variable)
            
            if self.safe_rate_limit_from < new_process_variable < self.safe_rate_limit_to:
                self.rate_limit_changed.emit(self.safe_rate_limit)
                self.set_rate_limit(self.safe_rate_limit)
            
            elif self.rate_limit == self.safe_rate_limit:
                self.rate_limit_changed.emit(self.rate_limit)
                self.set_rate_limit(self.rate_limit)
        
            
    def get_name(self) -> str:
        with QMutexLocker(self.data_mutex):
            return self.name
    
    def get_setpoint(self) -> float:
        with QMutexLocker(self.data_mutex):
            return self.read_data("setpoint", count=2)
    
    def get_rate_limit(self) -> float:
        with QMutexLocker(self.data_mutex):
            return self.read_data("setpoint_rate_limit", count=2)
    
    def get_rate_limit_safety(self) -> tuple[float, float, float]:
        """
        Returns safe_rate_limit, safe_rate_limit_from, and safe_rate_limit_to as tuple
        """
        with QMutexLocker(self.data_mutex):
            return (self.safe_rate_limit, self.safe_rate_limit_from, self.safe_rate_limit_to)
    
    def get_pid(self) -> tuple[float, float, float]:
        """
        Returns pid_pb, pid_ti, and pid_td as tuple
        """
        with QMutexLocker(self.data_mutex):
            pid_pb = self.read_data("pid_pb", count=2)
            pid_ti = self.read_data("pid_ti", count=2)
            pid_td = self.read_data("pid_td", count=2)
            
            # If any failed to read
            if None in (pid_pb, pid_ti, pid_td):
                logger.debug(f"Failed to retrieve a pid value for {self.name}")
                return (0.0, 0.0, 0.0)
            
            return (pid_pb, pid_ti, pid_td)
        
    def get_max_process_variable(self):
        with QMutexLocker(self.data_mutex):
            # TODO: Add real read here
            return 0   

    def set_setpoint(self, setpoint):
        with QMutexLocker(self.data_mutex):
            logger.debug(f"Setting setpoint to {setpoint} for source id {self.id}, {self.name}")
            self.write_data("setpoint", setpoint)
            self.setpoint = setpoint
            self.setpoint_changed.emit(self.setpoint)

    def set_rate_limit(self, rate_limit):
        with QMutexLocker(self.data_mutex):
            logger.debug(f"Setting rate_limit to {rate_limit} for source id {self.id}, {self.name}")
            self.write_data("setpoint_rate_limit", rate_limit)
            self.rate_limit = rate_limit
            self.rate_limit_changed.emit(self.rate_limit)

    def set_rate_limit_safety(self, safe_rate_limit, safe_rate_limit_from, safe_rate_limit_to):
        with QMutexLocker(self.data_mutex):
            logger.debug(f"""
                Setting multiple values for source id {self.id}, {self.name}
                - safe_rate_limit: {safe_rate_limit}
                - safe_rate_limit_from: {safe_rate_limit_from}
                - safe_rate_limit_to: {safe_rate_limit_to}
                """)
            self.safe_rate_limit = safe_rate_limit
            self.safe_rate_limit_from = safe_rate_limit_from
            self.safe_rate_limit_to = safe_rate_limit_to
        
    def set_pid(self, pid_pb, pid_ti, pid_td):
        with QMutexLocker(self.data_mutex):
            logger.debug(f"""
                Setting multiple values for source id {self.id}, {self.name}
                - pid_pb: {pid_pb}
                - pid_ti: {pid_ti}
                - pid_td: {pid_td}
                """)
            self.write_data("pid_pb", pid_pb)
            self.write_data("pid_ti", pid_ti)
            self.write_data("pid_td", pid_td)
            
    def set_max_process_variable(self, value):
        with QMutexLocker(self.data_mutex):
            # TODO: Add actual write here
            pass
            
    def is_pv_close_to_sp(self):
        with QMutexLocker(self.data_mutex):
            # TODO: Ask if rel_tol would be more appropriate
            return math.isclose(self.setpoint, self.process_variable, abs_tol=0.5)