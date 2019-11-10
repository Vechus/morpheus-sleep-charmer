import smbus
import time

class si7021:
	def __init__(self, interface):
		self.bus = smbus.SMBus(interface)
		time.sleep(0.5)
		self.addr = 0x40

	def read_humidity(self):
		self.bus.write_byte(self.addr, 0xF5)
		time.sleep(0.1)
		hum = (self.bus.read_byte(self.addr) << 8) + self.bus.read_byte(self.addr)
		hum = hum * 125.0
		hum = hum / 65536.0
		hum = hum - 6.0
		
		return hum

	def read_temperature(self):
		self.bus.write_byte(self.addr, 0xF3)
		time.sleep(0.1)
		temp = (self.bus.read_byte(self.addr) << 8) + self.bus.read_byte(self.addr)
		temp = temp * 175.72
		temp = temp / 65536.0
		temp = temp - 46.85

		return temp
