from core.serial_worker import SerialWorker

class Source:
    def __init__(self, address):
        self.address = address
        self.setpoint = 0
        self.ramp_rate = 0.0
        self.safe_ramp_rate = 0.0
        self.safe_rr_from = 0
        self.safe_rr_to = 0

    def monitor(self):
        pass

    def set_ramp_rate(self, ramp_rate):
        self.ramp_rate = ramp_rate

    def set_ramp_rate_safety(self, safe_ramp_rate, safe_rr_from, safe_rr_to):
        self.safe_ramp_rate = safe_ramp_rate
        self.safe_rr_from = safe_rr_from
        self.safe_rr_to = safe_rr_to

    def set_setpoint(self, setpoint):
        pass