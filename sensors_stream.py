import os
import pygame
import pygame.camera
import numpy as np
import socket
import multiprocessing
import pyaudio
import struct

TCP_IP = '192.168.0.100'
CAMERA_TCP_PORT = 5005
MIC_TCP_PORT = 5006
BUFFER_SIZE = 1024

def camera_stream():

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, CAMERA_TCP_PORT))
    
    cam_dev = "/dev/video0"
    cam_width = 100
    cam_height = 100
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
    
            print "Camera detected"
            cam_online = True
        except:
            print "Camera not detected"
            cam_online = False    
    cam.start()
    
    img_buffer=np.zeros((cam_width, cam_height), dtype='uint8')
    
    while True:
        s.recv(1)
        catSurfaceObj = cam.get_image()
        scaledDown = pygame.transform.scale(
            catSurfaceObj, (int(cam_width), int(cam_height)))
        pixArray = pygame.surfarray.pixels3d(scaledDown)
    
        pixArray[:, :, 0] = pixArray[:, :, 2]
        pixArray[:, :, 1] = pixArray[:, :, 2]
        np.copyto(img_buffer, pixArray[:, :, 2])
        dat = img_buffer.tostring()
        s.send(dat)


def mic_stream():
    audio_bin=4000
    
    pa=pyaudio.PyAudio()
    dev = None
    for i in range(pa.get_device_count()):
        if 'Webcam' in pa.get_device_info_by_index(i).get('name'):
            dev = i
            break
    
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=audio_bin, input_device_index=dev) 
    #print dev           
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, MIC_TCP_PORT))
    
    
    while True:
        s.recv(1)
        a = stream.read(audio_bin, exception_on_overflow = False)
        b = np.array(struct.unpack('<' + str(audio_bin) + 'h', a), dtype='int16')
        dat = b.tostring()
        
        s.send(dat)


cam_proc = multiprocessing.Process(target = camera_stream, args = ())
mic_proc = multiprocessing.Process(target = mic_stream, args = ())

cam_proc.start()
mic_proc.start()
