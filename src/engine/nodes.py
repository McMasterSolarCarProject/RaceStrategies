from __future__ import annotations

import math

from ..config import Vehicle, Engine, constants, vehicle_default, engine_default
from ..models import Segment

class StateNode:

    def __init__(self, segment: Segment, vehicle: Vehicle =  vehicle_default, engine: Engine = engine_default):
        self.segment = segment
        self.vehicle = vehicle
        self.engine = engine

        self.torque = 0
        self.Fb = 0

    def Fm_calc(self):
        self.Fm = self.torque / self.vehicle.wheel_radius * self.vehicle.num_motors

    def Fd_calc(self, initial_speed: float):
        self.Fd = 0.5 * constants.air_density * self.vehicle.coef_drag * self.vehicle.cross_section * ((initial_speed + self.segment.wind_speed) ** 2)

    def Frr_calc(self):
        self.Frr = self.vehicle.coef_rr * self.vehicle.car_mass * constants.g * self.segment.gradient.cos()

    def Fg_calc(self):
        self.Fg = self.vehicle.car_mass * constants.g * self.segment.gradient.sin()

    def Ft_calc(self):
        self.Ft = self.Fm - self.Fd - self.Frr - self.Fg - self.Fb
        self.acc = self.Ft / self.vehicle.car_mass

    def solve_cruise_state(self):
        pass

class DynamicNode(StateNode):

    def __init__(self, segment: Segment, vehicle: Vehicle = vehicle_default, engine: Engine = engine_default, torque: float = 0, Fb: float = 0):
        super().__init__(segment, vehicle, engine)

        self.torque = torque
        self.Fb = Fb

    def initialize(self):
        self.velocity = 0
        self.time = 0
        self.dist = 0
        self.soc = 0

        self.acc = 0
        self.Fm_calc()
        self.Fd_calc(0)
        self.Frr_calc()
        self.Fg_calc()
        self.Ft_calc()


    def solve_DynamicNode(self, initial_DynamicNode: DynamicNode):
        self.Fm_calc()
        self.Fd_calc(initial_DynamicNode.velocity)
        self.Frr_calc()
        self.Fg_calc()
        self.Ft_calc()
        if abs(self.acc) < self.engine.MIN_ACCELERATION:
            return False

        self.dt = self.adaptive_timestep(initial_DynamicNode.velocity)
        if self.dt <= 0:
            return False

        self.velocity = initial_DynamicNode.velocity + self.acc * self.dt
        if self.velocity < 0:
            raise ValueError("DynamicNode velocity cannot be negative")

        self.time = initial_DynamicNode.time + self.dt
        self.dist = initial_DynamicNode.dist + initial_DynamicNode.velocity * self.dt + 0.5 * self.acc * self.dt ** 2
        self.soc = 0
        return True

    def adaptive_timestep(self, initial_velocity: float) -> float:
        dir = 1 if self.acc > 0 else -1
        dt = min(self.engine.time_step, self.engine.velocity_step / abs(self.acc))
        proposed_velocity = initial_velocity + self.acc * dt

        if dir > 0:
            velocity_boundary = (math.floor(initial_velocity / self.engine.velocity_interval) + 1) * self.engine.velocity_interval
        else:
            velocity_boundary = (math.ceil(initial_velocity / self.engine.velocity_interval) - 1) * self.engine.velocity_interval

        if dir * proposed_velocity >= dir * velocity_boundary:
            dt = (velocity_boundary - initial_velocity) / self.acc

        return dt

    def __repr__(self):
        return f"DynamicNode(velocity={self.velocity:.2f}, time={self.time:.2f}, dist={self.dist:.2f}, acc={self.acc:.2f})"
