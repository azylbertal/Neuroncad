"""
(C) Asaph Zylbertal 2016, HUJI, Jerusalem, Israel

Interface with SPI ADC chip (for IR distance sensor etc.)
"""

import spidev


class SpiSensors(object):

    def __init__(self, gains):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.gains = gains

    def ReadChannel(self, channel):
        adc = self.spi.xfer2([1, (8 + channel) << 4, 0])
        data = ((adc[1] & 3) << 8) + adc[2]
        return data

    def get_stim_amp(self, channel):
        channel_dat = self.ReadChannel(channel)
        return channel_dat / self.gains[channel]
