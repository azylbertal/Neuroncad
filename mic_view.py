import numpy as np
import socket
import matplotlib.pyplot as plt
from matplotlib import animation

audio_bin=4000

TCP_IP = '192.168.0.103'
TCP_PORT = 5006
BUFFER_SIZE = 1024  

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

conn, addr = s.accept()

fig = plt.figure()
ax = plt.axes(xlim=(0, audio_bin), ylim=(-100000, 100000))
line, = ax.plot([], [], lw=2)
x=(np.linspace(0, audio_bin-1, audio_bin)*44100.)/audio_bin + 1

def init():
    line.set_data([], [])
    return line,

def animate(i):
    buff=np.zeros(audio_bin, dtype='int16')
    conn.send('1')
    i=0
    while i<audio_bin:
        pack = np.fromstring(conn.recv(audio_bin), dtype='int16')
        buff[i:(i+len(pack))]=pack
        i+=len(pack)
        
    line.set_data(x, buff)
    return line,

anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=200, interval=20, blit=True)

plt.show()

print("disconnected")
conn.close()
print("all done")
