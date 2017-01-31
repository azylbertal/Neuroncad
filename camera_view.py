import pygame
import numpy as np
import socket

w = 640
h = 400

TCP_IP = '192.168.0.103'
TCP_PORT = 5005
BUFFER_SIZE = 1024  

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

conn, addr = s.accept()

pygame.init()
screen = pygame.display.set_mode((w, h))
buff=np.zeros(w*h, dtype='uint8')
while True:
    #client_sock.send('1')
    i=0
    while i<(w*h):
        pack = np.fromstring(conn.recv(w*h), dtype='uint8')
        
        buff[i:(i+len(pack))]=pack
        i+=len(pack)
    img = np.reshape(buff, (w, h))
    
    pygame.surfarray.blit_array(screen, img.astype('int'))
    pygame.display.update()

print("disconnected")
conn.close()
print("all done")
