import os
import pygame
import pygame.camera
import numpy as np
import socket
import multiprocessing
import pyaudio
import struct
import RPi.GPIO as io

FORWARD_LEFT = 17
BACKWARD_LEFT = 18
FORWARD_RIGHT = 23
BACKWARD_RIGHT = 22

TCP_IP = '192.168.0.100'
CAMERA_TCP_PORT = 5005
MIC_TCP_PORT = 5006
LEFT_MOTOR_PORT = 5007
RIGHT_MOTOR_PORT = 5008
BUFFER_SIZE = 1024

def camera_stream():

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, CAMERA_TCP_PORT))
    
    cam_dev = "/dev/video0"
    cam_width = 32
    cam_height = 24
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


def motor_control():

    io.setmode(io.BCM)
    io.setup(FORWARD_LEFT, io.OUT)
    io.setup(BACKWARD_LEFT, io.OUT)
    io.setup(FORWARD_RIGHT, io.OUT)
    io.setup(BACKWARD_RIGHT, io.OUT)

    forward_left_pwm = io.PWM(FORWARD_LEFT, 500)
    backward_left_pwm = io.PWM(BACKWARD_LEFT, 500)
    forward_right_pwm = io.PWM(FORWARD_RIGHT, 500)
    backward_right_pwm = io.PWM(BACKWARD_RIGHT, 500)

    forward_left_pwm.start(0)
    backward_left_pwm.start(0)
    forward_right_pwm.start(0)
    backward_right_pwm.start(0)

    s_left = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_left.connect((TCP_IP, LEFT_MOTOR_PORT))
    s_right = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_right.connect((TCP_IP, RIGHT_MOTOR_PORT))

    while True:
        left_dat=s_left.recv(8)
        right_dat=s_right.recv(8)
	if left_dat == None or right_dat == None:
	    break
        left_power=struct.unpack("d", left_dat)[0]
        right_power=struct.unpack("d", right_dat)[0]

        if abs(left_power) > 0.00001:
            if left_power > 0:
                if left_power > 100:
                    left_power = 100
                backward_left_pwm.ChangeDutyCycle(0)
                forward_left_pwm.ChangeDutyCycle(int(left_power))
            else:
                if left_power < -100:
                    left_power = -100
                forward_left_pwm.ChangeDutyCycle(0)
                backward_left_pwm.ChangeDutyCycle(-int(left_power))
        else:
            forward_left_pwm.ChangeDutyCycle(0)
            backward_right_pwm.ChangeDutyCycle(0)

        if abs(right_power) > 0.00001:
            if right_power > 0:
                if right_power > 100:
                    right_power = 100
                backward_right_pwm.ChangeDutyCycle(0)
                forward_right_pwm.ChangeDutyCycle(int(right_power))
            else:
                if right_power < -100:
                    right_power = -100
                forward_right_pwm.ChangeDutyCycle(0)
                backward_right_pwm.ChangeDutyCycle(-int(right_power))
        else:
            forward_right_pwm.ChangeDutyCycle(0)
            backward_right_pwm.ChangeDutyCycle(0)
    s_left.close()
    s_right.close()
    io.cleanup()
            
cam_proc = multiprocessing.Process(target = camera_stream, args = ())
#mic_proc = multiprocessing.Process(target = mic_stream, args = ())
#motor_proc = multiprocessing.Process(target = motor_control, args = ())

cam_proc.start()
#mic_proc.start()
#motor_proc.start()
