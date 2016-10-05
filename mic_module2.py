"""
(C) Asaph Zylbertal 2016, HUJI, Jerusalem, Israel

Interface with microphone on a USB webcam

"""

try:
    import pyaudio
    PA = True
except:
    PA = False
    
        
import struct
import numpy as np

class Mic(object):

    def __init__(self, audio_bin, threshold, audio_gain):
        self.shut_down = False
        if PA:
            try:
                self.pa=pyaudio.PyAudio()
                self.stream = self.pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=audio_bin, input_device_index=8)                
                
#                self.inp = alsaaudio.PCM(
#                    alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, u'plughw:CARD=C170,DEV=0')
#                self.inp.setchannels(1)
#                self.inp.setrate(44100)
#                self.inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
                self.audio_bin = audio_bin
#                self.inp.setperiodsize(audio_bin)
                self.online = True
                self.freqs = np.zeros(audio_bin)
                self.audio_gain = audio_gain
                self.threshold = threshold
                print 'Mic detected'
            except:
                self.online = False
                print "Mic not detected"
        else:
            print "pyaudio not installed"
            self.online = False

    def get_audio_freqs(self):

        while not self.shut_down:
            
            a = self.stream.read(self.audio_bin, exception_on_overflow = False)
            self.freqs = np.abs(np.fft.fft(struct.unpack('<' + str(self.audio_bin) + 'h', a)))
            

        
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

    def __del__(self):
        print "cleaning audio stream"
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()