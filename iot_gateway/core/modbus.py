from pymodbus.client import ModbusTcpClient

""""

Dummy mode 


import random

class PLCClient:
    def __init__(self, ip, port=502):
        self.ip = ip

    def read(self, register):
        return random.randint(0, 1000)

"""


class PLCClient:
    def __init__(self, ip, port=502):
        self.client = ModbusTcpClient(ip, port=port)

    def read(self, register):
        try:
            result = self.client.read_holding_registers(register, 1)
            if not result.isError():
                return result.registers[0]
        except Exception as e:
            print(f"[MODBUS ERROR] {e}")
        return None