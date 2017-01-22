# -*- coding: utf-8 -*-
"""
Created on Tue Mar 22 10:06:19 2016

@author: asaph
"""

import pyaudio
import struct
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np

binn=4000
fig = plt.figure()
ax = plt.axes(xlim=(0, 4000), ylim=(5, 2000000))
#ax = plt.axes(xlim=(0, 4000), ylim=(-10000, 10000))

line, = ax.plot([], [], lw=2)

pa=pyaudio.PyAudio()

dev = None
for i in range(pa.get_device_count()):
    if 'Webcam' in pa.get_device_info_by_index(i).get('name'):
        dev = i
        break
        
stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=binn, input_device_index=dev) 

x=(np.linspace(0, binn-1, binn)*44100.)/binn + 1

def init():
    line.set_data([], [])
    return line,

def animate(i):
    a=stream.read(binn, exception_on_overflow = False)
    y=(np.abs(np.fft.fft(struct.unpack('<'+str(binn)+'h', a))))
    #y=(struct.unpack('<'+str(binn)+'h', a))
    
    if np.max(y)>500000:
        mf=x[y.argmax()]
        if mf<5000:
            print(x[y.argmax()])
    	#x=np.linspace(0, binn-1, binn)
    #y=b[200:]
    line.set_data(x, y)
    return line,


anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=200, interval=20, blit=True)



plt.show()
