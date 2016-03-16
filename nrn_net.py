import pygame
import pygame.camera
import math
import pickle
import neuron
import Tkinter as tk
import tkFileDialog
#import matplotlib.pyplot as plt
import numpy as np
import os
import copy
#import cProfile, pstats, StringIO
#from time import sleep
import eztext

try:
    import RPi.GPIO as io
    import spidev
    RPI = True

except:
    RPI = False

if RPI:
    io.setmode(io.BCM)
    spi = spidev.SpiDev()
    spi.open(0, 0)
    downSampleFactor=40.

else:
    downSampleFactor=20.

BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED   = (255,   0,   0)
BLUE  = (0,   0,   255)
width = 1300
height = 710

step=0.1

try:
    pygame.mixer.init()
    spike_sound=pygame.mixer.Sound("spike.wav")
    sound_card=True
except:
    sound_card=False
        
all_neurons = pygame.sprite.Group()

ir_conversion=50.
visual_conversion=7.
motors=False
sensors=False
visuals=False

cam_dev="/dev/video0"
cam_width=32.
cam_height=24.
cam_scale=8


class Neuron(pygame.sprite.Sprite):
    def __init__(self, x, y, tp, shift=True, nid=None, rf=None):
        global motors, sensors, visuals
        super(Neuron, self).__init__()
        self.rf=0
        if tp == 'excitatory':
            self.image = pygame.image.load("pyramidal.bmp").convert()
            self.super_type='neuron'
        elif tp=='inhibitory':
            self.image = pygame.image.load("interneuron.bmp").convert()
            self.super_type='neuron'
        elif tp=='rightforward':
            self.image = pygame.image.load("rightforward.bmp").convert()
            self.super_type='motor'
        elif tp=='rightbackward':
            self.image = pygame.image.load("rightbackward.bmp").convert()
            self.super_type='motor'
        elif tp=='leftforward':
            self.image = pygame.image.load("leftforward.bmp").convert()
            self.super_type='motor'
        elif tp=='leftbackward':
            self.image = pygame.image.load("leftbackward.bmp").convert()
            self.super_type='motor'
        elif tp=='irsensor':
            self.image = pygame.image.load("ir_sensor.bmp").convert()
            self.ir_stm=0
            self.super_type='sensor'
            sensors=True
        elif tp=='visual':
            self.ir_stm=0
            self.image = pygame.image.load("visual.bmp").convert()
            self.visual_stm=0
            self.super_type='sensor'
            pygame.camera.init()
            visuals=True
            if rf==None:
                self.rf=receptiveField()
                pygame.event.set_allowed([pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION])
            else:
                self.rf=rf



        self.nid=nid

        self.tp=tp
        self.image.set_colorkey(WHITE)
        self.rect = self.image.get_rect()
        if shift:
            self.rect.x=x-self.rect.width/2
            self.rect.y=y-self.rect.height/2
        else:
            self.rect.x=x
            self.rect.y=y

        self.mod=neuron.h.Section()
        if self.super_type=='neuron' or self.super_type=='sensor':
            self.mod.insert('hh')

        elif self.super_type=='motor':
            self.mod.insert('pas')
            motors=True
        self.fire_counter=0
        self.axons=[]

    def drawAxons(self):
        recs=[]
        for axon in self.axons:
            recs.append(axon.draw(screen))
        return recs

    def pickledAxons(self):
        paxons=[]
        for axon in self.axons:
            paxons+=[{'points':axon.points, 'weight':axon.w, 'start':axon.start_id, 'end':axon.end_id}]
        return paxons

class pickledNeuron():
    def __init__(self, nrn):
        self.rect=nrn.rect
        self.tp=nrn.tp
        self.super_type=nrn.super_type
        self.nid=nrn.nid
        self.rf=nrn.rf
        self.axons=nrn.pickledAxons()

