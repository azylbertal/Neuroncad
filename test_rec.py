# -*- coding: utf-8 -*-
"""
Created on Tue Mar 22 10:06:19 2016

@author: asaph
"""

import alsaaudio
import struct
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np

fig = plt.figure()
ax = plt.axes(xlim=(0, 300), ylim=(0, 30))
line, = ax.plot([], [], lw=2)

inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, u'plughw:CARD=C170,DEV=0')

    # Set attributes: Mono, 44100 Hz, 16 bit little endian samples
inp.setchannels(1)
inp.setrate(44100)
inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)

# The period size controls the internal number of frames per period.
# The significance of this parameter is documented in the ALSA api.
# For our purposes, it is suficcient to know that reads from the device
# will return this many frames. Each frame being 2 bytes long.
# This means that the reads below will return either 320 bytes of data
# or 0 bytes of data. The latter is possible because we are in nonblocking
# mode.
inp.setperiodsize(1600)
#b=[]

def init():
    line.set_data([], [])
    return line,

def animate(i):
    l, a=inp.read()
    if not l==-32:	
    	y=np.log(np.abs(np.fft.fft(struct.unpack('<1600h', a))))
    	x=np.linspace(0, 1600, 1600)
    #y=b[200:]
    	line.set_data(x, y)
    return line,
    

anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=200, interval=20, blit=True)

# save the animation as an mp4.  This requires ffmpeg or mencoder to be
# installed.  The extra_args ensure that the x264 codec is used, so that
# the video can be embedded in html5.  You may need to adjust this for
# your system: for more information, see
# http://matplotlib.sourceforge.net/api/animation_api.html
#anim.save('basic_animation.mp4', fps=30, extra_args=['-vcodec', 'libx264'])

plt.show()



