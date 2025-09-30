# TODO: Make terminate->running command somehow non-blocking or just accept 20ms freeze on send

from core.serial_worker import SerialWorker
import time
import logging

logger = logging.getLogger(__name__)

class Shutter():
    """Shutters currently use COM8"""
    
    def __init__(self, address, ser: SerialWorker):
        self.ser = ser
        self.address = address
        self.is_open = False

    def toggle(self):
        if self.is_open:
            self.close()
        if not self.is_open:
            self.open()

    def send_command(self, cmd):
        logger.debug(f"Pressure {self.address} sending on {self.ser.port}: {cmd}")
        self.ser.send_message(f'{cmd}\r\n'.encode('utf-8'))

    def reset(self):
        self.send_command(f'/{self.address}TR')
        time.sleep(0.02)
        self.send_command(f'/{self.address}e0R')
        self.is_open = False

    def open(self):
        self.send_command(f'/{self.address}TR')
        time.sleep(0.02)
        self.send_command(f'/{self.address}e7R')
        self.is_open = True

    def close(self):
        self.send_command(f'/{self.address}TR')
        time.sleep(0.02)
        self.send_command(f'/{self.address}e8R')
        self.is_open = False