class Button(pygame.sprite.Sprite):
    def __init__(self, imgf, x, y, tp=None):

        super(Button, self).__init__()
        self.image = pygame.image.load(imgf).convert()
        self.image.set_colorkey(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x=x
        self.rect.y=y
        self.tp=tp

class Axon():
    def __init__(self, startp, endp, points, tp, weight, start_id, end_id, interp=True):

        self.start_id=start_id
        self.end_id=end_id
        if interp:
            self.points=[]
            for p in range(len(points)-1):
                self.points+=inter(points[p], points[p+1])
        else:
            self.points=points
        self.len=len(self.points)
        self.syn=neuron.h.ExpSyn(endp.mod(0.5))
        self.syn.tau=4
        #self.rect=0
        self.w=weight
        self.tp=tp
        if tp=='excitatory' or tp=='irsensor' or tp=='visual':
            self.cl=BLUE
            self.syn.e=0.0
        elif tp=='inhibitory':
            self.cl=RED
            self.syn.e=-70.0
        self.con=neuron.h.NetCon(startp.mod(0.5)._ref_v, self.syn, 25.0, self.len*step, self.w, sec=startp.mod)


    def draw(self, screen):
        return pygame.draw.lines(screen, self.cl, False, self.points, int(self.w*20))


class AP():
    def __init__(self, axon):
        self.axon=axon
        self.pos=0
    def draw_and_advance(self):
        #oldc1=pygame.draw.circle(screen, bgcolor, [int(p) for p in self.axon.points[self.pos]], 5)
        oldc=pygame.draw.circle(screen, WHITE, [int(p) for p in self.axon.points[self.pos]], 7)
        #old_line=pygame.draw.line(screen, BLUE, [int(p) for p in self.axon.points[self.pos]], [int(pp) for pp in self.axon.points[self.pos+1]], 6)
        self.pos+=1
        newc=pygame.draw.circle(screen, self.axon.cl, [int(p) for p in self.axon.points[self.pos]], 7)
        return [oldc, newc]
    def clear(self):
        return [pygame.draw.circle(screen, WHITE, [int(p) for p in self.axon.points[self.pos]], 7)]



def getNeuronsInfo():

    neurons=[]

    for counter, neur in enumerate(all_neurons.sprites()):

        neurons+=[pickledNeuron(neur)]

    return neurons

def setNeuronsInfo(inf):
    all_neurons = pygame.sprite.Group()

    for counter, neur in enumerate(inf):
        nrn=Neuron(neur.rect.x, neur.rect.y, neur.tp, shift=False, nid=neur.nid, rf=neur.rf)
        all_neurons.add(nrn)
#rev_list=reversed(all_neurons.sprites())
    for counter, neur in enumerate(inf):

        for paxon in neur.axons:
                for counter, neur in enumerate(all_neurons.sprites()):
                    if neur.nid==paxon['start']:
                        start_nrn=neur
                    if neur.nid==paxon['end']:
                        end_nrn=neur

                start_nrn.axons.append(Axon(start_nrn, end_nrn, paxon['points'], start_nrn.tp, paxon['weight'], paxon['start'], paxon['end'], interp=False))
    return all_neurons



def ReadChannel(channel):
    adc = spi.xfer2([1,(8+channel)<<4,0])
    data = ((adc[1]&3) << 8) + adc[2]
    return data

def inter(pt1, pt2):
    ln_x=float(pt2[0])-pt1[0]
    ln_y=float(pt2[1])-pt1[1]
    ln=int(round(math.sqrt(ln_x*ln_x+ln_y*ln_y)))
    int_pts=[]
    for l in range(ln):
        int_pts+=[[pt1[0]+l*(ln_x/ln), pt1[1]+l*(ln_y/ln)]]

    return int_pts


def receptiveField():

    pixel_width=width/cam_width
    pixel_height=height/cam_height
    screen.fill(WHITE)
    selected=[]

    try:
        cam = pygame.camera.Camera(cam_dev,(width,height), 'HSV')
        cam.start()
        os.system('v4l2-ctl -d '+cam_dev+ ' --set-ctrl exposure_auto=1')
        os.system('v4l2-ctl -d '+cam_dev+ ' --set-ctrl exposure_absolute=10')
        
        camera=True
    except:
        camera=False


    #windowSurfaceObj = pygame.display.set_mode((640,480),1,16)
    #pygame.display.set_caption('Camera')
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
        if camera:
            image = cam.get_image()
            catSurfaceObj = image
            try_array=pygame.surfarray.pixels3d(image)
            try_array[:, :, 0]=try_array[:, :, 2]
            try_array[:, :, 1]=try_array[:, :, 2]
            
            scaledDown = pygame.transform.scale(catSurfaceObj, (int(cam_width), int(cam_height)))

            scaledUp = pygame.transform.scale(scaledDown, (width, height))
        else:
            scaledUp = pygame.Surface((width, height))
            scaledUp.fill(bgcolor)
        for neur in all_neurons.sprites():
            if neur.tp=='visual':
                for c in neur.rf:
                    poly_points=[[c[0]*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, (c[1]+1)*pixel_height], [c[0]*pixel_width, (c[1]+1)*pixel_height]]
                    cl=(int(255/(neur.nid+1)), 255-int(255/(neur.nid+1)), 255)
                    pygame.draw.polygon(scaledUp, cl, poly_points, 1)
        screen.blit(scaledUp,(0,0))
        for sel in selected:
            poly_points=[[sel[0]*pixel_width, sel[1]*pixel_height], [(sel[0]+1)*pixel_width, sel[1]*pixel_height], [(sel[0]+1)*pixel_width, (sel[1]+1)*pixel_height], [sel[0]*pixel_width, (sel[1]+1)*pixel_height]]
            pygame.draw.polygon(screen, RED, poly_points)
        pygame.display.update()
    if camera:
        cam.stop()
    return selected

def build_loop():

    global all_neurons

    buttons = pygame.sprite.Group()
    drawing=False;
    downflag=False;
    pts=[]
    building=1
    nid=0
    run_button=Button('run.bmp', width-80, height-50)
    buttons.add(run_button)
    exit_button=Button('exit.bmp', width-120, height-40)
    buttons.add(exit_button)
    excitatory_button=Button('pyramidal.bmp', 10, 10, 'excitatory')
    buttons.add(excitatory_button)
    inhibitory_button=Button('interneuron.bmp', 90, 10, 'inhibitory')
    buttons.add(inhibitory_button)
    visual_button=Button('visual.bmp', 180, 10, 'visual')
    buttons.add(visual_button)
    save_button=Button('save.bmp', width-100, 10)
    buttons.add(save_button)
    load_button=Button('load.bmp', width-50, 10)
    buttons.add(load_button)

    #if RPI:
    irsensor_button=Button('ir_sensor.bmp', 270, 10, 'irsensor')
    buttons.add(irsensor_button)
    rightforward_button=Button('rightforward.bmp', 360, 10, 'rightforward')
    buttons.add(rightforward_button)
    rightbackward_button=Button('rightbackward.bmp', 450, 10, 'rightbackward')
    buttons.add(rightbackward_button)
    leftforward_button=Button('leftforward.bmp', 540, 10, 'leftforward')
    buttons.add(leftforward_button)
    leftbackward_button=Button('leftbackward.bmp', 630, 10, 'leftbackward')
    buttons.add(leftbackward_button)

    focus=excitatory_button

    wightbx=eztext.Input(maxlength=6, color=BLUE,x=width-500, y=50, prompt='Synaptic weight: ')
    wightbx.value='0.1'
    wightbx.focus=True
    pygame.event.set_allowed([pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION])
    while building:


        event = pygame.event.poll()
        (x, y)=pygame.mouse.get_pos()
        if event.type == pygame.QUIT:
            return 0

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_buttons=pygame.mouse.get_pressed()
            if mouse_buttons[0]:
                downflag=True;
            if mouse_buttons[2]:
                for neur in all_neurons.sprites():
                    if neur.rect.collidepoint([x, y]):
                        for n in all_neurons.sprites():
                            to_remove=[]
                            for ax in n.axons:
                                if ax.end_id==neur.nid:
                                    del ax.con
                                    del ax.syn
                                    to_remove.append(ax)
                            for ax in to_remove:
                                n.axons.remove(ax)

                        all_neurons.remove(neur)
                        del neur

        if event.type == pygame.MOUSEMOTION:
            if downflag:
                drawing=True;
                pts=[]

                downflag=False;
                #

        if event.type == pygame.MOUSEBUTTONUP:
            if mouse_buttons[0]:
                if not drawing:

                    if run_button.rect.collidepoint([x, y]):
                        run_loop()
                    elif exit_button.rect.collidepoint([x, y]):
                        return 0
                    elif save_button.rect.collidepoint([x, y]):
                        file_path = tkFileDialog.asksaveasfilename()
                        fl=open(file_path, 'w')
                        info=getNeuronsInfo()

                        pickle.dump(info, fl)
                        fl.close()
                    elif load_button.rect.collidepoint([x, y]):
                        file_path = tkFileDialog.askopenfilename()
                        fl=open(file_path, 'r')
                        inf=pickle.load(fl)
                        all_neurons=setNeuronsInfo(inf)
                        nid=len(all_neurons.sprites())
                        fl.close()


                    elif excitatory_button.rect.collidepoint([x, y]):
                        focus=excitatory_button
                    elif inhibitory_button.rect.collidepoint([x, y]):
                        focus=inhibitory_button
                    elif visual_button.rect.collidepoint([x, y]):
                        focus=visual_button


#                    if RPI:
                    if rightforward_button.rect.collidepoint([x, y]):
                        focus=rightforward_button
                    elif rightbackward_button.rect.collidepoint([x, y]):
                        focus=rightbackward_button
                    elif leftforward_button.rect.collidepoint([x, y]):
                        focus=leftforward_button
                    elif leftbackward_button.rect.collidepoint([x, y]):
                        focus=leftbackward_button
                    elif irsensor_button.rect.collidepoint([x, y]):
                        focus=irsensor_button

                    if y>150 and y<height-100:
                        on_neuron=False
                        for counter, neur in enumerate(all_neurons.sprites()):
                            if neur.rect.collidepoint([x, y]):
                                on_neuron=True

                        if not on_neuron:
                            all_neurons.add(Neuron(x, y, focus.tp, nid=nid))
                            nid+=1




                else:
                    axon_start=False
                    axon_end=False
                    for counter, neur in enumerate(all_neurons.sprites()):
                        if neur.rect.collidepoint(pts[0]) and not neur.super_type=='motor':
                            start_nrn=counter
                            axon_start=True;
                        if neur.rect.collidepoint(pts[len(pts)-1]):
                            end_nrn=counter
                            axon_end=True;

                    if (axon_start and axon_end):
                        tp=all_neurons.sprites()[start_nrn].tp
                        w=float(wightbx.value)
                        start_id=all_neurons.sprites()[start_nrn].nid
                        end_id=all_neurons.sprites()[end_nrn].nid
                        all_neurons.sprites()[start_nrn].axons.append(Axon(all_neurons.sprites()[start_nrn], all_neurons.sprites()[end_nrn], pts, tp, w, start_id, end_id))

                    pts=[]
                    drawing=False;


                downflag=False;

        if drawing:

            pts=pts+[[x, y]]

        screen.fill(bgcolor)
        all_neurons.draw(screen)
        for neur in all_neurons.sprites():
            neur.drawAxons()
        buttons.draw(screen)
        wightbx.update(event)
        wightbx.draw(screen)
        pygame.draw.rect(screen, RED, focus.rect, 2)


        #for ax in axons:
        #    ax.draw(screen)

        if len(pts)>1:
            pygame.draw.lines(screen, BLACK, False, pts, 5)
        #for i in range(len(xx)-1):
        #    pygame.draw.line(screen, (200, 200, 200), (xx[i], yy[i]), (xx[i+1], yy[i+1]))



        pygame.display.flip()

def run_loop():

    global motors
    
    if motors:
        forward_left=17
        backward_left=18
        forward_right=23
        backward_right=22

        io.setup(forward_left, io.OUT)
        io.setup(backward_left, io.OUT)
        io.setup(forward_right, io.OUT)
        io.setup(backward_right, io.OUT)

        forward_left_pwm=io.PWM(forward_left, 500)
        backward_left_pwm=io.PWM(backward_left, 500)
        forward_right_pwm=io.PWM(forward_right, 500)
        backward_right_pwm=io.PWM(backward_right, 500)

        forward_left_pwm.start(0)
        backward_left_pwm.start(0)
        forward_right_pwm.start(0)
        backward_right_pwm.start(0)

    if visuals:
        cam = pygame.camera.Camera(cam_dev,(width,height), 'HSV')
        cam.start()
        os.system('v4l2-ctl -d '+cam_dev+ ' --set-ctrl exposure_auto=1')

    sensors_init=0
    vmin=-75.
    vmax=-40.
    plot_len=400
    plot_height=100
    fire_image_delay=100
    running=1
    plot_count=0
    visual_count=0
    buttons = pygame.sprite.Group()
    downflag=False;
    stop_button=pygame.sprite.Sprite()
    stop_button.image=pygame.image.load("stop.bmp").convert()
    stop_button.rect=stop_button.image.get_rect()
    stop_button.rect.x=width-stop_button.rect.width
    stop_button.rect.y=height-stop_button.rect.height
    buttons.add(stop_button)
    pipette=pygame.sprite.Sprite()
    pipette.image=pygame.image.load("pipette.bmp").convert()
    pipette.rect=pipette.image.get_rect()
    buttons.add(pipette)

    #firing_neuron_image=pygame.image.load("firing_neuron.bmp").convert()
    #firing_neuron_image.set_colorkey(WHITE)
    #neuron_image=pygame.image.load("neuron.bmp").convert()
    #neuron_image.set_colorkey(WHITE)
    plt=pygame.Surface((plot_len, plot_height))

    APs=[]
    recv=[]
    recording=False

    for counter, neur in enumerate(all_neurons.sprites()):
        recv+=[neuron.h.Vector()]
        recv[counter].record(neur.mod(0.5)._ref_v)

    #v1=neuron.h.Vector()
    #v1.record(all_neurons.sprites()[0].mod(0.5)._ref_v)
    #v2=neuron.h.Vector()
    #v2.record(all_neurons.sprites()[1].mod(0.5)._ref_v)


    neuron.h.finitialize(-60)
    neuron.run(plot_len)
    v=np.ones(plot_len)*-60
    t=neuron.h.t

    screen.fill(bgcolor)
    all_neurons.draw(screen)
    buttons.draw(screen)
    for neur in all_neurons.sprites():
        neur.drawAxons()

    pygame.display.flip()
    pixel_width=cam_scale
    pixel_height=cam_scale
    my_array=np.zeros((cam_width, cam_height))
    while running:
        plot_count+=1
        if sensors_init<500:
		sensors_init+=1

        right_power=0.
        left_power=0.

        if visuals:
            if plot_count==downSampleFactor:
                catSurfaceObj = cam.get_image()
                scaledDown = pygame.transform.scale(catSurfaceObj, (int(cam_width), int(cam_height)))
                pixArray=pygame.surfarray.pixels3d(scaledDown)

                pixArray[:, :, 0]=pixArray[:, :, 2]
                pixArray[:, :, 1]=pixArray[:, :, 2]
                my_array=copy.deepcopy(pixArray[:,:,2])
                del pixArray
                scaledUp = pygame.transform.scale(scaledDown, (int(cam_width*cam_scale), int(cam_height*cam_scale)))

                pygame.draw.rect(scaledUp, BLACK, scaledUp.get_rect(), 1)
                for neur in all_neurons.sprites():
                    if neur.tp=='visual':
                        for c in neur.rf:
                            poly_points=[[c[0]*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, c[1]*pixel_height], [(c[0]+1)*pixel_width, (c[1]+1)*pixel_height], [c[0]*pixel_width, (c[1]+1)*pixel_height]]
                            cl=(int(255/(neur.nid+1)), 255-int(255/(neur.nid+1)), 255)
                            pygame.draw.polygon(scaledUp, cl, poly_points, 1)
                            pygame.draw.rect(screen, cl, neur.rect, 1)

                screen.blit(scaledUp, (width-(cam_width*cam_scale+10), height-(cam_width*cam_scale+50)))
                #visual_count+=1
            #visual_count+=1
            #if visual_count==visualDownSample+1:
             #   visual_count=0

        for counter, neur in enumerate(all_neurons.sprites()):

            try:
                max_v=np.max(np.array(recv[counter]))
            except:
            	max_v=0.



            if neur.tp=='irsensor' and sensors_init==500:
                ir_range=ReadChannel(0)
                neur.ir_stm=neuron.h.IClamp(neur.mod(0.5))
                neur.ir_stm.delay=neuron.h.t
                neur.ir_stm.dur=step
                neur.ir_stm.amp=ir_range/ir_conversion

            if neur.tp=='visual':
                neur.ir_stm=neuron.h.IClamp(neur.mod(0.5))
                neur.ir_stm.delay=neuron.h.t
                neur.ir_stm.dur=step
                vamp=0

                for c in neur.rf:
                    vamp+=my_array[c[0], c[1]]
                vamp/=len(neur.rf)
                neur.ir_stm.amp=vamp/visual_conversion


            if neur.super_type=='motor':
                try:
                    mean_v=20*(70+np.mean(np.array(recv[counter])))
                except:
                    mean_v=0.

                if neur.tp=='rightforward':
                    right_power+=mean_v
                elif neur.tp=='rightbackward':
                    right_power-=mean_v
                elif neur.tp=='leftforward':
                    left_power+=mean_v
                elif neur.tp=='leftbackward':
                    left_power-=mean_v

            if not neur.super_type=='motor' and max_v>10.0: #and neur.fire_counter==0:
                #neur.fire_counter=fire_image_delay
                #neur.image=firing_neuron_image
                #dirty_recs.append(neur.rect)
                if recording:                
                    if sound_card and neur==rec_neuron:
                        spike_sound.play()
                for ax in neur.axons:
                    APs.append(AP(ax))

            if neur.fire_counter>0:

                #neur.image=firing_neuron_image
                neur.fire_counter-=1
                #if neur.fire_counter==0:
                #    neur.image=neuron_image
                    #dirty_recs.append(neur.rect)

        if motors:
            if abs(left_power)>0.00001:
                if left_power>0:
                    if left_power>100:
                        left_power=100
                    backward_left_pwm.ChangeDutyCycle(0)			
                    forward_left_pwm.ChangeDutyCycle(int(left_power))
                else:
                    if left_power<-100:
                        left_power=-100
                    forward_left_pwm.ChangeDutyCycle(0)
                    backward_left_pwm.ChangeDutyCycle(-int(left_power))
            else:
                forward_left_pwm.ChangeDutyCycle(0)
                backward_right_pwm.ChangeDutyCycle(0)

            if abs(right_power)>0.00001:
                if right_power>0:
                    if right_power>100:
                        right_power=100
                    backward_right_pwm.ChangeDutyCycle(0)
                    forward_right_pwm.ChangeDutyCycle(int(right_power))
                else:
                    if right_power<-100:
                        right_power=-100
                    forward_right_pwm.ChangeDutyCycle(0)
                    backward_right_pwm.ChangeDutyCycle(-int(right_power))
            else:
                forward_right_pwm.ChangeDutyCycle(0)
                backward_right_pwm.ChangeDutyCycle(0)

        event = pygame.event.poll()
        (x, y)=pygame.mouse.get_pos()
        if event.type == pygame.QUIT:
            if visuals:
                cam.stop()
            return 0

        if event.type == pygame.MOUSEBUTTONDOWN:
            downflag=True;
            mouse_buttons=pygame.mouse.get_pressed()
        if event.type == pygame.MOUSEMOTION:
            if downflag:

                downflag=False;
                #

        if event.type == pygame.MOUSEBUTTONUP:


            if stop_button.rect.collidepoint([x, y]):

                if visuals:
                    cam.stop()
                return 0
            for counter, neur in enumerate(all_neurons.sprites()):
                if neur.rect.collidepoint([x, y]):
                    if mouse_buttons[0]:
                        stm=neuron.h.IClamp(neur.mod(0.5))
                        stm.delay=neuron.h.t#+step
                        stm.dur=10
                        stm.amp=10
                    if mouse_buttons[2]:
                        rec_neuron=neur
                        pygame.draw.rect(screen, bgcolor, pipette.rect)
                        pipette.rect.x=x
                        pipette.rect.y=y
                        buttons.draw(screen)
                        recording=True


            downflag=False;

        #neuron.run(t)

        #t+=1



        for counter, neur in enumerate(all_neurons.sprites()):
            #dirty_recs+=neur.drawAxons()
            #dirty_recs.append(neur.rect)
            recv[counter].resize(0)

        for ap in APs:
            #dirty_recs+=
            ap.draw_and_advance()
            if ap.pos==(ap.axon.len-1):
                #dirty_recs+=ap.clear()
                ap.clear()
                APs.remove(ap)


        neuron.run(t)
        t+=step
#        if plot_count==downSampleFactor:
#            v=np.append(v[1::], [np.array(all_neurons.sprites()[0].mod(0.5).v)])
        

        if plot_count==downSampleFactor:
            plot_count=0
            if recording:
                v=np.append(v[1::], [np.array(rec_neuron.mod(0.5).v)])
                #vmax=np.max(v)
                #vmin=np.min(v)-1

                v_scaled=plot_height-(plot_height)*(v-vmin)/(vmax-vmin)
                v_scaled[(v_scaled<0)]=0

                plist=np.vstack((np.array(range(plot_len)), v_scaled))

                plt.fill(bgcolor)
                pygame.draw.lines(plt, BLUE, False, np.transpose(plist))
                screen.blit(plt, (100, 10))

            all_neurons.draw(screen)
            for counter, neur in enumerate(all_neurons.sprites()):
                neur.drawAxons()
            pygame.display.update()

        #dirty_recs=[]



pygame.init()
dispinf=pygame.display.Info()


width=dispinf.current_w-200
height=dispinf.current_h-200

if width>1300:
    width=1300
if height>710:
    height=710

    
root = tk.Tk()
root.withdraw()

neuron.h.load_file("stdrun.hoc")

y = 0
dir = 1
running = 1

screen = pygame.display.set_mode((width, height))
bgcolor = WHITE

screen.fill(WHITE)
#pr = cProfile.Profile()
#pr.enable()

build_loop()

#pr.disable()
#s = StringIO.StringIO()
#sortby = 'cumulative'
#ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
#ps.print_stats()
#print s.getvalue()
if RPI:
    io.cleanup()
pygame.quit()
