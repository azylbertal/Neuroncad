import os
import pygame
import pygame.camera
import numpy as np
import socket
import multiprocessing
import pyaudio
import struct
import RPi.GPIO as io
import spidev
import pickle
import Adafruit_LSM303
from time import sleep
from smbus import SMBus

busNum = 1
b = SMBus(busNum)
LGD = 0x6b #Device I2C slave address
LGD_WHOAMI_ADDRESS = 0x0F
LGD_WHOAMI_CONTENTS = 0b11010111 #Device self-id

LGD_CTRL_1 = 0x20 #turns on gyro
LGD_CTRL_2 = 0x21 #can set a high-pass filter for gyro
LGD_CTRL_3 = 0x22
LGD_CTRL_4 = 0x23
LGD_CTRL_5 = 0x24
LGD_CTRL_6 = 0x25

LGD_TEMP = 0x26

#Registers holding gyroscope readings
LGD_GYRO_X_LSB = 0x28
LGD_GYRO_X_MSB = 0x29
LGD_GYRO_Y_LSB = 0x2A
LGD_GYRO_Y_MSB = 0x2B
LGD_GYRO_Z_LSB = 0x2C
LGD_GYRO_Z_MSB = 0x2D

FORWARD_LEFT = 18
BACKWARD_LEFT = 17
FORWARD_RIGHT = 22
BACKWARD_RIGHT = 23

CAMERA_TCP_PORT = 5005
MIC_TCP_PORT = 5006
LEFT_MOTOR_PORT = 5007
RIGHT_MOTOR_PORT = 5008
SENS_TCP_PORT = 5009

BUFFER_SIZE = 1024

SETTINGS_FILE = "RTIMULib"

def twos_comp_combine(msb, lsb):
    twos_comp = 256*msb + lsb
    if twos_comp >= 32768:
        return twos_comp - 65536
    else:
        return twos_comp

def getGyro():
    gyrox = twos_comp_combine(b.read_byte_data(LGD, LGD_GYRO_X_MSB), b.read_byte_data(LGD, LGD_GYRO_X_LSB))
    gyroy = twos_comp_combine(b.read_byte_data(LGD, LGD_GYRO_Y_MSB), b.read_byte_data(LGD, LGD_GYRO_Y_LSB))
    gyroz = twos_comp_combine(b.read_byte_data(LGD, LGD_GYRO_Z_MSB), b.read_byte_data(LGD, LGD_GYRO_Z_LSB))

    return (gyrox, gyroy, gyroz)

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
        if s.recv(1) == 'c':
	    break
        catSurfaceObj = cam.get_image()
        scaledDown = pygame.transform.scale(
            catSurfaceObj, (int(cam_width), int(cam_height)))
        pixArray = pygame.surfarray.pixels3d(scaledDown)
    
        pixArray[:, :, 0] = pixArray[:, :, 2]
        pixArray[:, :, 1] = pixArray[:, :, 2]
        np.copyto(img_buffer, pixArray[:, :, 2])
        dat = img_buffer.tostring()

        s.send(dat)
    s.close()


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
        if s.recv(1)=='c': break
        a = stream.read(audio_bin, exception_on_overflow = False)
        b = np.array(struct.unpack('<' + str(audio_bin) + 'h', a), dtype='int16')
        dat = b.tostring()
        
        s.send(dat)
    s.close()

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
    sleep(1)
    s_right = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_right.connect((TCP_IP, RIGHT_MOTOR_PORT))
    print 'connected to motor server'
    while True:
        left_dat=s_left.recv(2)
        right_dat=s_right.recv(2)
	
	if left_dat == None or right_dat == None or len(left_dat)==0 or len(right_dat)==0:
	    break
        left_power=struct.unpack("h", left_dat)[0]
        right_power=struct.unpack("h", right_dat)[0]
        if abs(left_power) > 0:
            if left_power > 0:
#                if left_power > 100:
#                    left_power = 100
                backward_left_pwm.ChangeDutyCycle(0)
                forward_left_pwm.ChangeDutyCycle(left_power)
#		io.output(BACKWARD_LEFT, 0)
#		io.output(FORWARD_LEFT, 1)
            else:
#                if left_power < -100:
#                    left_power = -100
                forward_left_pwm.ChangeDutyCycle(0)
                backward_left_pwm.ChangeDutyCycle(-left_power)
