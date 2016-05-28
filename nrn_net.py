import pygame
import pickle
import neuron
import Tkinter as tk
import tkFileDialog
import numpy as np
from time import sleep
import eztext
import thread
from camera_module import Camera
from mic_module import Mic
from neuron_module import Neuron, Axon, AP, pickledNeuron

try:
    import RPi.GPIO as io
    from spi_module import SpiSensors
    from motors_module import Motors
    RPI = True
    print "Running on RPi"
except:
    RPI = False
    print "Not running on RPi"

BLACK = (0,   0,   0)
WHITE = (255, 255, 255)
RED = (255,   0,   0)
BLUE = (0,   0,   255)
BGCOLOR = WHITE

stdp_max = 5000

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
        self.cam = Camera("/dev/video0", 32, 24, 8, 7)
        self.mic = Mic(4000, 500000, 100000)

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
            self.spike_sound = pygame.mixer.Sound("spike.wav")
            self.sound_card = True
            print "Sound output detected"
        except:
            self.sound_card = False
            print "sound output not detected"

        self.tkroot = tk.Tk()
        self.tkroot.withdraw()

        self.screen = pygame.display.set_mode((self.width, self.height))
        self.screen.fill(BGCOLOR)

        neuron.h.load_file("stdrun.hoc")
        self.neurons = pygame.sprite.Group()
        self.sns = Sensors(RPI)

        self.step = step
        self.downSampleFactor = downSampleFactor

        self.motors = 0
        self.visuals = 0
        self.auditories = 0

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
                                       'weight'], paxon['start'], paxon['end'], self.step, interp=False))
        return last_nid

    def stop_rec(self):
        if self.visuals > 0:
            self.sns.cam.shut_down = True
            sleep(0.3)
            self.sns.cam.shut_down = False

        if self.auditories > 0:
            self.sns.mic.shut_down = True
            sleep(0.3)
            self.sns.mic.shut_down = False

    def updateCounts(self, tp, update):

        if tp == 'visual':
            self.visuals += update
        if tp == 'auditory':
            self.auditories += update
        if tp == 'rightforward' or tp == 'rightbackward' or tp == 'leftforward' or tp == 'leftbackward':
            self.motors += update

    def build_loop(self):

        buttons = pygame.sprite.Group()
        drawing = False
        downflag = False
        update_screen = True
        pts = []
        building = True
        nid = 0
        run_button = Button('run.bmp', self.width - 80, self.height - 50)
        buttons.add(run_button)
        exit_button = Button('exit.bmp', self.width - 120, self.height - 40)
        buttons.add(exit_button)
        excitatory_button = Button('pyramidal.bmp', 10, 10, 'excitatory')
        buttons.add(excitatory_button)
        inhibitory_button = Button('interneuron.bmp', 80, 10, 'inhibitory')
        buttons.add(inhibitory_button)
        visual_button = Button('visual.bmp', 150, 10, 'visual')
        buttons.add(visual_button)
        auditory_button = Button('auditory.bmp', 220, 10, 'auditory')
        buttons.add(auditory_button)
        save_button = Button('save.bmp', self.width - 100, 10)
        buttons.add(save_button)
        load_button = Button('load.bmp', self.width - 50, 10)
        buttons.add(load_button)
        irsensor_button = Button('ir_sensor.bmp', 290, 10, 'irsensor')
        buttons.add(irsensor_button)
        rightforward_button = Button(
            'rightforward.bmp', 360, 10, 'rightforward')
        buttons.add(rightforward_button)
        rightbackward_button = Button(
            'rightbackward.bmp', 450, 10, 'rightbackward')
        buttons.add(rightbackward_button)
        leftforward_button = Button('leftforward.bmp', 540, 10, 'leftforward')
        buttons.add(leftforward_button)
        leftbackward_button = Button(
            'leftbackward.bmp', 630, 10, 'leftbackward')
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

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_buttons = pygame.mouse.get_pressed()
                if mouse_buttons[0]:
                    downflag = True
                if mouse_buttons[2]:
                    for neur in self.neurons.sprites():
                        if neur.rect.collidepoint([x, y]):
                            update_screen=True
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
                update_screen=True
                if mouse_buttons[0]:
                    if not drawing:

                        if run_button.rect.collidepoint([x, y]):
                            self.run_loop()
                        elif exit_button.rect.collidepoint([x, y]):
                            return 0
                        elif save_button.rect.collidepoint([x, y]):
                            file_path = tkFileDialog.asksaveasfilename()
                            if not file_path == ():
                                fl = open(file_path, 'w')
                                info = self.get_neurons_info()
                                pickle.dump(info, fl)
                                fl.close()
                        elif load_button.rect.collidepoint([x, y]):
                            file_path = tkFileDialog.askopenfilename()
                            if not file_path == ():
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
                                start_nrn], self.neurons.sprites()[end_nrn], pts, tp, w, start_id, end_id, self.step))

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
                    neur.drawAxons()
                buttons.draw(self.screen)
                wightbx.draw(self.screen)
                pygame.draw.rect(self.screen, RED, focus.rect, 2)

                if len(pts) > 1:
                    pygame.draw.lines(self.screen, BLACK, False, pts, 5)

                pygame.display.flip()

    def run_loop(self):

        if RPI and self.motors > 0:
            mtrs = Motors()
        if self.visuals > 0 and self.sns.cam.online:
            thread.start_new_thread(
                self.sns.cam.update_buffer, (self.neurons.sprites(), self.screen, self.width - (self.sns.cam.width * self.sns.cam.scale + 10), self.height - (self.sns.cam.width * self.sns.cam.scale + 50)))
        if self.auditories > 0 and self.sns.mic.online:
            thread.start_new_thread(self.sns.mic.get_audio_freqs, ())

        sensors_init = 0
        vmin = -75.
        vmax = -40.
        plot_len = 400
        plist = np.vstack((np.arange(plot_len), np.zeros(plot_len)))

        plot_height = 100
        fire_image_delay = 10
        plot_count = 0
        buttons = pygame.sprite.Group()
        downflag = False
        stop_button = pygame.sprite.Sprite()
        stop_button.image = pygame.image.load("stop.bmp").convert()
        stop_button.rect = stop_button.image.get_rect()
        stop_button.rect.x = self.width - stop_button.rect.width
        stop_button.rect.y = self.height - stop_button.rect.height
        buttons.add(stop_button)
        pipette = pygame.sprite.Sprite()
        pipette.image = pygame.image.load("pipette.bmp").convert()
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
            neur.drawAxons()

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
                    neur.ext_stm.amp = self.sns.cam.get_stim_amp(neur.rf)

                if neur.tp == 'auditory' and sensors_init == 500:
                    audio_stim_amp = self.sns.mic.get_stim_amp(neur.freq)

                    if audio_stim_amp is not None:
                        neur.ext_stm.delay = neuron.h.t
                        neur.ext_stm.dur = self.step
                        neur.ext_stm.amp = audio_stim_amp

                if neur.super_type == 'motor':
                    try:
                        mean_v = 20 * (70 + np.mean(np.array(recv[counter])))
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

                if not neur.super_type == 'motor' and max_v > 25.0:
                    neur.stdp = stdp_max
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
                sleep(0.001)
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
                    neur.drawAxons()

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
    main()
