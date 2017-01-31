import pyaudio
import pygame
import numpy as np
import socket
import struct

TCP_IP = '192.168.0.103'
TCP_PORT = 5006
BUFFER_SIZE = 1024
audio_bin=4000

pa=pyaudio.PyAudio()
dev = None
for i in range(pa.get_device_count()):
    if 'Webcam' in pa.get_device_info_by_index(i).get('name'):
        dev = i
        break

stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=audio_bin, input_device_index=dev) 
#print dev           

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))


while True:
    stat = s.recv(1)
    a = stream.read(audio_bin, exception_on_overflow = False)
    dat = np.array(struct.unpack('<' + str(audio_bin) + 'h', a)).tostring()
    s.send(dat)
