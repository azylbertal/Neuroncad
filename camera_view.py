import pygame
import numpy as np
from bluetooth import *

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
screen = pygame.display.set_mode((100, 100))

while True:
        
    img = np.fromstring(client_sock.recv(32*24))
    if len(img) == 1: break
    img = np.reshape(img, (32, 24))
    screen.blit(img, (0, 0))
    pygame.display.update()

print("disconnected")
client_sock.close()
server_sock.close()
print("all done")
