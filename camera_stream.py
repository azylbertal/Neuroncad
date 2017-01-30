import os
import pygame
import pygame.camera
import numpy as np

from bluetooth import *
import sys

if sys.version < '3':
    input = raw_input

addr = None

if len(sys.argv) < 2:
    print("no device specified.  Searching all nearby bluetooth devices for")
    print("the SampleServer service")
else:
    addr = sys.argv[1]
    print("Searching for SampleServer on %s" % addr)

# search for the SampleServer service
uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"
service_matches = find_service( uuid = uuid, address = addr )

if len(service_matches) == 0:
    print("couldn't find the SampleServer service =(")
    sys.exit(0)

first_match = service_matches[0]
port = first_match["port"]
name = first_match["name"]
host = first_match["host"]

print("connecting to \"%s\" on %s" % (name, host))

# Create the client socket
sock=BluetoothSocket( RFCOMM )
sock.connect((host, port))

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
    sock.send(dat)
