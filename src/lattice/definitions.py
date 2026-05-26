from pathlib import Path
from lattice.utils.email_alerter import EmailAlerter

ROOT_DIR = Path(__file__).parent
ALERTER = EmailAlerter()

SOURCE_MODBUS_ADDRESSES = {
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