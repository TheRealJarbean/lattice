import logging
from lattice.devices.virtual_hardware import VirtualSerialDevice

logger = logging.getLogger(__name__)

class VirtualMotor(VirtualSerialDevice):
    """
    To be used in place of a Serial connection when testing the Motor class
    or any of it's child classes. Simulates motor behavior and responses.

    Simplistic simulation only, does not cover all motor behavior or potential responses and errors.
    (At time of writing this comment)
    """

    def __init__(self, port: str, baudrate: int, timeout: float):
        super().__init__(port, baudrate, timeout)

        self.COMMANDS = {
            "?": self.query, 
            "P": self.move_relative,
            "A": self.move_absolute, 
            "D": self.move_relative_reverse,
            "Z": self.home, 
            "z": self.set_current_step_count
        }

        self.position = 0
        self.polarity = 1

    def write(self, msg: str):
        logger.debug(f"Virtual motor received message: {msg}")
        command_buffer = [""]
        is_command = True

        # Validate message and fill command buffer
        if len(msg) < 5:
            logger.error("Message shorter than 5 characters. Message must begin with '/[address]' and end with 'R\\r\\n'")
            return

        if msg[0] != '/':
            logger.error(f"First character of message is {msg[0]}. It must be a '/'")
            return

        if msg[1] not in "123456789ABCDEF":
            logger.error(f"{msg[1]} is an invalid motor address. Must be one of '123456789ABCDEF'")
            return

        if msg[-2:] != "\r\n":
            logger.error(f"Invalid line ending: {msg[-2:]}\n Must be '\\r\\n'")
            return

        if msg[-3] != 'R':
            logger.error(f"Missing 'R' at and of message before line ending.")
            return

        for char in msg[2:-3]:
            print(char)
            # Is a command
            if is_command:
                if char in "0123456789":
                    if command_buffer[-1] not in self.COMMANDS.keys():
                        logger.error(f"Invalid command: {command_buffer[-1]}" if command_buffer[-1] != "" else "No commands given")
                        return

                    command_buffer.append(char)
                    is_command = False
                    continue
                
                command_buffer[-1] += char
                continue

            # Is a value
            if char not in "0123456789":
                command_buffer.append(char)
                is_command = True
                continue

            command_buffer[-1] += char

        if is_command:
            logger.error(f"Message cannot end with a command/ending command has no value.")
            return

        # Process commands in buffer
        logger.debug(f"Command buffer: {command_buffer}")
        while len(command_buffer) != 0:
            command = command_buffer.pop(0)
            value = command_buffer.pop(0)

            self.COMMANDS[command](int(value))

    def success(self):
        self.buffer.append(b"/0@")
        logger.debug(f"Command successful, motor position is {self.position}")

    def query(self):
        pass

    def move_relative(self, microsteps: int):
        self.position += microsteps * self.polarity
        self.success()

    def move_absolute(self, microsteps: int):
        self.position = microsteps
        self.success()

    def move_relative_reverse(self, microsteps: int):
        self.position -= microsteps * self.polarity
        self.success()

    def home(self):
        self.position = 0
        self.success()

    def set_current_step_count(self, steps):
        self.position = steps
        self.success()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    virt_motor = VirtualMotor("COM6", 9600, 0.1)
    virt_motor.write("/1P1000z0R\r\n")