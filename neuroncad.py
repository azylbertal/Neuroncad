"""
(C) Asaph Zylbertal 2016, HUJI, Jerusalem, Israel

Main module

"""

import pygame
import pickle
import neuron
import Tkinter as tk
import tkFileDialog
import tkSimpleDialog
import numpy as np
from time import sleep
import eztext
from neuron_module import Neuron, Axon, AP, pickledNeuron
import multiprocessing
import ctypes
import struct
import pyaudio
import pygame.camera
import os

try:
    import RPi.GPIO as io
    from spi_module import SpiSensors
    from motors_module import Motors
    RPI = True
    print "Running on RPi"
except:
    RPI = False
    print "Not running on RPi"

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BGCOLOR = WHITE

audio_bin=4000

cam_dev = "/dev/video0"
cam_width = 32
cam_height = 24
cam_scale = 8
cam_gain = 7
cam_expo = 10


def update_buffer(nrns, screen, x, y):
    print os.getpid()
    cam.start()
    pixel_width = cam_scale
    pixel_height = cam_scale
    while not shut_down.value:
        catSurfaceObj = cam.get_image()
        scaledDown = pygame.transform.scale(
            catSurfaceObj, (int(cam_width), int(cam_height)))
        pixArray = pygame.surfarray.pixels3d(scaledDown)

        pixArray[:, :, 0] = pixArray[:, :, 2]
        pixArray[:, :, 1] = pixArray[:, :, 2]

        np.copyto(img_buffer, pixArray[:, :, 2])
        cam_icon = pygame.transform.scale(
            scaledDown, (int(cam_width * cam_scale), int(cam_height * cam_scale)))
#        if cam_first_image:
#            cam_first_image = False
        for neur in nrns:
            if neur.tp == 'visual':
                for c in neur.rf:
                    poly_points = [[c[0] * pixel_width, c[1] * pixel_height], [(c[0] + 1) * pixel_width, c[1] * pixel_height], [(
                        c[0] + 1) * pixel_width, (c[1] + 1) * pixel_height], [c[0] * pixel_width, (c[1] + 1) * pixel_height]]
                    cl = (int(255 / (neur.nid + 1)), 255 -
                          int(255 / (neur.nid + 1)), 255)
                    pygame.draw.polygon(cam_icon, cl, poly_points, 1)

        screen.blit(cam_icon, (x, y))
    print 'Stopping camera'
    cam.stop()

def get_cam_stim_amp(rf):

    if cam_online:
        vamp = 0
        pixels = len(rf)
        for c in rf:
            vamp += img_buffer[c[0], c[1]]
        vamp /= pixels

        return vamp / cam_gain
    else:
        return 0


def receptive_field(brn):

    pixel_width = float(brn.width) / cam_width
    pixel_height = float(brn.height) / cam_height

    selected = []

    if cam_online:
        cam.start()
    going = True
    pygame.event.set_blocked(pygame.MOUSEMOTION)

    while going:
        event = pygame.event.poll()
        (x, y) = pygame.mouse.get_pos()
        if event.type == pygame.MOUSEBUTTONDOWN:
            xx = int(x / pixel_width)
            yy = int(y / pixel_height)
            selected.append((xx, yy))
        if event.type == pygame.QUIT:
            going = False
        if cam_online:
            image = cam.get_image()
            catSurfaceObj = image
            pix_array = pygame.surfarray.pixels3d(image)
            pix_array[:, :, 0] = pix_array[:, :, 2]
            pix_array[:, :, 1] = pix_array[:, :, 2]

            scaledDown = pygame.transform.scale(
                catSurfaceObj, (int(cam_width), int(cam_height)))

            scaledUp = pygame.transform.scale(
                scaledDown, (brn.width, brn.height))
        else:
            scaledUp = pygame.Surface((brn.width, brn.height))
        for neur in brn.neurons.sprites():
            if neur.tp == 'visual':
                for c in neur.rf:
                    poly_points = [[c[0] * pixel_width, c[1] * pixel_height], [(c[0] + 1) * pixel_width, c[1] * pixel_height], [(
                        c[0] + 1) * pixel_width, (c[1] + 1) * pixel_height], [c[0] * pixel_width, (c[1] + 1) * pixel_height]]
                    cl = (int(255 / (neur.nid + 1)), 255 -
                          int(255 / (neur.nid + 1)), 255)
                    pygame.draw.polygon(scaledUp, cl, poly_points, 1)
        brn.screen.blit(scaledUp, (0, 0))
        for sel in selected:
            poly_points = [[sel[0] * pixel_width, sel[1] * pixel_height], [(sel[0] + 1) * pixel_width, sel[1] * pixel_height], [(
                sel[0] + 1) * pixel_width, (sel[1] + 1) * pixel_height], [sel[0] * pixel_width, (sel[1] + 1) * pixel_height]]
            pygame.draw.polygon(brn.screen, RED, poly_points)
        pygame.display.update()

    if cam_online:
        cam.stop()

    return np.array(selected)

