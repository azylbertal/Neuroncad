# -*- coding: utf-8 -*-
"""
Created on Tue May 24 09:50:45 2016

@author: asaph
"""

import RPi.GPIO as io

FORWARD_LEFT = 17
BACKWARD_LEFT = 18
FORWARD_RIGHT = 23
BACKWARD_RIGHT = 22

class Motors(object):
    def __init__(self):

        io.setup(FORWARD_LEFT, io.OUT)
        io.setup(BACKWARD_LEFT, io.OUT)
        io.setup(FORWARD_RIGHT, io.OUT)
        io.setup(BACKWARD_RIGHT, io.OUT)

        self.forward_left_pwm=io.PWM(FORWARD_LEFT, 500)
        self.backward_left_pwm=io.PWM(BACKWARD_LEFT, 500)
        self.forward_right_pwm=io.PWM(FORWARD_RIGHT, 500)
        self.backward_right_pwm=io.PWM(BACKWARD_RIGHT, 500)

        self.forward_left_pwm.start(0)
        self.backward_left_pwm.start(0)
        self.forward_right_pwm.start(0)
        self.backward_right_pwm.start(0)
    
    def update_power(self, left_power, right_power):
        if abs(left_power)>0.00001:
            if left_power>0:
                if left_power>100:
                    left_power=100
                self.backward_left_pwm.ChangeDutyCycle(0)			
                self.forward_left_pwm.ChangeDutyCycle(int(left_power))
            else:
                if left_power<-100:
                    left_power=-100
                self.forward_left_pwm.ChangeDutyCycle(0)
                self.backward_left_pwm.ChangeDutyCycle(-int(left_power))
        else:
            self.forward_left_pwm.ChangeDutyCycle(0)
            self.backward_right_pwm.ChangeDutyCycle(0)

        if abs(right_power)>0.00001:
            if right_power>0:
                if right_power>100:
                    right_power=100
                self.backward_right_pwm.ChangeDutyCycle(0)
                self.forward_right_pwm.ChangeDutyCycle(int(right_power))
            else:
                if right_power<-100:
                    right_power=-100
                self.forward_right_pwm.ChangeDutyCycle(0)
                self.backward_right_pwm.ChangeDutyCycle(-int(right_power))
        else:
            self.forward_right_pwm.ChangeDutyCycle(0)
            self.backward_right_pwm.ChangeDutyCycle(0)
    
    