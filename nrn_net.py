import pygame
import pygame.camera
import math
import pickle
import neuron
import Tkinter as tk
import tkFileDialog
import tkSimpleDialog
import numpy as np
from time import sleep
import eztext
import alsaaudio
import struct
import thread

from camera_module import Camera, receptiveField

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
    downSampleFactor=10.

BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED   = (255,   0,   0)
BLUE  = (0,   0,   255)
BGCOLOR = WHITE


step=0.1
audio_bin=4000
stdp_max=5000

try:
    pygame.mixer.init()
    spike_sound=pygame.mixer.Sound("spike.wav")
    sound_card=True
except:
    sound_card=False



ir_conversion=50.
visual_conversion=7.
auditory_conversion=100000.
motors=False
sensors=False
visuals=False
auditories=False


freqs=np.zeros(audio_bin)
first_image=False

shut_down=False


class Mic(object):
    def __init__(self):
        try:
            self.inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, u'plughw:CARD=C170,DEV=0')
            self.inp.setchannels(1)
            self.inp.setrate(44100)
            self.inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            self.inp.setperiodsize(audio_bin)
            self.online=True
            print 'Mic detected'
        except:
            self.online=False
            
            
class sensors(object):
    def __init__(self):
        self.cam = Camera("/dev/video0", 32, 24, 8)
        self.mic = Mic()
        
        
class Neuron(pygame.sprite.Sprite):
    def __init__(self, x, y, tp, brn, shift=True, nid=None, rf=None, freq=None):
        global motors, sensors, visuals, auditories
        super(Neuron, self).__init__()
        self.screen = brn.screen
        
        self.rf=0
        self.freq=None
        self.stdp=0
        
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
            self.ext_stm=0
            self.super_type='sensor'
            sensors=True
        elif tp=='auditory':
            self.ext_stm=0
            self.image = pygame.image.load("auditory.bmp").convert()
            self.auditory_stm=0
            self.super_type='sensor'
            auditories=True
            if freq==None:
                self.freq=int(tkSimpleDialog.askstring('Auditory cell', 'Frequency (Hz): '))
            else:
                self.freq=freq

        elif tp=='visual':
            self.ext_stm=0
            self.image = pygame.image.load("visual.bmp").convert()
            self.visual_stm=0
            self.super_type='sensor'
            visuals=True
            if rf==None:
                self.rf=receptiveField(brn)
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
            recs.append(axon.draw(self.screen))
        return recs

    def pickledAxons(self):
        paxons=[]
        for axon in self.axons:
            paxons+=[{'points':axon.points, 'weight':axon.w, 'start':axon.start_id, 'end':axon.end_id}]
        return paxons


   


        
class pickledNeuron(object):
    def __init__(self, nrn):
        self.rect=nrn.rect
        self.tp=nrn.tp
        self.super_type=nrn.super_type
        self.nid=nrn.nid
        self.rf=nrn.rf
        self.freq=nrn.freq
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

class Axon(object):
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
        self.w=weight
        self.tp=tp
        if tp=='excitatory' or tp=='irsensor' or tp=='visual' or tp=='auditory':
            self.syn.tau=4
            self.cl=BLUE
            self.syn.e=0.0
        elif tp=='inhibitory':
            self.syn.tau=20
            self.cl=RED
            self.syn.e=-90.0
        self.con=neuron.h.NetCon(startp.mod(0.5)._ref_v, self.syn, 25.0, self.len*step, self.w, sec=startp.mod)


    def draw(self, screen):
        return pygame.draw.lines(screen, self.cl, False, self.points, int(self.w*20))


class AP(object):
    def __init__(self, axon, screen):
        self.axon=axon
        self.pos=0
        self.old_pos=0
        self.screen=screen


    def draw_and_advance(self, to_draw):
        self.pos+=1
        if to_draw:
		oldc=pygame.draw.circle(self.screen, BGCOLOR, map(int, self.axon.points[self.old_pos]), 7)

        	newc=pygame.draw.circle(self.screen, self.axon.cl, map(int, self.axon.points[self.pos]), 7)
		self.old_pos=self.pos
        	return [oldc, newc]
        else:
             return []

    def clear(self):
        return [pygame.draw.circle(self.screen, WHITE, [int(p) for p in self.axon.points[self.old_pos]], 7)]



