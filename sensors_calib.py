import os
import numpy as np
import RPi.GPIO as io
import Adafruit_LSM303
from time import sleep
from smbus import SMBus
import pickle

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

def calib_gyro():
    if b.read_byte_data(LGD, LGD_WHOAMI_ADDRESS) == LGD_WHOAMI_CONTENTS:
        print 'L3GD20H detected successfully on I2C bus '+str(busNum)+'.'
    else:
        print 'No L3GD20H detected on bus on I2C bus '+str(busNum)+'.'
    b.write_byte_data(LGD, LGD_CTRL_1, 0x0F)

    print 'Calibrating gyros'

    calibx=np.zeros(500)
    caliby=np.zeros(500)
    calibz=np.zeros(500)
    

    for i in range(500):
	(calibx[i], caliby[i], calibz[i]) = getGyro()
        
    return (np.mean(calibx), np.mean(caliby), np.mean(calibz))

def calib_mag():

    print "Calibrating magnetometer, rotate sensor"
    lsm303 = Adafruit_LSM303.LSM303()

    calibx=np.zeros(500)
    caliby=np.zeros(500)
    calibz=np.zeros(500)

    for i in range(500):
	(accel, mag) = lsm303.read()

	calibx[i]=mag[0]
	caliby[i]=mag[1]
	calibz[i]=mag[2]

        sleep(0.1)

    xshift=(np.max(calibx)+np.min(calibx))/2.
    yshift=(np.max(caliby)+np.min(caliby))/2.
    zshift=(np.max(calibz)+np.min(calibz))/2.

    return (xshift, yshift, zshift)


gyro_rest=calib_gyro()
print gyro_rest
mag_shift=calib_mag()
print mag_shift

cal={'gyro':gyro_rest, 'mag':mag_shift}
f=open('calib.ini', 'w')
pickle.dump(cal, f)
f.close()

