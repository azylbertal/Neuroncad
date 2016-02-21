import pygame
import math
import neuron
#import matplotlib.pyplot as plt
import numpy as np
import cProfile, pstats, StringIO
from time import sleep
import eztext

BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED   = (255,   0,   0)
BLUE  = (0,   0,   255)
width = 800
height = 600

step=0.1
    
class Neuron(pygame.sprite.Sprite):
    def __init__(self, x, y):
    
        super(Neuron, self).__init__()  
        self.image = pygame.image.load("neuron.bmp").convert()
        self.image.set_colorkey(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x=x-self.rect.width/2
        self.rect.y=y-self.rect.height/2
        self.mod=neuron.h.Section()
        self.mod.insert('hh')
        self.fire_counter=0
        self.axons=[]
        
    def drawAxons(self):
        for axon in self.axons:
            axon.draw(screen)
        

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
        pygame.draw.lines(screen, BLUE, False, self.points, 1)


class AP():
    def __init__(self, axon):
        self.axon=axon
        self.pos=0
    def draw_and_advance(self):
        pygame.draw.circle(screen, BLUE, [int(p) for p in self.axon.points[self.pos]], 10)
        self.pos+=1
       
        
        
def inter(pt1, pt2):
    ln_x=float(pt2[0])-pt1[0]
    ln_y=float(pt2[1])-pt1[1]
    ln=int(round(math.sqrt(ln_x*ln_x+ln_y*ln_y)))
    int_pts=[]   
    for l in range(ln):
        int_pts+=[[pt1[0]+l*(ln_x/ln), pt1[1]+l*(ln_y/ln)]]
        
    return int_pts 

def runmod(t):
	neuron.h.continuerun(t)

def build_loop():

    all_neurons = pygame.sprite.Group()
    buttons = pygame.sprite.Group()
    drawing=False;
    downflag=False;
    pts=[]
    building=1
    run_button=pygame.sprite.Sprite()
    run_button.image=pygame.image.load("run.bmp").convert()
    run_button.rect=run_button.image.get_rect()
    run_button.rect.x=width-run_button.rect.width
    run_button.rect.y=height-run_button.rect.height
    buttons.add(run_button)
    exit_button=pygame.sprite.Sprite()
    exit_button.image=pygame.image.load("exit.bmp").convert()
    exit_button.rect=exit_button.image.get_rect()
    exit_button.rect.x=width-run_button.rect.width-exit_button.rect.width
    exit_button.rect.y=height-exit_button.rect.height
    buttons.add(exit_button)
    
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
                else:
                    all_neurons.add(Neuron(x,y))
                
                
    
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
        #for ax in axons:
        #    ax.draw(screen)
            
        if len(pts)>1:
            pygame.draw.lines(screen, BLACK, False, pts, 5)
        #for i in range(len(xx)-1):
        #    pygame.draw.line(screen, (200, 200, 200), (xx[i], yy[i]), (xx[i+1], yy[i+1]))
            
    
    
        pygame.display.flip()
        

def run_loop(all_neurons):
    
    vmin=-70.
    vmax=80.   
    plot_len=300    
    fire_image_delay=100
    running=1
    
    buttons = pygame.sprite.Group()
    downflag=False;
    stop_button=pygame.sprite.Sprite()
    stop_button.image=pygame.image.load("stop.bmp").convert()
    stop_button.rect=stop_button.image.get_rect()
    stop_button.rect.x=width-stop_button.rect.width
    stop_button.rect.y=height-stop_button.rect.height
    buttons.add(stop_button)

    firing_neuron_image=pygame.image.load("firing_neuron.bmp").convert()
    neuron_image=pygame.image.load("neuron.bmp").convert()
    plt=pygame.Surface((plot_len, 50))    
    
    APs=[]
    recv=[]
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
    

    while running:
        
        

        for counter, neur in enumerate(all_neurons.sprites()):
            
            if len(np.array(recv[counter])>0):            
                max_v=np.max(np.array(recv[counter]))
            else:
                max_v=0
            if max_v>25.0 and neur.fire_counter==0:
                neur.fire_counter=fire_image_delay
                for ax in neur.axons:
                    APs.append(AP(ax))
                
            if neur.fire_counter>0:
                
                neur.image=firing_neuron_image
                neur.fire_counter-=1
            else:
                neur.image=neuron_image
                
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
        
        
        screen.fill(bgcolor)    
        all_neurons.draw(screen)
        buttons.draw(screen)
        for counter, neur in enumerate(all_neurons.sprites()):
            neur.drawAxons()
            recv[counter].resize(0)
        
        for ap in APs:
            ap.draw_and_advance() 
            if ap.pos==ap.axon.len:
                APs.remove(ap)                

        runmod(t)
	#neuron.h.continuerun(t)
        t+=step         
        
        v=np.append(v[1::], [all_neurons.sprites()[0].mod(0.5).v])
        vmax=np.max(v)
        vmin=np.min(v)-1
                
        plist=[]
        for i in range(plot_len):
            plist+=[[i, 50-49*(v[i]-vmin)/(vmax-vmin)]]
            
        plt.fill(bgcolor)
        pygame.draw.lines(plt, BLUE, False, plist)
        screen.blit(plt, (100, 100))
    
        pygame.display.flip()    
    


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
pygame.quit()