def get_audio_freqs():
    #global freqs
    print os.getpid()
    pa=pyaudio.PyAudio()
    dev = None
    for i in range(pa.get_device_count()):
        if 'Webcam' in pa.get_device_info_by_index(i).get('name'):
            dev = i
            break
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=audio_bin, input_device_index=dev) 
    #print dev           
    freqs.fill(200.)    
    while not shut_down.value:
        a = stream.read(audio_bin, exception_on_overflow = False)
        np.copyto(freqs, np.abs(np.fft.fft(struct.unpack('<' + str(audio_bin) + 'h', a))))
        #print freqs[40]
        #print freqs[40]

def get_mic_stim_amp(freq, threshold, audio_gain):
    ind = int(round((freq - 1) * (audio_bin / 44100.)))
    fval = freqs[ind]
    
    if fval > threshold:
        return (fval - threshold) / audio_gain
    else:
        return None

class RingBuffer():

    def __init__(self, length, initial):
        self.data = np.ones(length, dtype='f') * initial
        self.index = 0

    def extend(self, x):
        self.data[self.index] = x
        self.index = (self.index + 1) % self.data.size

    def get(self):
        idx = (self.index + np.arange(self.data.size)) % self.data.size
        return self.data[idx]


class Sensors(object):

    def __init__(self, RPi):
        #self.cam = Camera("/dev/video0", 32, 24, 8, 7)
        #self.mic = Mic(4000, 500000, 10000)

        if RPi:
            self.spi = SpiSensors([30])


