import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI
import spidev
import time
import os
 
# Open SPI bus : questa parte va nel main per dichiarare la spi che poi
# l'adc ha come ingresso

# spi = spidev.SpiDev()
# spi.open(0,0)
# spi.max_speed_hz=1000000

class MCP3008 :
    def __init__ (self, clk=None, cs=None, miso=None, mosi=None, spi=None, gpio=None):
        self._spi = None
        #Handle hardware SPI
        if spi is not None:
            self._spi = spi
        elif clk is not None and cs is not None and miso is not None and mosi is not None:
            # Default to platform GPIO if not provided.
            if gpio is None:
                gpio = GPIO.get_platform_gpio()
            self._spi = SPI.BitBang(gpio, clk, mosi, miso, cs)
        else:
            raise ValueError('Must specify either spi for for hardware SPI or clk, cs, miso, and mosi for software SPI!')
        self._spi.set_clock_hz(1000000)
        self._spi.set_mode(0)
        self._spi.set_bit_order(SPI.MSBFIRST)
    
    #questa inizializzazione è necessaria nel caso in cui nel main non vengano passate le informazioni necessarie
    
# Function to read SPI data from MCP3008 chip
# Channel must be an integer 0-7
    def ReadChannel(self, channel):
        adc = spi.xfer2([1,(8+channel)<<4,0])
        data = ((adc[1]&3) << 8) + adc[2]
        return data
 
