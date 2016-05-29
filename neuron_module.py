"""
(C) Asaph Zylbertal 2016, HUJI, Jerusalem, Israel

Methods for single neuron simulation and graphics: axons, action potentials

"""

import pygame
import math
import neuron
from camera_module import receptive_field

WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)


class Neuron(pygame.sprite.Sprite):

    def __init__(self, x, y, tp, brn, shift=True, nid=None, rf=None, freq=None):

        super(Neuron, self).__init__()
        self.screen = brn.screen

        self.rf = 0
        self.freq = None
        self.stdp = 0
        self.mod = neuron.h.Section()
        if tp == 'excitatory':
            self.image = pygame.image.load("static/pyramidal.bmp").convert()
            self.super_type = 'neuron'
        elif tp == 'inhibitory':
            self.image = pygame.image.load("static/interneuron.bmp").convert()
            self.super_type = 'neuron'
        elif tp == 'rightforward':
            self.image = pygame.image.load("static/rightforward.bmp").convert()
            self.super_type = 'motor'
        elif tp == 'rightbackward':
            self.image = pygame.image.load(
                "static/rightbackward.bmp").convert()
            self.super_type = 'motor'
        elif tp == 'leftforward':
            self.image = pygame.image.load("static/leftforward.bmp").convert()
            self.super_type = 'motor'
        elif tp == 'leftbackward':
            self.image = pygame.image.load("static/leftbackward.bmp").convert()
            self.super_type = 'motor'
        elif tp == 'irsensor':
            self.image = pygame.image.load("static/ir_sensor.bmp").convert()
            self.super_type = 'sensor'
        elif tp == 'auditory':
            self.image = pygame.image.load("static/auditory.bmp").convert()
            self.auditory_stm = 0
            self.super_type = 'sensor'
            self.freq = freq

        elif tp == 'visual':

            self.image = pygame.image.load("static/visual.bmp").convert()
            self.visual_stm = 0
            self.super_type = 'sensor'
            if rf is None:
                self.rf = receptive_field(brn)
                pygame.event.set_allowed(
                    [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION])
            else:
                self.rf = rf

        self.nid = nid

        self.tp = tp
        self.image.set_colorkey(WHITE)
        self.rect = self.image.get_rect()
        if shift:
            self.rect.x = x - self.rect.width / 2
            self.rect.y = y - self.rect.height / 2
        else:
            self.rect.x = x
            self.rect.y = y

        if self.super_type == 'neuron' or self.super_type == 'sensor':
            self.mod.insert('hh')

        elif self.super_type == 'motor':
            self.mod.insert('pas')
        if self.super_type == 'sensor':
            self.ext_stm = neuron.h.IClamp(self.mod(0.5))
            self.ext_stm.delay = 0
            self.ext_stm.dur = 1
            self.ext_stm.amp = 0
        self.fire_counter = 0
        self.axons = []

    def draw_axons(self):
        recs = []
        for axon in self.axons:
            recs.append(axon.draw(self.screen))
        return recs

    def pickled_axons(self):
        paxons = []
        for axon in self.axons:
            paxons += [{'points': axon.points, 'weight': axon.w,
                        'start': axon.start_id, 'end': axon.end_id}]
        return paxons


class pickledNeuron(object):

    def __init__(self, nrn):
        self.rect = nrn.rect
        self.tp = nrn.tp
        self.super_type = nrn.super_type
        self.nid = nrn.nid
        self.rf = nrn.rf
        self.freq = nrn.freq
        self.axons = nrn.pickled_axons()


class Axon(object):

    def __init__(self, startp, endp, points, tp, weight, start_id, end_id, time_step, spike_threshold, interp=True):

        self.cl = BLACK
        self.start_id = start_id
        self.end_id = end_id
        if interp:
            self.points = []
            for p in range(len(points) - 1):
                self.points += inter(points[p], points[p + 1])
        else:
            self.points = points
        self.len = len(self.points)
        self.syn = neuron.h.ExpSyn(endp.mod(0.5))
        self.w = weight
        self.tp = tp
        if tp == 'excitatory' or tp == 'irsensor' or tp == 'visual' or tp == 'auditory':
            self.syn.tau = 4
            self.cl = BLUE
            self.syn.e = 0.0
        elif tp == 'inhibitory':
            self.syn.tau = 20
            self.cl = RED
            self.syn.e = -90.0
        self.con = neuron.h.NetCon(startp.mod(
            0.5)._ref_v, self.syn, spike_threshold, self.len * time_step, self.w, sec=startp.mod)

    def draw(self, screen):
        return pygame.draw.lines(screen, self.cl, False, self.points, int(self.w * 20))


class AP(object):

    def __init__(self, axon, screen):
        self.axon = axon
        self.pos = 0
        self.old_pos = 0
        self.screen = screen
        self.size = int(self.axon.w * 30)

    def draw_and_advance(self, to_draw):
        self.pos += 1
        if to_draw:
            oldc = pygame.draw.circle(self.screen, WHITE, map(
                int, self.axon.points[self.old_pos]), self.size)

            newc = pygame.draw.circle(self.screen, self.axon.cl, map(
                int, self.axon.points[self.pos]), self.size)
            self.old_pos = self.pos
            return [oldc, newc]
        else:
            return []

    def clear(self):
        return [pygame.draw.circle(self.screen, WHITE, [int(p) for p in self.axon.points[self.old_pos]], self.size)]


def inter(pt1, pt2):
    ln_x = float(pt2[0]) - pt1[0]
    ln_y = float(pt2[1]) - pt1[1]
    ln = int(round(math.sqrt(ln_x * ln_x + ln_y * ln_y)))
    int_pts = []
    for l in range(ln):
        int_pts += [[pt1[0] + l * (ln_x / ln), pt1[1] + l * (ln_y / ln)]]

    return int_pts