class Button(pygame.sprite.Sprite):

    def __init__(self, imgf, x, y, tp=None):

        super(Button, self).__init__()
        self.image = pygame.image.load(imgf).convert()
        self.image.set_colorkey(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.tp = tp


class brain(object):

    def __init__(self, downSampleFactor, step):
        pygame.init()
        dispinf = pygame.display.Info()
        self.width = dispinf.current_w - 200
        self.height = dispinf.current_h - 50
        if self.width > 1300:
            self.width = 1300
        if self.height > 710:
            self.height = 710

        try:
            pygame.mixer.init()
            self.spike_sound = pygame.mixer.Sound("static/spike.wav")
            self.sound_card = True
            print "Sound output detected"
        except:
            self.sound_card = False
            print "sound output not detected"

        self.tkroot = tk.Tk()
        self.tkroot.withdraw()
        print "Initializing main window"
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.screen.fill(BGCOLOR)
        pygame.display.set_caption("Brain")

        neuron.h.load_file("stdrun.hoc")

        self.neurons = pygame.sprite.Group()
        self.sns = Sensors(RPI)

        self.step = step
        self.downSampleFactor = downSampleFactor

        self.motors = 0
        self.visuals = 0
        self.auditories = 0

        self.spike_threshold = 0.

        self.stdp = False
        self.stdp_max = 4000

    def __del__(self):
        print "brain object deleted"

    def get_neurons_info(self):
        neurons = []
        for counter, neur in enumerate(self.neurons.sprites()):
            neurons += [pickledNeuron(neur)]

        return neurons

    def set_neurons_info(self, inf):
        self.neurons = pygame.sprite.Group()
        self.visuals = 0
        self.motors = 0
        self.auditories = 0
        last_nid = 0
        for counter, neur in enumerate(inf):
            nrn = Neuron(neur.rect.x, neur.rect.y, neur.tp, self,
                         shift=False, nid=neur.nid, rf=neur.rf, freq=neur.freq)
            self.updateCounts(neur.tp, 1)
            self.neurons.add(nrn)
            if neur.nid > last_nid:
                last_nid = neur.nid
        for counter, neur in enumerate(inf):

            for paxon in neur.axons:
                for counter, neur in enumerate(self.neurons.sprites()):
                    if neur.nid == paxon['start']:
                        start_nrn = neur
                    if neur.nid == paxon['end']:
                        end_nrn = neur
                start_nrn.axons.append(Axon(start_nrn, end_nrn, paxon['points'], start_nrn.tp, paxon[
                                       'weight'], paxon['start'], paxon['end'], self.step, self.spike_threshold, interp=False))
        return last_nid

    def stop_rec(self):
        shut_down.value = True
        sleep(0.3)
        shut_down.value = False


    def updateCounts(self, tp, update):

        if tp == 'visual':
            self.visuals += update
        if tp == 'auditory':
            self.auditories += update
        if tp == 'rightforward' or tp == 'rightbackward' or tp == 'leftforward' or tp == 'leftbackward':
            self.motors += update

    def build_loop(self):
        print "Starting build loop"
        buttons = pygame.sprite.Group()
        drawing = False
        downflag = False
        update_screen = True
        pts = []
        building = True
        nid = 0
        run_button = Button(
            'static/run.bmp', self.width - 80, self.height - 50)
        buttons.add(run_button)
        exit_button = Button(
            'static/exit.bmp', self.width - 120, self.height - 40)
        buttons.add(exit_button)
        excitatory_button = Button(
            'static/pyramidal.bmp', 10, 10, 'excitatory')
        buttons.add(excitatory_button)
        inhibitory_button = Button(
            'static/interneuron.bmp', 80, 10, 'inhibitory')
        buttons.add(inhibitory_button)
        visual_button = Button('static/visual.bmp', 150, 10, 'visual')
        buttons.add(visual_button)
        auditory_button = Button('static/auditory.bmp', 220, 10, 'auditory')
        buttons.add(auditory_button)
        save_button = Button('static/save.bmp', self.width - 100, 10)
        buttons.add(save_button)
        load_button = Button('static/load.bmp', self.width - 50, 10)
        buttons.add(load_button)
        irsensor_button = Button('static/ir_sensor.bmp', 290, 10, 'irsensor')
        buttons.add(irsensor_button)
        rightforward_button = Button(
            'static/rightforward.bmp', 360, 10, 'rightforward')
        buttons.add(rightforward_button)
        rightbackward_button = Button(
            'static/rightbackward.bmp', 450, 10, 'rightbackward')
        buttons.add(rightbackward_button)
        leftforward_button = Button(
            'static/leftforward.bmp', 540, 10, 'leftforward')
        buttons.add(leftforward_button)
        leftbackward_button = Button(
            'static/leftbackward.bmp', 630, 10, 'leftbackward')
        buttons.add(leftbackward_button)

        focus = excitatory_button

        wightbx = eztext.Input(
            maxlength=6, color=BLUE, x=self.width - 500, y=50, prompt='Synaptic weight: ')
        wightbx.value = '0.1'
        wightbx.focus = True
        pygame.event.set_allowed(
            [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION])

        while building:

            event = pygame.event.poll()
            (x, y) = pygame.mouse.get_pos()
            if event.type == pygame.QUIT:
                return 0

            if event.type == pygame.KEYDOWN:
                update_screen = True
            if event.type == pygame.KEYUP:
                update_screen = True

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_buttons = pygame.mouse.get_pressed()
                if mouse_buttons[0]:
                    downflag = True
                if mouse_buttons[2]:
                    for neur in self.neurons.sprites():
                        if neur.rect.collidepoint([x, y]):
                            update_screen = True
                            for n in self.neurons.sprites():
                                axons_to_remove = []
                                for ax in n.axons:
                                    if ax.end_id == neur.nid:
                                        del ax.con
                                        del ax.syn
                                        axons_to_remove.append(ax)
                                for ax in axons_to_remove:
                                    n.axons.remove(ax)

                            self.neurons.remove(neur)
                            self.updateCounts(neur.tp, -1)
                            del neur

            if event.type == pygame.MOUSEMOTION:
                if downflag:
                    drawing = True
                    pts = []

                    downflag = False

            if event.type == pygame.MOUSEBUTTONUP:
                update_screen = True
                if mouse_buttons[0]:
                    if not drawing:

                        if run_button.rect.collidepoint([x, y]):
                            self.run_loop()
                        elif exit_button.rect.collidepoint([x, y]):
                            return 0
                        elif save_button.rect.collidepoint([x, y]):
                            file_path = tkFileDialog.asksaveasfilename()
                            if file_path:
                                fl = open(file_path, 'w')
                                info = self.get_neurons_info()
                                pickle.dump(info, fl)
                                fl.close()
                        elif load_button.rect.collidepoint([x, y]):
                            file_path = tkFileDialog.askopenfilename()
                            if file_path:
                                fl = open(file_path, 'r')
                                inf = pickle.load(fl)
                                nid = self.set_neurons_info(inf) + 1
                                fl.close()

                        elif excitatory_button.rect.collidepoint([x, y]):
                            focus = excitatory_button
                        elif inhibitory_button.rect.collidepoint([x, y]):
                            focus = inhibitory_button
                        elif visual_button.rect.collidepoint([x, y]):
                            focus = visual_button
                        elif auditory_button.rect.collidepoint([x, y]):
                            focus = auditory_button

                        if rightforward_button.rect.collidepoint([x, y]):
                            focus = rightforward_button
                        elif rightbackward_button.rect.collidepoint([x, y]):
                            focus = rightbackward_button
                        elif leftforward_button.rect.collidepoint([x, y]):
                            focus = leftforward_button
                        elif leftbackward_button.rect.collidepoint([x, y]):
                            focus = leftbackward_button
                        elif irsensor_button.rect.collidepoint([x, y]):
                            focus = irsensor_button

                        if y > 150 and y < self.height - 100:
                            on_neuron = False
                            for counter, neur in enumerate(self.neurons.sprites()):
                                if neur.rect.collidepoint([x, y]):
                                    on_neuron = True

                            if not on_neuron:
                                if focus.tp == 'auditory':
                                    freq = tkSimpleDialog.askstring(
                                        'Auditory cell', 'Frequency (Hz): ')
                                    if freq is not None:
                                        self.neurons.add(
                                            Neuron(x, y, focus.tp, self, nid=nid, freq=int(freq)))
                                        self.updateCounts(focus.tp, 1)
                                        nid += 1
                                elif focus.tp == 'visual':
                                    self.neurons.add(
                                        Neuron(x, y, focus.tp, self, nid=nid, receptive_field = receptive_field))
                                    self.updateCounts(focus.tp, 1)
                                else:
                                    
                                    self.neurons.add(
                                        Neuron(x, y, focus.tp, self, nid=nid))
                                    self.updateCounts(focus.tp, 1)
                                    nid += 1

                    else:
                        axon_start = False
                        axon_end = False
                        for counter, neur in enumerate(self.neurons.sprites()):
                            if neur.rect.collidepoint(pts[0]) and not neur.super_type == 'motor':
                                start_nrn = counter
                                axon_start = True
                            if neur.rect.collidepoint(pts[len(pts) - 1]):
                                end_nrn = counter
                                axon_end = True

                        if (axon_start and axon_end):
                            tp = self.neurons.sprites()[start_nrn].tp
                            w = float(wightbx.value)
                            start_id = self.neurons.sprites()[start_nrn].nid
                            end_id = self.neurons.sprites()[end_nrn].nid
                            self.neurons.sprites()[start_nrn].axons.append(Axon(self.neurons.sprites()[
                                start_nrn], self.neurons.sprites()[end_nrn], pts, tp, w, start_id, end_id, self.step, self.spike_threshold))

                        pts = []
                        drawing = False

                    downflag = False

            if drawing:
                update_screen = True
                pts = pts + [[x, y]]

            wightbx.update(event)

            if update_screen:
                update_screen = False
                self.screen.fill(BGCOLOR)
                self.neurons.draw(self.screen)
                for neur in self.neurons.sprites():
                    neur.draw_axons()
                buttons.draw(self.screen)
                wightbx.draw(self.screen)
                pygame.draw.rect(self.screen, RED, focus.rect, 2)

                if len(pts) > 1:
                    pygame.draw.lines(self.screen, BLACK, False, pts, 5)

                pygame.display.flip()
    #@profile
    def run_loop(self):

        if RPI and self.motors > 0:
            mtrs = Motors()
        if self.visuals > 0 and cam_online:
            cam_proc = multiprocessing.Process(target = update_buffer, args = (self.neurons.sprites(), self.screen, self.width - (cam_width * cam_scale + 10), self.height - (cam_width * cam_scale + 50)))
            cam_proc.start()
        if self.auditories > 0:# and self.sns.mic.online:
            #get_audio_freqs(self.sns.mic)
            mic_proc = multiprocessing.Process(target=get_audio_freqs, args=())
            mic_proc.start()
 #           mic_proc.join()

        sensors_init = 0
        vmin = -75.
        vmax = -40.
        plot_len = 400
        plist = np.vstack((np.arange(plot_len), np.zeros(plot_len)))

        plot_height = 100
        fire_image_delay = 20
        plot_count = 0
        buttons = pygame.sprite.Group()
        downflag = False
        stop_button = pygame.sprite.Sprite()
        stop_button.image = pygame.image.load("static/stop.bmp").convert()
        stop_button.rect = stop_button.image.get_rect()
        stop_button.rect.x = self.width - stop_button.rect.width
        stop_button.rect.y = self.height - stop_button.rect.height
        buttons.add(stop_button)
        pipette = pygame.sprite.Sprite()
        pipette.image = pygame.image.load("static/pipette.bmp").convert()
        pipette.rect = pipette.image.get_rect()
        buttons.add(pipette)
        plt = pygame.Surface((plot_len, plot_height))
        rec_neuron = 0
        APs = []
        recv = []
        recording = False

        for counter, neur in enumerate(self.neurons.sprites()):
            recv += [neuron.h.Vector()]
            recv[counter].record(neur.mod(0.5)._ref_v)

        neuron.h.finitialize(-60)
        neuron.run(plot_len)
        v = RingBuffer(plot_len, -60.0)
        t = neuron.h.t

        self.screen.fill(BGCOLOR)
        self.neurons.draw(self.screen)
        buttons.draw(self.screen)
        for neur in self.neurons.sprites():
            neur.draw_axons()

        pygame.display.flip()

        while True:
            plot_count += 1
            if sensors_init < 500:
                sensors_init += 1

            right_power = 0.
            left_power = 0.

            for counter, neur in enumerate(self.neurons.sprites()):

                try:
                    max_v = recv[counter].max()
                except:
                    max_v = 0.

                if RPI and neur.tp == 'irsensor' and sensors_init == 500:
                    neur.ext_stm.delay = neuron.h.t
                    neur.ext_stm.dur = self.step
                    neur.ext_stm.amp = self.sns.spi.get_stim_amp(0)

                if neur.tp == 'visual' and sensors_init == 500:
                    neur.ext_stm.delay = neuron.h.t
                    neur.ext_stm.dur = self.step
                    if plot_count==self.downSampleFactor:
                        neur.ext_stm.amp=get_cam_stim_amp(neur.rf)


                if neur.tp == 'auditory' and sensors_init == 500:
                    audio_stim_amp = get_mic_stim_amp(neur.freq, 500000, 10000)

                    if audio_stim_amp is not None:
                        neur.ext_stm.delay = neuron.h.t
                        neur.ext_stm.dur = self.step
                        neur.ext_stm.amp = audio_stim_amp

                if neur.super_type == 'motor':
                    try:

                        b=neur.mod(0.5).v
                        mean_v=20*(70+b)
                        if mean_v < 0:
                            mean_v = 0
                    except:
                        mean_v = 0.

                    if neur.tp == 'rightforward':
                        right_power += mean_v
                    elif neur.tp == 'rightbackward':
                        right_power -= mean_v
                    elif neur.tp == 'leftforward':
                        left_power += mean_v
                    elif neur.tp == 'leftbackward':
                        left_power -= mean_v

                if neur.stdp > 0:
                    neur.stdp -= 1

                if not neur.super_type == 'motor' and max_v > self.spike_threshold:

                    if self.stdp:
                        neur.stdp = self.stdp_max
                        for n in self.neurons.sprites():
                            for ax in n.axons:
                                if ax.end_id == neur.nid:
                                    if n.stdp > 0:
                                        ax.w += (0.2 - ax.w) * 0.01
                                    else:
                                        ax.w -= (ax.w - 0.01) * 0.01

                                    ax.con.weight[0] = ax.w

                    if neur.fire_counter == 0:
                        neur.fire_counter = fire_image_delay
                        if recording:
                            if self.sound_card and neur == rec_neuron:
                                self.spike_sound.play()
                        for ax in neur.axons:

                            APs.append(AP(ax, self.screen))

                if neur.fire_counter > 0:

                    neur.fire_counter -= 1

            if self.motors > 0 and RPI:
                mtrs.update_power(left_power, right_power)

            event = pygame.event.poll()
            (x, y) = pygame.mouse.get_pos()
            if event.type == pygame.QUIT:
                self.stop_rec()

                return 0

            if event.type == pygame.MOUSEBUTTONDOWN:
                downflag = True
                mouse_buttons = pygame.mouse.get_pressed()
            if event.type == pygame.MOUSEMOTION:
                if downflag:
                    downflag = False
            if event.type == pygame.MOUSEBUTTONUP:
                if stop_button.rect.collidepoint([x, y]):
                    self.stop_rec()
                    return 0
                for counter, neur in enumerate(self.neurons.sprites()):
                    if neur.rect.collidepoint([x, y]):
                        if mouse_buttons[0]:
                            stm = neuron.h.IClamp(neur.mod(0.5))
                            stm.delay = neuron.h.t
                            stm.dur = 10
                            stm.amp = 10
                        if mouse_buttons[2]:
                            rec_neuron = neur
                            pygame.draw.rect(
                                self.screen, BGCOLOR, pipette.rect)
                            pipette.rect.x = x
                            pipette.rect.y = y
                            buttons.draw(self.screen)
                            recording = True

                downflag = False

            for counter, neur in enumerate(self.neurons.sprites()):
                recv[counter].resize(0)

                to_draw = plot_count == self.downSampleFactor

            for ap in APs:
                ap.draw_and_advance(to_draw)
                if ap.pos == (ap.axon.len - 1):
                    ap.clear()
                    APs.remove(ap)

            neuron.run(t)
            t += self.step

            if plot_count == self.downSampleFactor:
                plot_count = 0
                #sleep(0.0001)
                if recording:
                    v.extend(rec_neuron.mod(0.5).v)
                    v_scaled = plot_height - \
                        (plot_height) * (v.get() - vmin) / (vmax - vmin)
                    v_scaled[(v_scaled < 0)] = 0
                    plist[1, :] = v_scaled

                    plt.fill(BGCOLOR)
                    pygame.draw.lines(plt, BLUE, False, np.transpose(plist))

                    self.screen.blit(plt, (100, 10))

                self.neurons.draw(self.screen)
                for counter, neur in enumerate(self.neurons.sprites()):
                    neur.draw_axons()

                pygame.display.update()


def main():

    if RPI:
        io.setmode(io.BCM)
        downSampleFactor = 30.
        io.setwarnings(False)
    else:
        downSampleFactor = 10.

    brn = brain(downSampleFactor, 0.1)
    brn.build_loop()

    if RPI:
        io.cleanup()
    pygame.quit()

if __name__ == "__main__":
    freqs_base = multiprocessing.Array(ctypes.c_double, audio_bin)
    freqs = np.frombuffer(freqs_base.get_obj(), dtype=ctypes.c_double)
    img_buffer_base = multiprocessing.Array(ctypes.c_double, cam_width*cam_height)
    img_buffer = np.frombuffer(img_buffer_base.get_obj(), dtype=ctypes.c_double)
    img_buffer=img_buffer.reshape(cam_width, cam_height)
    shut_down = multiprocessing.Value(ctypes.c_bool, False)
    
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
        
            cam_online = True
            print "Camera detected"
        except:
            cam_online = False
            print "Camera not detected"
    main()
