# -*- coding: utf-8 -*-
"""
Created on Sun May 22 12:36:11 2016

@author: asaph
"""

import pygame
import pygame.camera
import numpy as np
import os
from copy import deepcopy

RED   = (255,   0,   0)

class Camera(object):
    def __init__(self, dev, width, height, scale, gain):
        self.dev=dev
        self.width=width
        self.height=height
        self.scale=scale
        self.gain=gain
        self.img_buffer=np.zeros((self.width, self.height))
        self.expo=10
        self.first_image=False
        self.shut_down=False
        try:
            pygame.camera.init()
    
            self.cam = pygame.camera.Camera(self.dev,(self.width,self.height), 'HSV')
    
            os.system('v4l2-ctl -d '+self.dev+ ' --set-ctrl exposure_auto=1')
            os.system('v4l2-ctl -d '+self.dev+ ' --set-ctrl exposure_absolute='+str(self.expo))
    
            self.online=True
            print "Camera detected"
        except:
            self.online=False
            print "Camera not detected"

    def update_buffer(self, nrns):
        #os.system('v4l2-ctl -d '+self.cam_dev+ ' --set-ctrl exposure_auto=1')
    
        #cam = pygame.camera.Camera(cam_dev,(width,height), 'HSV')
        self.cam.start()
        pixel_width=self.scale
        pixel_height=self.scale
        self.first_image=False
        while not self.shut_down:
            if self.cam.query_image():
    
                catSurfaceObj = self.cam.get_image()
                scaledDown = pygame.transform.scale(catSurfaceObj, (int(self.width), int(self.height)))
                pixArray=pygame.surfarray.pixels3d(scaledDown)
    
                pixArray[:, :, 0]=pixArray[:, :, 2]
                pixArray[:, :, 1]=pixArray[:, :, 2]
                self.img_buffer=deepcopy(pixArray[:,:,2])
                del pixArray
                self.cam_icon = pygame.transform.scale(scaledDown, (int(self.width*self.scale), int(self.height*self.scale)))
    
                self.first_image=True
            if self.first_image:
                for neur in nrns:
                    if neur.tp=='visual':
                        for c in neur.rf:
                            poly_points=[[c[0]*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, (c[1]+1)*pixel_height], [c[0]*pixel_width, (c[1]+1)*pixel_height]]
                            cl=(int(255/(neur.nid+1)), 255-int(255/(neur.nid+1)), 255)
                            pygame.draw.polygon(self.cam_icon, cl, poly_points, 1)
    
    
        self.cam.stop()


    def get_stim_amp(self, rf):
        
#        vamp=np.mean(self.img_buffer[rf[:, 0], rf[:, 1]])
        vamp=0
        pixels=len(rf)
        for c in rf:
            vamp+=self.img_buffer[c[0], c[1]]
        vamp /= pixels

        return vamp/self.gain        

def receptiveField(brn):

    pixel_width=brn.width/brn.sns.cam.width
    pixel_height=brn.height/brn.sns.cam.height
    #brn.screen.fill(WHITE)
    selected=[]



    brn.sns.cam.cam.start()
    going=True
    pygame.event.set_blocked(pygame.MOUSEMOTION)

    while going:
        event = pygame.event.poll()
        (x, y)=pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            xx=int(x/pixel_width)
            yy=int(y/pixel_height)
            selected.append((xx, yy))
        if event.type == pygame.QUIT:
            going=False
        if brn.sns.cam.online:
            image = brn.sns.cam.cam.get_image()
            catSurfaceObj = image
            try_array=pygame.surfarray.pixels3d(image)
            try_array[:, :, 0]=try_array[:, :, 2]
            try_array[:, :, 1]=try_array[:, :, 2]

            scaledDown = pygame.transform.scale(catSurfaceObj, (int(brn.sns.cam.width), int(brn.sns.cam.height)))

            scaledUp = pygame.transform.scale(scaledDown, (brn.width, brn.height))
        else:
            scaledUp = pygame.Surface((brn.width, brn.height))
        for neur in brn.neurons.sprites():
            if neur.tp=='visual':
                for c in neur.rf:
                    poly_points=[[c[0]*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, (c[1]+1)*pixel_height], [c[0]*pixel_width, (c[1]+1)*pixel_height]]
                    cl=(int(255/(neur.nid+1)), 255-int(255/(neur.nid+1)), 255)
                    pygame.draw.polygon(scaledUp, cl, poly_points, 1)
        brn.screen.blit(scaledUp,(0,0))
        for sel in selected:
            poly_points=[[sel[0]*pixel_width, sel[1]*pixel_height], [(sel[0]+1)*pixel_width, sel[1]*pixel_height], [(sel[0]+1)*pixel_width, (sel[1]+1)*pixel_height], [sel[0]*pixel_width, (sel[1]+1)*pixel_height]]
            pygame.draw.polygon(brn.screen, RED, poly_points)
        pygame.display.update()
    
    brn.sns.cam.cam.stop()
    return np.array(selected)