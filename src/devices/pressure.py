from core.serial_worker import SerialWorker

class Pressure:
    ser = SerialWorker("COM10")

    def __init__(self, address):
        self.address = address
        self.pressure = 0
        self.rate_per_second = 0.0

    def update_rate(self):
        """Call in intervals to update rate_per_second automatically"""
        self.rate_per_second = (self.rate_per_second + self.pressures) / 2

    def monitor(self):
        pass

    def turn_on(self):
        pass

    def turn_off(self):
        pass