def getNeuronsInfo():

    neurons=[]

    for counter, neur in enumerate(all_neurons.sprites()):

        neurons+=[pickledNeuron(neur)]

    return neurons

def setNeuronsInfo(inf):
    all_neurons = pygame.sprite.Group()

    for counter, neur in enumerate(inf):
        nrn=Neuron(neur.rect.x, neur.rect.y, neur.tp, shift=False, nid=neur.nid, rf=neur.rf, freq=neur.freq)
        all_neurons.add(nrn)
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




def get_audio_freqs():

    global shut_down, freqs

    while not shut_down:
        l, a=inp.read()
        if not l==-32:	
            freqs = np.abs(np.fft.fft(struct.unpack('<'+str(audio_bin)+'h', a)))




class brain(object):
    def __init__(self):
        pygame.init()
        dispinf=pygame.display.Info()
        self.width=dispinf.current_w-200
        self.height=dispinf.current_h-50
    
        if self.width>1300:
            self.width=1300
        if self.height>710:
            self.height=710
    
        self.tkroot = tk.Tk()
        self.tkroot.withdraw()
    
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.screen.fill(BGCOLOR)
        
        neuron.h.load_file("stdrun.hoc")
        self.neurons = pygame.sprite.Group()
        self.sns=sensors()
        
    def __del__(self):
        print "brain object deleted"
        
    def stop_rec(self):
        if visuals:
            self.sns.cam.shut_down=True
            sleep(0.3)
            self.sns.cam.shut_down=False
            
    def build_loop(self):
    
        #global all_neurons
    
        buttons = pygame.sprite.Group()
        drawing=False;
        downflag=False;
        pts=[]
        building=True
        nid=0
        run_button=Button('run.bmp', self.width-80, self.height-50)
        buttons.add(run_button)
        exit_button=Button('exit.bmp', self.width-120, self.height-40)
        buttons.add(exit_button)
        excitatory_button=Button('pyramidal.bmp', 10, 10, 'excitatory')
        buttons.add(excitatory_button)
        inhibitory_button=Button('interneuron.bmp', 80, 10, 'inhibitory')
        buttons.add(inhibitory_button)
        visual_button=Button('visual.bmp', 150, 10, 'visual')
        buttons.add(visual_button)
        auditory_button=Button('auditory.bmp', 220, 10, 'auditory')
        buttons.add(auditory_button)
        save_button=Button('save.bmp', self.width-100, 10)
        buttons.add(save_button)
        load_button=Button('load.bmp', self.width-50, 10)
        buttons.add(load_button)
    
        #if RPI:
        irsensor_button=Button('ir_sensor.bmp', 290, 10, 'irsensor')
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
    
        wightbx=eztext.Input(maxlength=6, color=BLUE,x=self.width-500, y=50, prompt='Synaptic weight: ')
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
                    for neur in self.neurons.sprites():
                        if neur.rect.collidepoint([x, y]):
                            for n in self.neurons.sprites():
                                to_remove=[]
                                for ax in n.axons:
                                    if ax.end_id==neur.nid:
                                        del ax.con
                                        del ax.syn
                                        to_remove.append(ax)
                                for ax in to_remove:
                                    n.axons.remove(ax)
    
                            self.neurons.remove(neur)
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
                            self.run_loop()
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
                            self.neurons=setNeuronsInfo(inf)
                            nid=len(self.neurons.sprites())
                            fl.close()
    
    
                        elif excitatory_button.rect.collidepoint([x, y]):
                            focus=excitatory_button
                        elif inhibitory_button.rect.collidepoint([x, y]):
                            focus=inhibitory_button
                        elif visual_button.rect.collidepoint([x, y]):
                            focus=visual_button
                        elif auditory_button.rect.collidepoint([x, y]):
                            focus=auditory_button
    
    
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
    
                        if y>150 and y<self.height-100:
                            on_neuron=False
                            for counter, neur in enumerate(self.neurons.sprites()):
                                if neur.rect.collidepoint([x, y]):
                                    on_neuron=True
    
                            if not on_neuron:
                                self.neurons.add(Neuron(x, y, focus.tp, self, nid=nid))
                                nid+=1
    
    
    
    
                    else:
                        axon_start=False
                        axon_end=False
                        for counter, neur in enumerate(self.neurons.sprites()):
                            if neur.rect.collidepoint(pts[0]) and not neur.super_type=='motor':
                                start_nrn=counter
                                axon_start=True;
                            if neur.rect.collidepoint(pts[len(pts)-1]):
                                end_nrn=counter
                                axon_end=True;
    
                        if (axon_start and axon_end):
                            tp=self.neurons.sprites()[start_nrn].tp
                            w=float(wightbx.value)
                            start_id=self.neurons.sprites()[start_nrn].nid
                            end_id=self.neurons.sprites()[end_nrn].nid
                            self.neurons.sprites()[start_nrn].axons.append(Axon(self.neurons.sprites()[start_nrn], self.neurons.sprites()[end_nrn], pts, tp, w, start_id, end_id))
    
                        pts=[]
                        drawing=False;
    
    
                    downflag=False;
    
            if drawing:
    
                pts=pts+[[x, y]]
    
            self.screen.fill(BGCOLOR)
            self.neurons.draw(self.screen)
            for neur in self.neurons.sprites():
                neur.drawAxons()
            buttons.draw(self.screen)
            wightbx.update(event)
            wightbx.draw(self.screen)
            pygame.draw.rect(self.screen, RED, focus.rect, 2)
    
    
            #for ax in axons:
            #    ax.draw(screen)
    
            if len(pts)>1:
                pygame.draw.lines(self.screen, BLACK, False, pts, 5)
            #for i in range(len(xx)-1):
            #    pygame.draw.line(screen, (200, 200, 200), (xx[i], yy[i]), (xx[i+1], yy[i+1]))
    
    
    
            pygame.display.flip()
    
    def run_loop(self):
    
        global motors, shut_down
    
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
            thread.start_new_thread(self.sns.cam.update_buffer, (self.neurons.sprites(),))
        if auditories:
            thread.start_new_thread(get_audio_freqs, ())
    
        sensors_init=0
        vmin=-75.
        vmax=-40.
        plot_len=400
        plot_height=100
        fire_image_delay=10
        running=1
        plot_count=0
        buttons = pygame.sprite.Group()
        downflag=False;
        stop_button=pygame.sprite.Sprite()
        stop_button.image=pygame.image.load("stop.bmp").convert()
        stop_button.rect=stop_button.image.get_rect()
        stop_button.rect.x=self.width-stop_button.rect.width
        stop_button.rect.y=self.height-stop_button.rect.height
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
    
        for counter, neur in enumerate(self.neurons.sprites()):
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
    
        self.screen.fill(BGCOLOR)
        self.neurons.draw(self.screen)
        buttons.draw(self.screen)
        for neur in self.neurons.sprites():
            neur.drawAxons()
    
        pygame.display.flip()
    
        while running:
            plot_count+=1
            if sensors_init<500:
    		sensors_init+=1
    
            right_power=0.
            left_power=0.
    
    
            for counter, neur in enumerate(self.neurons.sprites()):
    
                try:
                    max_v=recv[counter].max()
                except:
                	max_v=0.
    
    
    
                if neur.tp=='irsensor' and sensors_init==500:
                    ir_range=ReadChannel(0)
                    neur.ext_stm=neuron.h.IClamp(neur.mod(0.5))
                    neur.ext_stm.delay=neuron.h.t
                    neur.ext_stm.dur=step
                    neur.ext_stm.amp=ir_range/ir_conversion
    
                if neur.tp=='visual':
                    neur.ext_stm=neuron.h.IClamp(neur.mod(0.5))
                    neur.ext_stm.delay=neuron.h.t
                    neur.ext_stm.dur=step
                    vamp=0
    
                    for c in neur.rf:
                        vamp+=self.sns.cam.img_buffer[c[0], c[1]]
                    vamp/=len(neur.rf)
                    neur.ext_stm.amp=vamp/visual_conversion
    
    
                if neur.tp=='auditory':
                    ind=int(round((neur.freq-1)*(audio_bin/44100.)))
                    fval=freqs[ind]
                    if fval>500000:
                        neur.ext_stm=neuron.h.IClamp(neur.mod(0.5))
                        neur.ext_stm.delay=neuron.h.t
                        neur.ext_stm.dur=step
                        neur.ext_stm.amp=(fval-500000)/auditory_conversion
    
                if neur.super_type=='motor':
                    try:
                        mean_v=20*(70+np.mean(np.array(recv[counter])))
                        if mean_v<0:
                            mean_v=0
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
    
                if neur.stdp>0:
                    neur.stdp-=1
    
                if not neur.super_type=='motor' and max_v>25.0:
                    neur.stdp=stdp_max
                    for n in self.neurons.sprites():
                        for ax in n.axons:
                            if ax.end_id==neur.nid:
                                if n.stdp>0:
                                    ax.w+=(0.2-ax.w)*0.01
                                else:
                                    ax.w-=(ax.w-0.01)*0.01
    
                                ax.con.weight[0]=ax.w
    
    
                    if neur.fire_counter==0:
                        neur.fire_counter=fire_image_delay
                        #neur.image=firing_neuron_image
                        #dirty_recs.append(neur.rect)
                        if recording:
                            if sound_card and neur==rec_neuron:
                                spike_sound.play()
                        for ax in neur.axons:
        			
                            APs.append(AP(ax, self.screen))
    
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
                self.stop_rec()

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
                    self.stop_rec()

                    return 0
                for counter, neur in enumerate(self.neurons.sprites()):
                    if neur.rect.collidepoint([x, y]):
                        if mouse_buttons[0]:
                            stm=neuron.h.IClamp(neur.mod(0.5))
                            stm.delay=neuron.h.t#+step
                            stm.dur=10
                            stm.amp=10
                        if mouse_buttons[2]:
                            rec_neuron=neur
                            pygame.draw.rect(self.screen, BGCOLOR, pipette.rect)
                            pipette.rect.x=x
                            pipette.rect.y=y
                            buttons.draw(self.screen)
                            recording=True
    
    
                downflag=False;
    
            #neuron.run(t)
    
            #t+=1
    
    
    
            for counter, neur in enumerate(self.neurons.sprites()):
                #dirty_recs+=neur.drawAxons()
                #dirty_recs.append(neur.rect)
                recv[counter].resize(0)
    
        	to_draw=plot_count==downSampleFactor
    
            for ap in APs:
                #dirty_recs+=
                ap.draw_and_advance(to_draw)
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
    
    
                    v_scaled=plot_height-(plot_height)*(v-vmin)/(vmax-vmin)
                    v_scaled[(v_scaled<0)]=0
    
                    plist=np.vstack((np.array(range(plot_len)), v_scaled))
    
                    plt.fill(BGCOLOR)
                    pygame.draw.lines(plt, BLUE, False, np.transpose(plist))
                    self.screen.blit(plt, (100, 10))
    
                self.neurons.draw(self.screen)
                for counter, neur in enumerate(self.neurons.sprites()):
                    neur.drawAxons()
                if visuals and self.sns.cam.first_image:
                    self.screen.blit(self.sns.cam.cam_icon, (self.width-(self.sns.cam.width*self.sns.cam.scale+10), self.height-(self.sns.cam.width*self.sns.cam.scale+50)))
                pygame.display.update()
    
            #dirty_recs=[]


def main():
    

    #pygame.init()
#    dispinf=pygame.display.Info()
#    width=dispinf.current_w-200
#    height=dispinf.current_h-50
#    
#    if width>1300:
#        width=1300
#    if height>710:
#        height=710
#    
#    root = tk.Tk()
#    root.withdraw()
#    
#    neuron.h.load_file("stdrun.hoc")
#    
#   
#    screen = pygame.display.set_mode((width, height))
#    screen.fill(BGCOLOR)

    brn=brain()
    brn.build_loop()
    
    if RPI:
        io.cleanup()
    pygame.quit()

if __name__ == "__main__":
    main()