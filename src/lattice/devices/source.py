from PySide6.QtCore import Signal, QMutex, QMutexLocker, QObject, QTimer
from pymodbus.client.serial import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusException
import logging
import math
import time

logger = logging.getLogger(__name__)

MODBUS_ADDRESSES = {
    "2604_loop_1": {
        "setpoint": 32816,
        "working_setpoint": 32778,
        "setpoint_rate_limit": 32838,
        "process_variable": 32770,
        "pid_pb": 33470,
        "pid_ti": 33472,
        "pid_td": 33474
    },
    "2604_loop_2": {
        "setpoint": 34864,
        "working_setpoint": 34826,
        "setpoint_rate_limit": 34886,
        "process_variable": 34818,
        "pid_pb": 35518,
        "pid_ti": 35520,
        "pid_td": 35522
    },
    "2404_loop_1": {
        "setpoint": 32816,
        "working_setpoint": 32778,
        "setpoint_rate_limit": 32838,
        "process_variable": 32770,
        "pid_pb": 32780,
        "pid_ti": 32784,
        "pid_td": 32786
    }
}

# TODO: All methods that use read_data, only emit and set new values if modbus read returns success
class Source(QObject):
    process_variable_changed = Signal(float, QObject) # Value, self ref
    working_setpoint_changed = Signal(float, QObject) # Value, self ref
    setpoint_changed = Signal(float, QObject) # Value, self ref
    working_setpoint_changed = Signal(float, QObject) # Value, self ref
    safe_rate_limit_changed = Signal(float, QObject) # Value, self ref
    safe_rate_limit_from_changed = Signal(float, QObject) # Value, self ref
    safe_rate_limit_to_changed = Signal(float, QObject) # Value, self ref
    is_stable_changed = Signal(bool, QObject) # Value, self ref
    new_modbus_data = Signal(str, str) # Name, string representation of data
    
    # This does not always match the value of "rate_limit"
    # Should also emit when the safe rate limit is applied
    # i.e. it should emit whenever the hardware rate limit changes
    rate_limit_changed = Signal(float, QObject) # Value, self ref
    
    def __init__(self, name, device_id, address_set, safety_settings: dict, client: ModbusClient, serial_mutex: QMutex):
        super().__init__()
        
        if address_set not in MODBUS_ADDRESSES:
            raise KeyError("Address set not valid")
        
        # Set instance attributes
        self.name = name
        self.device_id = device_id
        self.addresses = MODBUS_ADDRESSES[address_set]
        self.working_setpoint = 0.0
        self.rate_limit = 0.1
        self.client = client
        self.serial_mutex = serial_mutex
        self.data_mutex = QMutex()

        # Stability attributes
        self.stability_time = time.monotonic()
        self.is_stable = False
        self.is_pv_close_to_sp = False
        
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
            self.max_setpoint = safety_settings['max_setpoint']
            self.stability_tolerance = safety_settings['stability_tolerance']
        else:
            self.safe_rate_limit = 0.0
            self.safe_rate_limit_from = 0.0
            self.safe_rate_limit_to = 0.0
            self.max_setpoint = 2000.0
            self.stability_tolerance = 1.0
            
        # Create and connect poll timer
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll)

        # Create and connect the stability timer
        self.stability_timer = QTimer()
        self.stability_timer.timeout.connect(self.check_stability)
        self.stability_timer.start(1000)

        
    def read_data_by_address(self, address: int, count=2):
        self.data_mutex.lock()
        self.serial_mutex.lock()
        try:
            res = self.client.read_holding_registers(address=address, count=count, device_id=self.device_id)

            if res.isError():
                logger.warning(f"Modbus response was error when reading address {address} from source {self.device_id}, {self.name}: {res}")
                return None
            
            value = self.client.convert_from_registers(res.registers, self.client.DATATYPE.FLOAT32)
            self.new_modbus_data.emit(self.name, f"Read: {address} | Result: {value}")

            return value
        
        except Exception as e:
            logger.error(f"Error reading address {address} from source {self.device_id}, {self.name}: {e}")
            return None
        
        finally:
            self.serial_mutex.unlock()
            self.data_mutex.unlock()
            
    def read_data_by_key(self, key: str, count=2):
        self.data_mutex.lock()
        address = self.addresses[key]
        self.data_mutex.unlock()
        
        return self.read_data_by_address(address, count)
        
    def write_data_by_address(self, address: int, value: float):
        self.data_mutex.lock()
        self.serial_mutex.lock()
        try:
            encoded_value = self.client.convert_to_registers(value, self.client.DATATYPE.FLOAT32)
            res = self.client.write_registers(address=address, values=encoded_value, device_id=self.device_id)
            if res.isError():
                logger.warning(f"Modbus response was error when writing address {address} to source id {self.device_id}, {self.name}: {res}")
                
            self.new_modbus_data.emit(self.name, f"Write: {address} | Value: {value}")
        
        except ModbusException as e:
            logger.error(f"Error writing address {address} to source id {self.device_id}, {self.name}: {e}")
        
        finally:
            self.data_mutex.unlock()
            self.serial_mutex.unlock()
            
    def write_data_by_key(self, key: str, value: float):
        self.data_mutex.lock()
        address = self.addresses[key]
        self.data_mutex.unlock()
        
        return self.write_data_by_address(address, value)
    
    def start_polling(self, interval_ms: int):
        self.data_mutex.lock()
        if not self.poll_timer.isActive():
            logger.debug(f"Beginning poll for source {self.name}")
            self.poll_timer.start(interval_ms)
        self.data_mutex.unlock()
    
    def stop_polling(self):
        self.data_mutex.lock()
        if self.poll_timer.isActive():
            self.poll_timer.stop()
        self.data_mutex.unlock()
        
    def poll(self):
        new_process_variable = self.get_process_variable()
        new_setpoint = self.get_setpoint()
        new_working_setpoint = self.get_working_setpoint()
        new_rate_limit = self.get_rate_limit()

        if new_setpoint is not None:
            self.setpoint_changed.emit(new_setpoint, self)

        if new_rate_limit is not None:
            self.rate_limit_changed.emit(new_rate_limit, self)

            # For initialization
            self.data_mutex.lock()
            if self.rate_limit == -1:
                self.rate_limit = new_rate_limit
            self.data_mutex.unlock()

        if new_working_setpoint is not None:
            self.working_setpoint_changed.emit(new_working_setpoint, self)

            self.data_mutex.lock()
            safe_rate, safe_from, safe_to = self.safe_rate_limit, self.safe_rate_limit_from, self.safe_rate_limit_to
            rate_limit = self.rate_limit
            self.data_mutex.unlock()

            if not any(x <= 0.0 for x in (safe_rate, safe_from, safe_to)):
                if safe_from < new_working_setpoint < safe_to:
                    self._set_rate_limit(safe_rate)

        if new_process_variable is not None:
            self.process_variable_changed.emit(new_process_variable, self)

            if new_setpoint is not None:
                self.data_mutex.lock()
                tolerance = self.stability_tolerance
                self.data_mutex.unlock()
                
                self.is_pv_close_to_sp = math.isclose(new_setpoint, new_process_variable, abs_tol=tolerance)
            
        self._set_rate_limit(rate_limit)
        
    def get_name(self) -> str:
        self.data_mutex.lock()
        name = self.name
        self.data_mutex.unlock()
        
        return name
        
    def get_process_variable(self) -> float | None:
        value = self.read_data_by_key("process_variable", count=2)
        return value
    
    def get_setpoint(self) -> float:
        return self.read_data_by_key("setpoint", count=2)

    def get_working_setpoint(self) -> float:
        return self.read_data_by_key("working_setpoint", count=2)
    
    def get_rate_limit(self) -> float:
        return self.read_data_by_key("setpoint_rate_limit", count=2)
    
    def get_rate_limit_safety(self) -> tuple[float, float, float]:
        """
        Returns safe_rate_limit, safe_rate_limit_from, and safe_rate_limit_to as tuple
        """
        self.data_mutex.lock()
        safe_rate, safe_from, safe_to = self.safe_rate_limit, self.safe_rate_limit_from, self.safe_rate_limit_to
        self.data_mutex.unlock()
        
        return (safe_rate, safe_from, safe_to)
    
    def get_pid(self) -> tuple[float, float, float]:
        """
        Returns pid_pb, pid_ti, and pid_td as tuple
        """
        pid_pb = self.read_data_by_key("pid_pb", count=2)
        pid_ti = self.read_data_by_key("pid_ti", count=2)
        pid_td = self.read_data_by_key("pid_td", count=2)
        
        # If any failed to read
        if None in (pid_pb, pid_ti, pid_td):
            self.data_mutex.lock()
            logger.debug(f"Failed to retrieve a pid value for {self.name}")
            self.data_mutex.unlock()
            
            return (0.0, 0.0, 0.0)
        
        return (pid_pb, pid_ti, pid_td)
        
    def get_max_setpoint(self):
        self.data_mutex.lock()
        max_setpoint = self.max_setpoint
        self.data_mutex.unlock()
        return max_setpoint
    
    def get_stability_tolerance(self):
        self.data_mutex.lock()
        tolerance = self.stability_tolerance
        self.data_mutex.unlock()
        return tolerance
    
    def get_is_stable(self):
        self.data_mutex.lock()
        is_stable = self.is_stable
        self.data_mutex.unlock()
        
        return is_stable

    def set_setpoint(self, setpoint):
        self.write_data_by_key("setpoint", setpoint)
    
    def set_rate_limit(self, rate_limit):
        self.data_mutex.lock()
        self.rate_limit = rate_limit
        self.data_mutex.unlock()

    def _set_rate_limit(self, rate_limit):
        self.write_data_by_key("setpoint_rate_limit", rate_limit)

    def set_rate_limit_safety(self, safe_rate_limit, safe_rate_limit_from, safe_rate_limit_to):
        self.data_mutex.lock()
        logger.debug(f"""
            Setting multiple values for source id {self.device_id}, {self.name}
            - safe_rate_limit: {safe_rate_limit}
            - safe_rate_limit_from: {safe_rate_limit_from}
            - safe_rate_limit_to: {safe_rate_limit_to}
            """)
        
        self.safe_rate_limit = safe_rate_limit
        self.safe_rate_limit_from = safe_rate_limit_from
        self.safe_rate_limit_to = safe_rate_limit_to
        self.data_mutex.unlock()
        
    def set_pid(self, pid_pb, pid_ti, pid_td):
        self.data_mutex.lock()
        logger.debug(f"""
            Setting multiple values for source id {self.device_id}, {self.name}
            - pid_pb: {pid_pb}
            - pid_ti: {pid_ti}
            - pid_td: {pid_td}
            """)
        self.write_data_by_key("pid_pb", pid_pb)
        self.write_data_by_key("pid_ti", pid_ti)
        self.write_data_by_key("pid_td", pid_td)
        self.data_mutex.unlock()
            
    def set_max_setpoint(self, value):
        self.data_mutex.lock()
        self.max_setpoint = value
        self.data_mutex.unlock()

    def set_stability_tolerance(self, value):
        self.data_mutex.lock()
        self.stability_tolerance = value
        self.data_mutex.unlock()
    
    def check_stability(self):
        self.data_mutex.lock()
        is_stable = self.is_stable
        self.data_mutex.unlock()

        if not self.is_pv_close_to_sp:
            self.data_mutex.lock()
            self.stability_time = time.monotonic()
            self.is_stable = False
            self.data_mutex.unlock()
            
            self.is_stable_changed.emit(False, self)
            return
        
        if is_stable:
            return
        
        self.data_mutex.lock()
        stability_time = self.stability_time
        self.data_mutex.unlock()
        
        if time.monotonic() - stability_time > 5:
            self.data_mutex.lock()
            self.is_stable = True
            self.data_mutex.unlock()
            
            self.is_stable_changed.emit(True, self)