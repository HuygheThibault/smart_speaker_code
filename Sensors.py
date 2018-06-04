from RPi import GPIO
from spidev import SpiDev
import time, math
GPIO.setmode(GPIO.BCM)


def value_to_percent(channel=0):
    spi = SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 20 ** 5
    spi_data = spi.xfer2([1, (8 + channel) << 4, 0])
    spi.close()

    licht_waarde = int((spi_data[1] << 8) + spi_data[2])
    licht_percent = round((licht_waarde / 1023 * 100), 2)

    digitale_waarde = float((spi_data[1] << 8) + spi_data[2])
    # decibels = round((digitale_waarde+83.2073) /11.003 , 2)
    decibels = (20.0 * math.log10(digitale_waarde / 5.0))

    # return print("lichtsterkte: ", licht_percent)
    return print("decibels: ", decibels)