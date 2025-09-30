from core.serial_worker import SerialWorker
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Pressure:
    """
    Pressure sensors currently use COM6
    Sensor names appear to be T1 I1 I2 and I3
    Appears to request updates periodically, wait 25ms for a response, and wait 10ms to loop
    """

    def __init__(self, address, ser: SerialWorker):
        self.ser = ser
        self.address = address
        self.pressure = 0
        self.rate_per_second = 0.0
        self.is_on = False
        
    def send_command(self, cmd):
        logger.debug(f"Pressure {self.address} sending on {self.ser.port}: {cmd}")
        self.ser.send_message(f'{cmd}\r\n'.encode('utf-8'))

    def update_rate(self):
        """Call in intervals to update rate_per_second automatically"""
        self.rate_per_second = (self.rate_per_second + self.pressures) / 2

    def monitor(self):
        # TODO: Revise this
        # This replicates the sequence structure of LabVIEW, but shouldn't be necessary to run commands sequentially like this
        
        self.send_command(f'#0032{self.address}')
        # Wait 25ms for a response
        if self.is_on:
            self.send_command(f'#0031{self.address}')
        else:
            self.send_command(f'##0030{self.address}')
        # Wait 25ms for a response
        self.send(f'#000F')
        # Wait for 75ms

    def turn_on(self):
        # TODO: Verify this command is correct
        self.send_command(f'#0031{self.address}')
        # Wait 25ms for a response
        
    def turn_off(self):
        # TODO: Verify this command is correct
        self.send_command(f'##0030{self.address}')
        # Wait 25ms for a response