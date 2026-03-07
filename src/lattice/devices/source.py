from PySide6.QtCore import Signal, QMutex, QThread, QObject, QTimer, Slot
from pymodbus.client.serial import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusException
import logging
import math
import time

# Local imports
from lattice.definitions import SOURCE_MODBUS_ADDRESSES

logger = logging.getLogger(__name__)

class Source(QObject):
    """
    safety_settings = (rate_limit, from, to)
    """

    # Internal Signals
    _start_polling = Signal(int) # poll interval in ms
    _stop_polling = Signal()
    _read_data_by_address = Signal(int, int) # Address, register count
    _write_data_by_address = Signal(int, float) # Address, value
    _read_pid = Signal()
    _write_pid = Signal(float, float, float) # PB, TI, TD
    _set_max_setpoint = Signal(float)
    _set_stability_tolerance = Signal(float)
    _write_setpoint = Signal(float)
    _update_desired_rate_limit = Signal(float)
    _set_rate_limit_safety = Signal(float, float, float) # rate limit, from, to

    # External Signals
    process_variable_changed = Signal(float) # Process variable
    rate_limit_changed = Signal(float) # Rate limit
    setpoint_changed = Signal(float) # Setpoint
    working_setpoint_changed = Signal(float) # Working setpoint
    new_modbus_data = Signal(str) # Message
    is_pv_close_to_sp_changed = Signal(bool)
    is_stable_changed = Signal(bool)

    def __init__(self, 
                 name, 
                 device_id, 
                 address_set, 
                 safety_settings: dict | None, 
                 client: ModbusClient, 
                 serial_mutex: QMutex, 
                 worker_thread: QThread):
        
        super().__init__()

        self.worker = SourceWorker(
            name, 
            device_id, 
            address_set, 
            safety_settings, 
            client, 
            serial_mutex
            )
        self.worker.moveToThread(worker_thread)

        self.name = name

        # Live data monitoring attributes
        self.process_variable = 0.0
        self.rate_limit = 0.0
        self.setpoint = 0.0
        self.working_setpoint = 0.0
        self.is_pv_close_to_sp = False
        self.is_stable = False

        # Last read PID values
        self.pid_pb = 0.0
        self.pid_ti = 0.0
        self.pid_td = 0.0

        # Connect worker signals to data monitoring updaters
        self.worker.setpoint_changed.connect(self._update_setpoint)
        self.worker.rate_limit_changed.connect(self._update_rate_limit)
        self.worker.working_setpoint_changed.connect(self._update_working_setpoint)
        self.worker.process_variable_changed.connect(self._update_process_variable)
        self.worker.is_pv_close_to_sp_changed.connect(self._update_is_pv_close_to_sp)
        self.worker.is_stable_changed.connect(self._update_is_stable)
        self.worker.pid_changed.connect(self._update_pid)
        self.worker.new_modbus_data.connect(self.on_new_modbus_data)

        # Connect internal signals
        self._read_data_by_address.connect(self.worker.read_data_by_address)
        self._write_data_by_address.connect(self.worker.write_data_by_address)
        self._start_polling.connect(self.worker.start_polling)
        self._stop_polling.connect(self.worker.stop_polling)
        self._read_pid.connect(self.worker.read_pid)
        self._write_pid.connect(self.worker.write_pid)
        self._set_max_setpoint.connect(self.worker.set_max_setpoint)
        self._set_stability_tolerance.connect(self.worker.set_stability_tolerance)
        self._write_setpoint.connect(self.worker.write_setpoint)
        self._update_desired_rate_limit.connect(self.worker.set_desired_rate_limit)
        self._set_rate_limit_safety.connect(self.worker.set_rate_limit_safety)

        # Stability attributes
        self.stability_time = time.monotonic()
        self.is_stable = False
        self.is_pv_close_to_sp = False

        # Grab current PID values
        self._read_pid.emit()

    # MONITORING SLOTS #
    @Slot(float)
    def _update_setpoint(self, setpoint: float):
        if self.setpoint != setpoint:
            self.setpoint = setpoint
            self.setpoint_changed.emit(self.setpoint)

    @Slot(float)
    def _update_rate_limit(self, rate_limit: float):
        if self.rate_limit != rate_limit:
            self.rate_limit = rate_limit
            self.rate_limit_changed.emit(self.rate_limit)
    
    @Slot(float)
    def _update_working_setpoint(self, working_setpoint: float):
        if self.working_setpoint != working_setpoint:
            self.working_setpoint = working_setpoint
            self.working_setpoint_changed.emit(self.working_setpoint)

    @Slot(float)
    def _update_process_variable(self, process_variable: float):
        if self.process_variable != process_variable:
            self.process_variable = process_variable
            self.process_variable_changed.emit(self.process_variable)

    @Slot(float, float, float)
    def _update_pid(self, pid_pb, pid_ti, pid_td):
        if (self.pid_pb, self.pid_ti, self.pid_td) != (pid_pb, pid_ti, pid_td):
            self.pid_pb, self.pid_ti, self.pid_td = pid_pb, pid_ti, pid_td
    
    @Slot(bool)
    def _update_is_pv_close_to_sp(self, is_pv_close_to_sp):
        self.is_pv_close_to_sp = is_pv_close_to_sp
        self.is_pv_close_to_sp_changed.emit(self.is_pv_close_to_sp)

    @Slot(bool)
    def _update_is_stable(self, is_stable):
        self.is_stable = is_stable
        self.is_stable_changed.emit(self.is_stable)

    @Slot(str)
    def on_new_modbus_data(self, message: str):
        self.new_modbus_data.emit(message)
    # MONITORING SLOTS END #

    # READ AND WRITE DATA #
    def read_data_by_address(self, address: int, count=2):
        self._read_data_by_address.emit(address, count)

    def write_data_by_address(self, address: int, value: float):
        self._write_data_by_address.emit(address, value)
    # READ AND WRITE DATA END #

    # POLLING #
    def start_polling(self, interval_ms: int):
        self._start_polling.emit(interval_ms)

    def stop_polling(self):
        self._stop_polling.emit()
    # POLLING END #

    # TODO: Don't use getters? Direct access should be fine, lots of UI code
    # using getters because of old architecture though
    def get_name(self):
        return self.name

    def get_process_variable(self):
        return self.process_variable
    
    def get_rate_limit(self):
        return self.rate_limit
    
    def get_setpoint(self):
        return self.setpoint
    
    def get_working_setpoint(self):
        return self.working_setpoint
    
    def get_is_stable(self):
        return self.is_stable
    
    def get_is_pv_close_to_sp(self):
        return self.is_pv_close_to_sp
    
    def set_setpoint(self, setpoint: float):
        self._write_setpoint.emit(setpoint)

    def set_rate_limit(self, rate_limit: float):
        self._update_desired_rate_limit.emit(rate_limit)

    def set_rate_limit_safety(self, safe_rate_limit: float, safe_rate_limit_from: float, safe_rate_limit_to: float):
        self._set_rate_limit_safety.emit(safe_rate_limit, safe_rate_limit_from, safe_rate_limit_to)

    def set_pid(self, pid_pb: float, pid_ti: float, pid_td: float):
        self._write_pid.emit(pid_pb, pid_ti, pid_td)

    def set_max_setpoint(self, max_setpoint: float):
        self._set_max_setpoint.emit(max_setpoint)

    def set_stability_tolerance(self, tolerance: float):
        self._set_stability_tolerance.emit(tolerance)

