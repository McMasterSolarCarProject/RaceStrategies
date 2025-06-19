from __future__ import annotations
from .kinematics import Vec, Velocity, Displacement, Speed, Coordinate, ZERO_VEC, UNIT_VEC, ZERO_VELOCITY
from ..utils.constants import *
from math import sin, cos


class Segment(Displacement):  # Meters
    def __init__(self, p1: Coordinate, p2: Coordinate, speed_limit: Speed = Speed(0), wind: Velocity = ZERO_VEC, v_eff: Speed = Speed(0), p_eff: float = 0, azimuth: float = 0, ghi: float = 0):
        super().__init__(p1, p2)
        self.displacement = Displacement(p1, p2)
        self.v_eff = Velocity(self.displacement.unit_vector(), v_eff)
        self.p_eff = p_eff
        self.wind = wind
        self.speed_limit = speed_limit
        self.tdist = self.dist
        self.ghi = ghi
        self.azimuth = azimuth

    def __str__(self):
        return f"Total Distance: {self.tdist} | V eff: {self.v_eff} | P eff: {self.p_eff}"

class StateNode:
    def __init__(self, power: float = 0, Fb: float = 0, velocity: Velocity = ZERO_VELOCITY):
        self.power = power
        self.Fb = Fb
        self.velocity = velocity
        self.Fm = 0

    def Fm_calc(self, velocity: Velocity):
        if velocity.mag <= 0.2:
            self.Fm = 50
        else:
            self.Fm = self.power / velocity.mag

    def Fd_calc(self, velocity: Velocity, wind: Velocity = ZERO_VELOCITY):
        self.Fd = 0.5 * air_density * coef_drag * cross_section * ((velocity - wind).mag ** 2)

    def Frr_calc(self, seg: Segment):
        self.Frr = coef_rr * car_mass * accel_g * seg.gradient.cos()

    def Fg_calc(self, seg: Segment):
        self.Fg = car_mass * accel_g * seg.gradient.sin()

    def Ft_calc(self):
        self.Ft = self.Fm - self.Fd - self.Frr - self.Fg - self.Fb

    def solar_energy_cal(self):
        self.solar = 0


class TimeNode(StateNode):
    def __init__(self, time: float = 0, dist: float = 0, velocity: Velocity = ZERO_VELOCITY, acc: float = 0, power: float = 0, Fb: float = 0):
        super().__init__(power, Fb)
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
        self.velocity = Velocity(segment.unit_vector(), Speed(initial_TimeNode.velocity.mps + self.acc * time_step))
        self.dist = initial_TimeNode.dist + initial_TimeNode.velocity.mag * time_step + 0.5 * self.acc * time_step ** 2

    def __str__(self):
        return f"D: {self.dist} T:{self.time},P: {self.power}, A: {self.acc}, Ft: {self.Ft}, V: {self.velocity.kmph}\n Forces {self.Fd, self.Frr, self.Fg}"


class VelocityNode(StateNode):
    #constant vel --> motor force -->  power, torque --> energy per metre (epm)
    def __init__(self, velocity: Velocity = ZERO_VELOCITY):
        super().__init__(0, 0, velocity)

    def solve_velocity(self,segment):
        self.Fd_calc(self.velocity)
        self.Fg_calc(segment)
        self.Frr_calc(segment)
        self.solar_energy_cal()
        self.Fm = self.Fg + self.Frr + self.Fd
        self.power = self.Fm * self.velocity.mps
        self.torque = self.Fm * wheel_radius
        if self.power == 0:
            raise ValueError(f"Power is zero for velocity {self.velocity.mps:.2f} m/s.")
        self.epm = self.power / (self.velocity.mps) #- self.solar / self.velocity.mps

if __name__ == "__main__":
    def test_segment():
        pass

    def test_StateNode():
        pass

    def test_TimeNode():
        pass

    def test_VelocityNode():
        pass

    print("typeshi")