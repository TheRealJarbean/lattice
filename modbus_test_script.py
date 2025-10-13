from pymodbus.client import ModbusSerialClient

client = ModbusSerialClient(
    port="COM10", 
    baudrate=9600
    )

res = client.read_holding_registers(address=32770, count=2, device_id=3)
registers = res.registers
value = client.convert_from_registers(registers, data_type=client.DATATYPE.FLOAT32)
print(value)