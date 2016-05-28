# -*- coding: utf-8 -*-
"""
Created on Tue May 24 08:59:34 2016

@author: asaph
"""
import alsaaudio
import struct
import numpy as np


class Mic(object):

    def __init__(self, audio_bin, threshold, audio_gain):
        self.shut_down = False
        try:
            self.inp = alsaaudio.PCM(
                alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, u'plughw:CARD=C170,DEV=0')
            self.inp.setchannels(1)
            self.inp.setrate(44100)
            self.inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            self.audio_bin = audio_bin
            self.inp.setperiodsize(audio_bin)
            self.online = True
            self.freqs = np.zeros(audio_bin)
            self.audio_gain = audio_gain
            self.threshold = threshold
            print 'Mic detected'
        except:
            self.online = False
            print "Mic not detected"

    def get_audio_freqs(self):

        while not self.shut_down:
            l, a = self.inp.read()
            if not l == -32:
                self.freqs = np.abs(np.fft.fft(
                    struct.unpack('<' + str(self.audio_bin) + 'h', a)))

    def get_stim_amp(self, freq):
        if self.online:
            ind = int(round((freq - 1) * (self.audio_bin / 44100.)))
            fval = self.freqs[ind]
            if fval > self.threshold:
                return (fval - self.threshold) / self.audio_gain
            else:
                return None
        else:
            return None
