import os
import pygame
import pygame.camera
import numpy as np
import socket


TCP_IP = '192.168.0.103'
TCP_PORT = 5005
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

cam_dev = "/dev/video0"
cam_width = 100
cam_height = 100
cam_scale = 8
cam_gain = 7
cam_expo = 60

if not os.path.exists(cam_dev):
    print "Camera not detected"
    cam_online = False
else:
    try:
	pygame.camera.init()

    	cam = pygame.camera.Camera(cam_dev, (cam_width, cam_height), 'HSV')

    	os.system('v4l2-ctl -d ' + cam_dev +
                  ' --set-ctrl exposure_auto=1')
    	os.system('v4l2-ctl -d ' + cam_dev +
              	  ' --set-ctrl exposure_absolute=' + str(cam_expo))

    	cam_online = True
    	print "Camera detected"
    except:
        cam_online = False
        print "Camera not detected"
            
cam.start()

img_buffer=np.zeros((cam_width, cam_height), dtype='uint8')

while True:
    #stat = sock.recv(1)
    catSurfaceObj = cam.get_image()
    scaledDown = pygame.transform.scale(
        catSurfaceObj, (int(cam_width), int(cam_height)))
    pixArray = pygame.surfarray.pixels3d(scaledDown)

    pixArray[:, :, 0] = pixArray[:, :, 2]
    pixArray[:, :, 1] = pixArray[:, :, 2]
    np.copyto(img_buffer, pixArray[:, :, 2])
    dat = img_buffer.tostring()
    s.send(dat)
