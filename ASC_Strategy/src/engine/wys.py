from __future__ import annotations
from .ts import *  # Displacement
from src.utils.constants import *


# Used for Optimizer

class CarNode:
    def __init__(self, power: float = 0, braking_force: float = 0, velocity: Velocity = Velocity(Vec(0, 0), 0)):
        self.power = power
        self.braking_force = braking_force
        self.velocity = velocity
        self.Fm = 0

    def Fm_calc(self, velocity: Velocity):
        if velocity.mag <= 0.2:
            self.Fm = 50
        else:
            self.Fm = self.power / velocity.mag

    def Fd_calc(self, velocity: Velocity, wind: Velocity = Velocity(Vec(0, 0), 0)):
        self.Fd = 0.5 * air_density * coef_drag * cross_section * ((velocity - wind).mag ** 2)

    def Frr_calc(self, seg: Segment):
        self.Frr = coef_rr * car_mass * accel_g * seg.gradient.cos()

    def Fg_calc(self, seg: Segment):
        self.Fg = car_mass * accel_g * seg.gradient.sin()

    def Ft_calc(self):
        self.Ft = self.Fm - self.Fd - self.Frr - self.Fg - self.braking_force


class TimeNode(CarNode):
    def __init__(self, time: float = 0, dist: float = 0, velocity: Velocity = Velocity(Vec(0, 0), 0), acc: float = 0,
                 power: float = 0, braking_force: float = 0):
        super().__init__(power, braking_force)
        self.time = time
        self.dist = dist
        self.velocity = velocity
        self.acc = acc

    def solve_TimeNode(self, initial_TimeNode: TimeNode, segment: Segment, time_step):
        self.Fm_calc(initial_TimeNode.velocity)
        self.Fd_calc(initial_TimeNode.velocity)  # add wind here
        self.Frr_calc(segment)
        self.Fg_calc(segment)
        self.Ft_calc()
        self.acc = self.Ft / car_mass
        self.velocity = Velocity(segment.unit_vector(), initial_TimeNode.velocity.mag + self.acc * time_step)
        self.dist = initial_TimeNode.dist + initial_TimeNode.velocity.mag * time_step + 0.5 * self.acc * time_step ** 2

    def __str__(self):
        return f"D: {self.dist} T:{self.time},P: {self.power}, A: {self.acc}, Ft: {self.Ft}, V: {self.velocity.kmph}\n Forces {self.Fd, self.Frr, self.Fg}"


class VelocityNode(CarNode):
    def __init__(self, time: float = 0, current: float = 0, power: float = 0, acc: float = 0,
                 velocity: Velocity = Velocity(Vec(0, 0), 0)):
        super().__init__(time, power, acc, velocity)

    def power_calc(self):
        pass
