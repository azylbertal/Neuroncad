import pygame
import math
import neuron
#import matplotlib.pyplot as plt
import numpy as np
import cProfile, pstats, StringIO
from time import sleep
import eztext

try:
    import RPi.GPIO as io
    import spidev
    RPI=True
    
except:
    RPI=False
            
if RPI:
    io.setmode(io.BCM)
    spi=spidev.SpiDev()
    spi.open(0,0)
    
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED   = (255,   0,   0)
BLUE  = (0,   0,   255)
width = 1024
height = 768

step=0.1


ir_conversion=50.
motors=False
sensors=False


class Neuron(pygame.sprite.Sprite):
    def __init__(self, x, y, tp):
        global motors, sensors
        super(Neuron, self).__init__()  
        if tp=='excitatory':        
            self.image = pygame.image.load("pyramidal.bmp").convert()
            self.super_type='neuron'
        elif tp=='inhibitory':        
            self.image = pygame.image.load("interneuron.bmp").convert()
            self.super_type='neuron'
        elif tp=='rightclockwise':
            self.image = pygame.image.load("right_clockwise.bmp").convert()
            self.super_type='motor'
        elif tp=='rightanticlockwise':        
            self.image = pygame.image.load("right_anticlockwise.bmp").convert()
            self.super_type='motor'
        elif tp=='leftclockwise':        
            self.image = pygame.image.load("left_clockwise.bmp").convert()
            self.super_type='motor'
        elif tp=='leftanticlockwise':        
            self.image = pygame.image.load("left_anticlockwise.bmp").convert()
            self.super_type='motor'
        elif tp=='irsensor':
            self.image = pygame.image.load("ir_sensor.bmp").convert()
	    self.ir_stm=0
            self.super_type='sensor'

        self.tp=tp
        self.image.set_colorkey(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x=x-self.rect.width/2
        self.rect.y=y-self.rect.height/2
        self.mod=neuron.h.Section()
        if self.super_type=='neuron' or self.super_type=='sensor':        
            self.mod.insert('hh')
            sensors=True
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
    def __init__(self, startp, endp, points):
        
        #self.startp=startp
        self.endp=endp
        self.points=[]
        for p in range(len(points)-1):
            self.points+=inter(points[p], points[p+1])
        self.len=len(self.points)
        self.syn=neuron.h.ExpSyn(endp.mod(0.5))
        self.syn.tau=4
        self.w=0.5
        
        self.con=neuron.h.NetCon(startp.mod(0.5)._ref_v, self.syn, 25.0, self.len*step, self.w, sec=startp.mod)
                
    
    def draw(self, screen):
        return pygame.draw.lines(screen, BLUE, False, self.points, 8)


class AP():
    def __init__(self, axon):
        self.axon=axon
        self.pos=0
    def draw_and_advance(self):
        #oldc1=pygame.draw.circle(screen, bgcolor, [int(p) for p in self.axon.points[self.pos]], 5)        
        oldc=pygame.draw.circle(screen, BLUE, [int(p) for p in self.axon.points[self.pos]], 3)
        #old_line=pygame.draw.line(screen, BLUE, [int(p) for p in self.axon.points[self.pos]], [int(pp) for pp in self.axon.points[self.pos+1]], 6)
        self.pos+=1
        newc=pygame.draw.circle(screen, WHITE, [int(p) for p in self.axon.points[self.pos]], 3)
        return [oldc, newc]
       
        
        
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


def build_loop():

    all_neurons = pygame.sprite.Group()
    buttons = pygame.sprite.Group()
    drawing=False;
    downflag=False;
    pts=[]
    building=1

    run_button=Button('run.bmp', width-80, height-50)
    buttons.add(run_button)
    exit_button=Button('exit.bmp', width-120, height-40)
    buttons.add(exit_button)
    excitatory_button=Button('pyramidal.bmp', 10, 10, 'excitatory')
    buttons.add(excitatory_button)
    inhibitory_button=Button('interneuron.bmp', 90, 10, 'inhibitory')
    buttons.add(inhibitory_button)
    if RPI:
        rightclockwise_button=Button('right_clockwise.bmp', 180, 10, 'rightclockwise')
        buttons.add(rightclockwise_button)
        rightanticlockwise_button=Button('right_anticlockwise.bmp', 270, 10, 'rightanticlockwise')
        buttons.add(rightanticlockwise_button)
        leftclockwise_button=Button('left_clockwise.bmp', 360, 10, 'leftclockwise')
        buttons.add(leftclockwise_button)
        leftanticlockwise_button=Button('left_anticlockwise.bmp', 450, 10, 'leftanticlockwise')
        buttons.add(leftanticlockwise_button)
    
    irsensor_button=Button('ir_sensor.bmp', 540, 10, 'irsensor')
    buttons.add(irsensor_button)
    
    focus=excitatory_button
    
    txtbx=eztext.Input(maxlength=6, color=BLUE,y=100, prompt='type here ')
    txtbx.focus=True
    
    while building:
        
        
        event = pygame.event.poll()
        (x, y)=pygame.mouse.get_pos()    
        if event.type == pygame.QUIT:
            return 0
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            downflag=True;
        if event.type == pygame.MOUSEMOTION:
            if downflag:
                drawing=True;
                pts=[]
                
                downflag=False;
                #
    
        if event.type == pygame.MOUSEBUTTONUP:
                
            if not drawing:
                
                if run_button.rect.collidepoint([x, y]):
                    run_loop(all_neurons)
                elif exit_button.rect.collidepoint([x, y]):
                    return 0
                elif excitatory_button.rect.collidepoint([x, y]):
                    focus=excitatory_button
                elif inhibitory_button.rect.collidepoint([x, y]):
                    focus=inhibitory_button
                elif irsensor_button.rect.collidepoint([x, y]):
                    focus=irsensor_button

                if RPI:
                    if rightclockwise_button.rect.collidepoint([x, y]):
                        focus=rightclockwise_button
                    elif rightanticlockwise_button.rect.collidepoint([x, y]):
                        focus=rightanticlockwise_button
                    elif leftclockwise_button.rect.collidepoint([x, y]):
                        focus=leftclockwise_button
                    elif leftanticlockwise_button.rect.collidepoint([x, y]):
                        focus=leftanticlockwise_button

                if y>150 and y<height-100:
                    all_neurons.add(Neuron(x, y, focus.tp))                    
            
                
                
    
            else:
                axon_start=False
                axon_end=False
                for counter, neur in enumerate(all_neurons.sprites()):
                    if neur.rect.collidepoint(pts[0]):
                        start_nrn=counter
                        axon_start=True;
                    if neur.rect.collidepoint(pts[len(pts)-1]):
                        end_nrn=counter
                        axon_end=True;
                
                if (axon_start and axon_end):
                    all_neurons.sprites()[start_nrn].axons.append(Axon(all_neurons.sprites()[start_nrn], all_neurons.sprites()[end_nrn], pts))   
                    
                
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
        txtbx.update(event)
        txtbx.draw(screen)
        pygame.draw.rect(screen, RED, focus.rect, 2)
        
        
        #for ax in axons:
        #    ax.draw(screen)
            
        if len(pts)>1:
            pygame.draw.lines(screen, BLACK, False, pts, 5)
        #for i in range(len(xx)-1):
        #    pygame.draw.line(screen, (200, 200, 200), (xx[i], yy[i]), (xx[i+1], yy[i+1]))
            
    
    
        pygame.display.flip()
        
def run_loop(all_neurons):
    
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

    sensors_init=0        
    vmin=-70.
    vmax=80.   
    plot_len=300    
    fire_image_delay=100
    running=1
    plot_count=0
    buttons = pygame.sprite.Group()
    downflag=False;
    stop_button=pygame.sprite.Sprite()
    stop_button.image=pygame.image.load("stop.bmp").convert()
    stop_button.rect=stop_button.image.get_rect()
    stop_button.rect.x=width-stop_button.rect.width
    stop_button.rect.y=height-stop_button.rect.height
    buttons.add(stop_button)

    #firing_neuron_image=pygame.image.load("firing_neuron.bmp").convert()
    #firing_neuron_image.set_colorkey(WHITE)
    #neuron_image=pygame.image.load("neuron.bmp").convert()
    #neuron_image.set_colorkey(WHITE)
    plt=pygame.Surface((plot_len, 50))    
    
    APs=[]
    recv=[]
    dirty_recs=[]
    
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
    while running:
        
	if sensors_init<500:
		sensors_init+=1
       
        right_power=0.
        left_power=0.

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
                
            if neur.super_type=='motor':
                try:
                    mean_v=2*(70+np.mean(np.array(recv[counter])))
                except:
                    mean_v=0.
                    
                if neur.tp=='rightclockwise':
                    right_power+=mean_v
                elif neur.tp=='rightanticlockwise':
                    right_power-=mean_v
                elif neur.tp=='leftclockwise':
                    left_power+=mean_v
                elif neur.tp=='leftanticlockwise':
                    left_power-=mean_v
            
            if not neur.super_type=='motor' and max_v>25.0 and neur.fire_counter==0:
                neur.fire_counter=fire_image_delay
                #neur.image=firing_neuron_image
                #dirty_recs.append(neur.rect)
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
                    backward_left_pwm.ChangeDutyCycle(0)			
                    forward_left_pwm.ChangeDutyCycle(int(left_power))
                else:
                    forward_left_pwm.ChangeDutyCycle(0)
                    backward_left_pwm.ChangeDutyCycle(-int(left_power))
            else:
                forward_left_pwm.ChangeDutyCycle(0)
                backward_right_pwm.ChangeDutyCycle(0)
    
            if abs(right_power)>0.00001:
                if right_power>0:
                    backward_right_pwm.ChangeDutyCycle(0)
                    forward_right_pwm.ChangeDutyCycle(int(right_power))
                else:
                    forward_right_pwm.ChangeDutyCycle(0)
                    backward_right_pwm.ChangeDutyCycle(-int(right_power))
            else:
                forward_right_pwm.ChangeDutyCycle(0)
                backward_right_pwm.ChangeDutyCycle(0)

        event = pygame.event.poll()
        (x, y)=pygame.mouse.get_pos()    
        if event.type == pygame.QUIT:
            return 0
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            downflag=True;
        if event.type == pygame.MOUSEMOTION:
            if downflag:
               
                downflag=False;
                #
    
        if event.type == pygame.MOUSEBUTTONUP:
                
                
            if stop_button.rect.collidepoint([x, y]):
                
                
                return 0
            for counter, neur in enumerate(all_neurons.sprites()):
                if neur.rect.collidepoint([x, y]):
                        stm=neuron.h.IClamp(neur.mod(0.5))
                        stm.delay=neuron.h.t#+step
                        stm.dur=10
                        stm.amp=10
                       
            
            downflag=False;
        
        #neuron.run(t)
        
        #t+=1
        
        
        
        
        #all_neurons.draw(screen)

        for counter, neur in enumerate(all_neurons.sprites()):
            #dirty_recs+=neur.drawAxons()
            #dirty_recs.append(neur.rect)
            recv[counter].resize(0)
        
        for ap in APs:
            dirty_recs+=ap.draw_and_advance() 
            if ap.pos==(ap.axon.len-1):
                APs.remove(ap)                

        neuron.h.continuerun(t)
        t+=step         
        
        v=np.append(v[1::], [all_neurons.sprites()[0].mod(0.5).v])
        plot_count+=1
	if plot_count==10:
		plot_count=0
		vmax=np.max(v)
        	vmin=np.min(v)-1
        
        	v_scaled=50-49*(v-vmin)/(vmax-vmin)
        
		plist=np.vstack((np.array(range(plot_len)), v_scaled))
        
        	plt.fill(bgcolor)
        	pygame.draw.lines(plt, BLUE, False, np.transpose(plist))
        	dirty_recs.append(screen.blit(plt, (100, 100)))
        
        pygame.display.update(dirty_recs)
        dirty_recs=[]
    


pygame.init()

neuron.h.load_file("stdrun.hoc")

y = 0
dir = 1
running = 1

screen = pygame.display.set_mode((width, height))
bgcolor = WHITE

screen.fill(WHITE)
pr = cProfile.Profile()
pr.enable()

build_loop()

pr.disable()
s = StringIO.StringIO()
sortby = 'cumulative'
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print s.getvalue()
if RPI:
    io.cleanup()
pygame.quit()
