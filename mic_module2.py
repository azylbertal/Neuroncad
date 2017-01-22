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
import multiprocessing
import ctypes

audio_bin=4000
freqs_base = multiprocessing.Array(ctypes.c_double, audio_bin, lock=False)
freqs = np.frombuffer(freqs_base, dtype=ctypes.c_double)

class Mic(object):

    def __init__(self, audio_bin, threshold, audio_gain):
        self.shut_down = False
        if PA:
            try:
                    
                self.pa=pyaudio.PyAudio()
                dev = None
                for i in range(self.pa.get_device_count()):
                    if 'Webcam' in self.pa.get_device_info_by_index(i).get('name'):
                        dev = i
                        break
                if not dev == None:
                    self.stream = self.pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=audio_bin, input_device_index=8)                
                
#                self.inp = alsaaudio.PCM(
#                    alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, u'plughw:CARD=C170,DEV=0')
#                self.inp.setchannels(1)
#                self.inp.setrate(44100)
#                self.inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
                    self.audio_bin = audio_bin
#                self.inp.setperiodsize(audio_bin)
                    self.online = True
                    
                    self.audio_gain = audio_gain
                    self.threshold = threshold
                    print 'Mic detected'
                    
                else:
                    self.online = False
                    print "Mic not detected"
            except:
                self.online = False
                print "Mic not detected"
        else:
            print "pyaudio not installed"
            self.online = False

            

        
    def get_stim_amp(self, freq):
        if self.online:
            ind = int(round((freq - 1) * (audio_bin / 44100.)))
            fval = freqs[ind]
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
        
def get_audio_freqs(pa):

    while True:
        a = pa.stream.read(audio_bin, exception_on_overflow = False)
        freqs = np.abs(np.fft.fft(struct.unpack('<' + str(audio_bin) + 'h', a)))