class SourceWorker(QObject):
    process_variable_changed = Signal(float)
    setpoint_changed = Signal(float)
    working_setpoint_changed = Signal(float)
    safety_settings_changed = Signal(float, float, float, float, float) # rate limit, from, to, max setpoint, stability tolerance
    pid_changed = Signal(float, float, float) # PB, TI, TD
    is_stable_changed = Signal(bool)
    is_pv_close_to_sp_changed = Signal(bool)
    new_modbus_data = Signal(str) # Modbus message data 

    # This does not always match the value of "desired_rate_limit"
    # Should also emit when the safe rate limit is applied
    # i.e. it should emit whenever the hardware rate limit changes
    rate_limit_changed = Signal(float) # Rate limit

    def __init__(self,
                 name, 
                 device_id, 
                 address_set, 
                 safety_settings: dict | None, 
                 client: ModbusClient, 
                 serial_mutex: QMutex):
        
        super().__init__()

        if address_set not in SOURCE_MODBUS_ADDRESSES:
            raise KeyError("Address set not valid")
        
        self.name = name
        self.device_id = device_id
        self.addresses = SOURCE_MODBUS_ADDRESSES[address_set]
        self.client = client
        self.serial_mutex = serial_mutex
        self.desired_rate_limit = 0.1
        self.is_pv_close_to_sp = False
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
        self._polling = False
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll)

        # Create and connect the stability timer
        self.stability_time = time.monotonic()
        self.stability_check_timer = QTimer(self)
        self.stability_check_timer.timeout.connect(self._check_stability)
        self.stability_check_timer.start(1000)

    @Slot(int, int)
    def read_data_by_address(self, address: int, count=2):
        self.serial_mutex.lock()
        try:
            res = self.client.read_holding_registers(address=address, count=count, device_id=self.device_id)

            if res.isError():
                logger.warning(f"Modbus response was error when reading address {address} from source {self.device_id}, {self.name}: {res}")
                return None
            
            value = self.client.convert_from_registers(res.registers, self.client.DATATYPE.FLOAT32)
            self.new_modbus_data.emit(f"Read: {address} | Result: {value}")

            return value
        
        except Exception as e:
            logger.error(f"Error reading address {address} from source {self.device_id}, {self.name}: {e}")
            return None
        
        finally:
            self.serial_mutex.unlock()

    @Slot(int, float)
    def write_data_by_address(self, address: int, value: float):
        self.serial_mutex.lock()
        try:
            encoded_value = self.client.convert_to_registers(value, self.client.DATATYPE.FLOAT32)
            res = self.client.write_registers(address=address, values=encoded_value, device_id=self.device_id)
            if res.isError():
                logger.warning(f"Modbus response was error when writing address {address} to source id {self.device_id}, {self.name}: {res}")
                
            self.new_modbus_data.emit(f"Write: {address} | Value: {value}")
        
        except ModbusException as e:
            logger.error(f"Error writing address {address} to source id {self.device_id}, {self.name}: {e}")
        
        finally:
            self.serial_mutex.unlock()

    def _read_data_by_key(self, key: str, count=2):
        address = self.addresses[key]
        return self.read_data_by_address(address, count)

    def _write_data_by_key(self, key: str, value: float):
        address = self.addresses[key]
        return self.write_data_by_address(address, value)
    
    @Slot(int)
    def start_polling(self, interval_ms: int):
        if not self.poll_timer.isActive():
            logger.debug(f"Beginning poll for source {self.name}")
            self.poll_timer.start(interval_ms)
    
    @Slot()
    def stop_polling(self):
        if self.poll_timer.isActive():
            self.poll_timer.stop()

    def _poll(self):
        # Safeguard to ensure if modbus hangs
        # timer does not keep stacking poll calls
        if self._polling:
            return
        self._polling = True
        
        try:
            new_process_variable = self._read_process_variable()
            new_setpoint = self._read_setpoint()
            new_working_setpoint = self._read_working_setpoint()
            new_rate_limit = self._read_rate_limit()

            if new_setpoint is not None:
                self.setpoint_changed.emit(new_setpoint)

            if new_rate_limit is not None:
                self.rate_limit_changed.emit(new_rate_limit)

            if new_process_variable is not None:
                self.process_variable_changed.emit(new_process_variable)

                if new_setpoint is not None:
                    self.is_pv_close_to_sp = math.isclose(new_setpoint, new_process_variable, abs_tol=self.stability_tolerance)
                    self.is_pv_close_to_sp_changed.emit(self.is_pv_close_to_sp)

            if new_working_setpoint is not None:
                self.working_setpoint_changed.emit(new_working_setpoint)

                # Check if setpoint is within safety range and apply safe rate limit,
                # skip if current rate limit was not read
                if new_rate_limit is not None:
                    safe_rate, safe_from, safe_to = self.safe_rate_limit, self.safe_rate_limit_from, self.safe_rate_limit_to
                    if (safe_rate > 0 and safe_from > 0 and safe_to > 0
                        and safe_from < new_working_setpoint < safe_to):
                        target = safe_rate
                    else:
                        target = self.desired_rate_limit
                    
                    if new_rate_limit != target:
                        self.write_rate_limit(target)

        # Ensure polling guard gets reset no matter what
        finally:
            self._polling = False

    def _read_process_variable(self) -> float | None:
        return self._read_data_by_key("process_variable", count=2)
    
    def _read_setpoint(self) -> float:
        return self._read_data_by_key("setpoint", count=2)

    def _read_working_setpoint(self) -> float:
        return self._read_data_by_key("working_setpoint", count=2)
    
    def _read_rate_limit(self) -> float:
        return self._read_data_by_key("setpoint_rate_limit", count=2)
    
    def _write_rate_limit(self, rate_limit):
        self._write_data_by_key("setpoint_rate_limit", rate_limit)
    
    @Slot()
    def read_pid(self) -> tuple[float, float, float] | None:
        """
        Returns pid_pb, pid_ti, and pid_td as tuple
        """
        pid_pb = self._read_data_by_key("pid_pb", count=2)
        pid_ti = self._read_data_by_key("pid_ti", count=2)
        pid_td = self._read_data_by_key("pid_td", count=2)
        
        # If any failed to read
        if None in (pid_pb, pid_ti, pid_td):
            logger.debug(f"Failed to retrieve a pid value for {self.name}")
            return None
        
        self.pid_changed.emit(pid_pb, pid_ti, pid_td)
    
    @Slot(float, float, float)
    def write_pid(self, pid_pb, pid_ti, pid_td):
        logger.debug(f"""
            Setting multiple values for source id {self.device_id}, {self.name}
            - pid_pb: {pid_pb}
            - pid_ti: {pid_ti}
            - pid_td: {pid_td}
            """)
        self._write_data_by_key("pid_pb", pid_pb)
        self._write_data_by_key("pid_ti", pid_ti)
        self._write_data_by_key("pid_td", pid_td)

    @Slot(float, float, float)
    def set_rate_limit_safety(self, rate_limit: float, rate_limit_from: float, rate_limit_to: float):
        self.safe_rate_limit = rate_limit
        self.safe_rate_limit_from = rate_limit_from
        self.safe_rate_limit_to = rate_limit_to
        self.safety_settings_changed.emit(
            self.safe_rate_limit,
            self.safe_rate_limit_from,
            self.safe_rate_limit_to,
            self.max_setpoint,
            self.stability_tolerance
        )

    @Slot(float)
    def set_max_setpoint(self, max_setpoint: float):
        self.max_setpoint = max_setpoint
        self.safety_settings_changed.emit(
            self.safe_rate_limit,
            self.safe_rate_limit_from,
            self.safe_rate_limit_to,
            self.max_setpoint,
            self.stability_tolerance
        )

    @Slot(float)
    def set_stability_tolerance(self, tolerance: float):
        self.stability_tolerance = tolerance
        self.safety_settings_changed.emit(
            self.safe_rate_limit,
            self.safe_rate_limit_from,
            self.safe_rate_limit_to,
            self.max_setpoint,
            self.stability_tolerance
        )

    @Slot(float)
    def write_setpoint(self, setpoint: float):
        self._write_data_by_key('setpoint', setpoint)

    @Slot(float)
    def set_desired_rate_limit(self, rate_limit: float):
        self.desired_rate_limit = rate_limit

    def _check_stability(self):
        if not self.is_pv_close_to_sp:
            self.stability_time = time.monotonic()
            self.is_stable = False
            self.is_stable_changed.emit(False)
            return
        
        if self.is_stable:
            return

        if time.monotonic() - self.stability_time > 5:
            self.is_stable = True
            self.is_stable_changed.emit(True)