#!/usr/bin/python
#import os
import pygame
import numpy as np

#from pygame.locals import *
import pygame.camera

width = 160
height = 120

#initialise pygame   
pygame.init()
pygame.camera.init()
cam = pygame.camera.Camera("/dev/video0",(width,height), 'HSV')
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
    try_array=pygame.surfarray.pixels3d(image)
    try_array[:, :, 0]=try_array[:, :, 2]
    try_array[:, :, 1]=try_array[:, :, 2]
    scaledDown = pygame.transform.scale(catSurfaceObj, (64, 48))

    scaledUp = pygame.transform.scale(scaledDown, (640, 480))
    windowSurfaceObj.blit(scaledUp,(0,0))
    pygame.display.update()

print cam.get_size()
cam.stop()
pygame.quit()


   