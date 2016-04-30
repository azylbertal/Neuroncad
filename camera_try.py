#!/usr/bin/python
#import os
import pygame
import numpy as np

#from pygame.locals import *
import pygame.camera

width = 640
height = 480

#initialise pygame   
pygame.init()
pygame.camera.init()
cam = pygame.camera.Camera("/dev/video0",(width,height), 'RGB')
cam.start()

#setup window
windowSurfaceObj = pygame.display.set_mode((640,480),1,16)
pygame.display.set_caption('Camera')

#take a picture
going=True
while going:
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        going=False
    image = cam.get_image()
    catSurfaceObj = image
#    try_array=pygame.surfarray.pixels3d(image)
#    try_array[:, :, 0]=try_array[:, :, 2]
#    try_array[:, :, 1]=try_array[:, :, 2]
#    scaledDown = pygame.transform.scale(catSurfaceObj, (320, 240))

#    scaledUp = pygame.transform.scale(scaledDown, (640, 480))
    windowSurfaceObj.blit(catSurfaceObj,(0,0))
    pygame.display.update()

print cam.get_size()
cam.stop()
pygame.quit()


   
