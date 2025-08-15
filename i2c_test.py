import smbus2
bus = smbus2.SMBus(1)
address = 0x48

try:
    value = bus.read_byte(address)
    print("Device responded: ", value)
except OSError as e:
    print("OSError: ", e)