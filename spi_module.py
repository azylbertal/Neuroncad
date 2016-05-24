# -*- coding: utf-8 -*-
"""
Created on Tue May 24 09:04:49 2016

@author: asaph
"""
import spidev
    
class SpiSensors(object):
    def __init__(self, gains):
        self.spi = spidev.SpiDev()
        self.open(0, 0)
        self.gains=gains
        
    def ReadChannel(self, channel):
        adc = self.spi.xfer2([1,(8+channel)<<4,0])
        data = ((adc[1]&3) << 8) + adc[2]
        return data
        
    def get_stim_amp(self, channel):
        channel_dat=self.ReadChannel(channel)
        return channel_dat/self.gains[channel]