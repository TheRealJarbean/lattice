# TODO: Make terminate->running command somehow non-blocking or just accept 20ms freeze on send

from core.serial_worker import SerialWorker
import time
import logging

logger = logging.getLogger(__name__)

class Shutter():
    def __init__(self, address):
        self.address = address
        self.is_open = False

class ShutterManager():
    """Shutters currently use COM8"""
    def __init__(self, port, baudrate=9600):
        self.ser = SerialWorker(port, baudrate, monitor_func=self.on_serial_data_received)
        self.shutters = {}

    def add_shutter(self, name, address):
        if name in self.shutters:
            logger.debug("Name already exists in shutters list")
            return
        
        if address in self.shutters.values():
            logger.debug("Address already exists in shutters list")
            return
        
        self.shutters[name] = Shutter(address)
        
    def send_command(self, cmd):
        self.ser.send(f'{cmd}\r\n')

    def start_monitor(self):
        self.ser.start_monitor()

    def stop_monitor(self):
        self.ser.stop_monitor()

    def on_serial_data_received(self, data):
        print(f"Serial data received: {data}")
        
    def toggle(self, name):
        if self.is_open:
            self.close(name)
        if not self.is_open:
            self.open(name)

    def reset(self, name):
        address = self.shutters[name].address
        self.send_command(f'/{address}TR')
        time.sleep(0.02)
        self.send_command(f'/{address}e0R')
        self.is_open = False

    def open(self, name):
        logger.debug("Made it!")
        address = self.shutters[name].address
        logger.debug(f"Opening shutter {address}")
        self.send_command(f'/{address}TR')
        time.sleep(0.02)
        self.send_command(f'/{address}e7R')
        self.is_open = True

    def close(self, name):
        address = self.shutters[name].address
        logger.debug(f"Closing shutter {address}")
        self.send_command(f'/{address}TR')
        time.sleep(0.02)
        self.send_command(f'/{address}e8R')
        self.is_open = False