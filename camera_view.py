import sys
from time import sleep
folder = '/home/asaph/anaconda2/lib/python2.7/site-packages'
if not folder in sys.path:
    sys.path.append(folder)
     
import pygame
import numpy as np
from bluetooth import *

w = 100
h = 100

server_sock=BluetoothSocket( RFCOMM )
server_sock.bind(("",PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

advertise_service( server_sock, "SampleServer",
                   service_id = uuid,
                   service_classes = [ uuid, SERIAL_PORT_CLASS ],
                   profiles = [ SERIAL_PORT_PROFILE ], 
#                   protocols = [ OBEX_UUID ] 
                    )
                   
print("Waiting for connection on RFCOMM channel %d" % port)

client_sock, client_info = server_sock.accept()
print("Accepted connection from ", client_info)

pygame.init()
screen = pygame.display.set_mode((w, h))
buff=np.zeros(w*h, dtype='uint8')
while True:
    #client_sock.send('1')
    i=0
    while i<(w*h):
        pack = np.fromstring(client_sock.recv(w*h), dtype='uint8')
        
        buff[i:(i+len(pack))]=pack
        i+=len(pack)
    img = np.reshape(buff, (w, h))
    
    pygame.surfarray.blit_array(screen, img.astype('int'))
    pygame.display.update()

print("disconnected")
client_sock.close()
server_sock.close()
print("all done")
