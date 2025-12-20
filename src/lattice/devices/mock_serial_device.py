import random
import logging

logger = logging.getLogger(__name__)

class MockSerialDevice():
    def __init__(self, port: str, baudrate: int, timeout: float):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.buffer: list[bytes] = []
        
    def reset_input_buffer(self):
        self.buffer = []
    
    def reset_output_buffer(self):
        pass

    def flush(self):
        pass
        
    def is_open(self) -> bool:
        return True
        
    def write(self, msg: str):
        """
        Add some data to the buffer depending on msg
        """
        raise NotImplementedError("This method must be implemented!")
    
    def readline(self) -> bytes | None:
        if len(self.buffer) > 0:
            return self.buffer.pop(0)
        
        return None
    
class MockPressureGauge(MockSerialDevice):
    def __init__(self, port: str, baudrate: int, timeout: float):
        super().__init__(port, baudrate, timeout)
        self.is_on: dict[bool] = {}
        self.addresses: list[str] = []
    
    def write(self, msg: bytes):
        """
        Handle the following command types:
        Turn on        - #0031{address}\r\n | ex. #0031T1\r\n
        Turn off       - #0030{address}\r\n | ex. #0030T1\r\n
        Query pressure - #0002{address}\r\n | ex. #0002T1\r\n
        """
        
        # Decode msg
        msg = msg.decode('utf-8', errors='ignore').strip()
        
        # Basic validation
        if len(msg) < 6:
            return
        
        # Trim leading #
        msg = msg[1:]
        
        # Store address
        address = msg[4:6]
        
        # Handle turn on and off
        if msg[0:3] == "003":
            if msg[3] == "1":
                logger.debug("Mock pressure gauge turning on...")
                self.is_on[address] = True
                # This is discarded by host but should be included
                # to ensure it is discarded
                self.buffer.append("I turned on!".encode('utf-8'))
                return
            
            if msg[3] == "0":
                logger.debug("Mock pressure gauge turning off...")
                self.is_on[address] = False
                # This is discarded by host but should be included
                # to ensure it is discarded
                self.buffer.append("I turned off!".encode('utf-8')) 
                return
        
        # Don't handle any other type of query if the device is not on or not registered
        if address not in self.is_on:
            return
        
        if not self.is_on[address]:
            return
            
        # Handle pressure query
        if msg[0:4] == "0002":
            pressure = f">{random.uniform(0, 1000):.3e}"
            self.buffer.append(pressure.encode('utf-8'))