#		io.output(FORWARD_LEFT, 0)
#		io.output(BACKWARD_LEFT, 1)

        else:
            forward_left_pwm.ChangeDutyCycle(0)
            backward_left_pwm.ChangeDutyCycle(0)
#	    io.output(FORWARD_LEFT, 0)
#	    io.output(BACKWARD_LEFT, 0)

        if abs(right_power) > 0:
            if right_power > 0:
#                if right_power > 100:
#                    right_power = 100
                backward_right_pwm.ChangeDutyCycle(0)
                forward_right_pwm.ChangeDutyCycle(right_power)
#		io.output(BACKWARD_RIGHT, 0)
#		io.output(FORWARD_RIGHT, 1)
            else:
#                if right_power < -100:
#                    right_power = -100
                forward_right_pwm.ChangeDutyCycle(0)
                backward_right_pwm.ChangeDutyCycle(-right_power)
#		io.output(FORWARD_RIGHT, 0)
#		io.output(BACKWARD_RIGHT, 1)
        else:
#	    io.output(FORWARD_RIGHT, 0)
#	    io.output(BACKWARD_RIGHT, 0)

            forward_right_pwm.ChangeDutyCycle(0)
            backward_right_pwm.ChangeDutyCycle(0)

#    io.output(FORWARD_LEFT, 0)
#    io.output(BACKWARD_LEFT, 0)
#    io.output(FORWARD_RIGHT, 0)
#    io.output(BACKWARD_RIGHT, 0)
    forward_right_pwm.stop()
    forward_left_pwm.stop()
    backward_right_pwm.stop()
    backward_left_pwm.stop()

    s_left.close()
    s_right.close()
    io.cleanup()
            

def sensors_str():

    f=open('calib.ini', 'r')
    cal = pickle.load(f)
    f.close()

    if b.read_byte_data(LGD, LGD_WHOAMI_ADDRESS) == LGD_WHOAMI_CONTENTS:
        print 'L3GD20H detected successfully on I2C bus '+str(busNum)+'.'
    else:
        print 'No L3GD20H detected on bus on I2C bus '+str(busNum)+'.'
    b.write_byte_data(LGD, LGD_CTRL_1, 0x0F)

    lsm303 = Adafruit_LSM303.LSM303()

    spi = spidev.SpiDev()
    spi.open(0, 0)
    print 'connecting to sensor server'
    s_sens = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_sens.connect((TCP_IP, SENS_TCP_PORT))
    print 'connected to sensor server'
    while True:

	req=s_sens.recv(1)
        if req=='c':
	    break
        adc = spi.xfer2([1, (8 + 0) << 4, 0])
        prox_data = ((adc[1] & 3) << 8) + adc[2]
        prox_str = struct.pack("H", prox_data)

	(accel, mag) = lsm303.read()
	gyro = getGyro()
	gyrox_str = struct.pack("f", gyro[0] - cal['gyro'][0])        
	gyroy_str = struct.pack("f", gyro[1] - cal['gyro'][1])        
	gyroz_str = struct.pack("f", gyro[2] - cal['gyro'][2])        

	accelx_str = struct.pack("f", accel[0])        
	accely_str = struct.pack("f", accel[1])        
	accelz_str = struct.pack("f", accel[2])        

	magnetx_str = struct.pack("f", mag[0] - cal['mag'][0])        
	magnety_str = struct.pack("f", mag[1] - cal['mag'][1])        
	magnetz_str = struct.pack("f", mag[2] - cal['mag'][2])        

	s_sens.send(prox_str + gyrox_str + gyroy_str + gyroz_str + accelx_str + accely_str + accelz_str + magnetx_str + magnety_str + magnetz_str)
        sleep(0.01)
    s_sens.close()


#s_broad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#s_broad.bind(('', 50000))

print 'waiting for server'
#TCP_IP, wherefrom = s_broad.recvfrom(1500, 0)
TCP_IP = '10.42.0.1'
print 'server ip:'+TCP_IP

cam_proc = multiprocessing.Process(target = camera_stream, args = ())
mic_proc = multiprocessing.Process(target = mic_stream, args = ())
motor_proc = multiprocessing.Process(target = motor_control, args = ())
sensors_proc = multiprocessing.Process(target = sensors_str, args = ())

sleep(1)
cam_proc.start()
sleep(1)
mic_proc.start()
sleep(1)
motor_proc.start()
sleep(2.5)
sensors_proc.start()
