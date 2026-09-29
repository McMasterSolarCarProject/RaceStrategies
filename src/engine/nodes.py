from __future__ import annotations

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

    def Fd_calc(self, initial_speed: float = 0):
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

        # Initial Dynamic Node
        self.velocity = 0
        self.time = 0
        self.dist = 0
        self.soc = 0

    def solve_DynamicNode(self, initial_DynamicNode: DynamicNode):
        self.Fm_calc()
        self.Fd_calc()
        self.Frr_calc()
        self.Fg_calc()
        self.Ft_calc()
        if self.acc > 0:
            self.dt = min(self.engine.time_step, self.engine.velocity_step / self.acc)
            self.velocity = initial_DynamicNode.velocity + self.acc * self.dt
            v_interval = (initial_DynamicNode.velocity // self.engine.velocity_interval + 1) * self.engine.velocity_interval
            if self.velocity >= v_interval:
                self.dt = (v_interval - initial_DynamicNode.velocity) / self.acc
            self.velocity = initial_DynamicNode.velocity + self.acc * self.dt
            self.time = initial_DynamicNode.time + self.dt
            self.dist = initial_DynamicNode.dist + initial_DynamicNode.velocity * self.dt + 0.5 * self.acc * self.dt ** 2
            
            # finish power calcs
            self.soc = 0
    def adaptive_timestep(self):
        pass