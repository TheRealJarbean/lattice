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
    process_variable_changed = Signal(float)
    working_setpoint_changed = Signal(float)
    setpoint_changed = Signal(float)
    working_setpoint_changed = Signal(float)
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
        self.rate_limit = -1
        self.client = client
        self.serial_mutex = serial_mutex
        self.data_mutex = QMutex()

        # Stability attributes
        self.stability_time = None
        self.is_stable = False
        
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
        self.stability_timer.start(500)

        
    def read_data(self, key, count=1):
        self.data_mutex.lock()
        self.serial_mutex.lock()
        try:
            addresses = self.addresses
            res = self.client.read_holding_registers(address=addresses[key], count=count, device_id=self.id)

            if res.isError():
                logger.warning(f"Modbus response was error when reading {key} from source {self.id}, {self.name}: {res}")
                return None
            
            value = self.client.convert_from_registers(res.registers, self.client.DATATYPE.FLOAT32)

            return value
        
        except Exception as e:
            logger.error(f"Error reading {key} from source {self.id}, {self.name}: {e}")
            return None
        
        finally:
            self.serial_mutex.unlock()
            self.data_mutex.unlock()
        
    def write_data(self, key, value):
        self.data_mutex.lock()
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
            self.data_mutex.unlock()
            self.serial_mutex.unlock()
        
    def start_polling(self):
        self.data_mutex.lock()
        if not self.poll_timer.isActive():
            logger.debug(f"Beginning poll for source {self.name}")
            self.poll_timer.start(500)
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
            self.setpoint = new_setpoint
            self.setpoint_changed.emit(new_setpoint)

        if new_working_setpoint is not None:
            self.working_setpoint_changed.emit(new_working_setpoint)

        if new_rate_limit is not None:
            self.rate_limit_changed.emit(new_rate_limit)

            # For initialization
            self.data_mutex.lock()
            if self.rate_limit == -1:
                self.rate_limit = new_rate_limit
            self.data_mutex.unlock()

        if new_process_variable is None:
            return
        
        self.process_variable_changed.emit(new_process_variable)
        logger.debug(new_process_variable)
        
        self.data_mutex.lock()
        logger.debug(f"{self.safe_rate_limit} {self.safe_rate_limit_from} {self.safe_rate_limit_to}")
        safe_rate, safe_from, safe_to = self.safe_rate_limit, self.safe_rate_limit_from, self.safe_rate_limit_to
        rate_limit = self.rate_limit
        self.data_mutex.unlock()


        if any(x <= 0.0 for x in (safe_rate, safe_from, safe_to)):
            if safe_from < new_process_variable < safe_to:
                self.set_rate_limit(safe_rate)
                return
            
        self.set_rate_limit(rate_limit)
        
            
    def get_name(self) -> str:
        self.data_mutex.lock()
        name = self.name
        self.data_mutex.unlock()
        
        return name
        
    def get_process_variable(self) -> float | None:
        value = self.read_data("process_variable", count=2)
        return value
    
    def get_setpoint(self) -> float:
        return self.read_data("setpoint", count=2)

    def get_working_setpoint(self) -> float:
        return self.read_data("working_setpoint", count=2)
    
    def get_rate_limit(self) -> float:
        return self.read_data("setpoint_rate_limit", count=2)
    
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
        pid_pb = self.read_data("pid_pb", count=2)
        pid_ti = self.read_data("pid_ti", count=2)
        pid_td = self.read_data("pid_td", count=2)
        
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

    def set_setpoint(self, setpoint):
        self.data_mutex.lock()
        logger.debug(f"Setting setpoint to {setpoint} for source id {self.id}, {self.name}")
        self.data_mutex.unlock()
        
        self.write_data("setpoint", setpoint)

        self.data_mutex.lock()
        self.setpoint = setpoint
        self.setpoint_changed.emit(self.setpoint)
        self.data_mutex.unlock()

    def set_rate_limit(self, rate_limit):
        self.data_mutex.lock()
        logger.debug(f"Setting rate_limit to {rate_limit} for source id {self.id}, {self.name}")
        self.data_mutex.unlock()

        self.write_data("setpoint_rate_limit", rate_limit)

        self.data_mutex.lock()
        self.rate_limit = rate_limit
        self.data_mutex.unlock()

    def set_rate_limit_safety(self, safe_rate_limit, safe_rate_limit_from, safe_rate_limit_to):
        self.data_mutex.lock()
        logger.debug(f"""
            Setting multiple values for source id {self.id}, {self.name}
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
            Setting multiple values for source id {self.id}, {self.name}
            - pid_pb: {pid_pb}
            - pid_ti: {pid_ti}
            - pid_td: {pid_td}
            """)
        self.write_data("pid_pb", pid_pb)
        self.write_data("pid_ti", pid_ti)
        self.write_data("pid_td", pid_td)
        self.data_mutex.unlock()
            
    def set_max_setpoint(self, value):
        self.data_mutex.lock()
        self.max_setpoint = value
        self.data_mutex.unlock()

    def set_stability_tolerance(self, value):
        self.data_mutex.lock()
        self.stability_tolerance = value
        self.data_mutex.unlock()
            
    def is_pv_close_to_sp(self):
        # TODO: Ask if rel_tol would be more appropriate
        current_sp = self.get_setpoint()
        current_pv = self.get_process_variable()
        if None in [current_sp, current_pv]:
            logger.error("Could not read sp or pv when comparing sp and pv")
            return
        
        return math.isclose(current_sp, current_pv, abs_tol=self.stability_tolerance)
    
    def check_stability(self):
        if not self.is_pv_close_to_sp():
            self.stability_time = None
            self.is_stable = False
            return
        
        if time.monotonic() - self.stability_time > 5:
            print(f"{self.name} is stable!")
            self.is_stable = True

        if self.stability_time is None:
            self.stability_time = time.monotonic()