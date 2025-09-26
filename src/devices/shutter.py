from core.serial_worker import SerialWorker
from enum import Enum
import queue

class State(Enum):
    """This is for readability so that closed and open are never confused"""
    OPEN = True
    CLOSED = False

class Shutters(SerialWorker):
    ser = SerialWorker("COM10")

    def __init__(self, address):
        self.address = address
        self.state = State.CLOSED
        self.command_queue = queue.Queue()

    def toggle(self):
        if self.state == State.OPEN:
            self.close()
        if self.state == State.CLOSED:
            self.open()

    def send_next_command(self):
        if self.command_queue.empty():
            return
        
        self.send_command(self.command_queue.get())

    def send_command(self):
        pass

    def reset(self):
        pass

    def open(self):
        pass

    def close(self):
        pass