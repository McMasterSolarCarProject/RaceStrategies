from __future__ import annotations

import math
from copy import copy

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

    def Fd_calc(self, initial_velocity: float):
        self.Fd = 0.5 * constants.air_density * self.vehicle.coef_drag * self.vehicle.cross_section * ((initial_velocity + self.segment.wind_speed) ** 2)

    def Frr_calc(self):
        self.Frr = self.vehicle.coef_rr * self.vehicle.car_mass * constants.g * self.segment.gradient.cos()

    def Fg_calc(self):
        self.Fg = self.vehicle.car_mass * constants.g * self.segment.gradient.sin()

    def Ft_calc(self):
        self.Ft = self.Fm - self.Fd - self.Frr - self.Fg - self.Fb
        self.acc = self.Ft / self.vehicle.car_mass

    def Power_calc(self, initial_velocity: float = None):
        self.Power = self.torque * self.vehicle.num_motors * initial_velocity / self.vehicle.wheel_radius

    def terminal_velocity(self, torque: float = 0, Fb: float = 0) -> None | float:
        self.torque = torque
        self.Fb = Fb
        self.Fm_calc()
        self.Frr_calc()
        self.Fg_calc()
        available_force = self.Fm - self.Frr - self.Fg - self.Fb
        v_squared = available_force / (0.5 * constants.air_density * self.vehicle.coef_drag* self.vehicle.cross_section)
        if v_squared < 0:
            return None
        terminal_velocity = math.sqrt(v_squared) - self.segment.wind_speed
        return terminal_velocity if terminal_velocity > 0 else None


    def solve_cruise_state(self, velocity: float, Fb: float = 0) -> StateNode:
        self.velocity = velocity
        self.Fb = Fb
        self.Fd_calc(velocity)
        self.Frr_calc()
        self.Fg_calc()
        required_force = self.Fd + self.Frr + self.Fg + self.Fb
        self.torque = (
            required_force
            * self.vehicle.wheel_radius
            / self.vehicle.num_motors
        )
        self.Power_calc(velocity)
        self.Fm_calc()
        self.Ft_calc()
        return self

class DynamicNode(StateNode):

    def __init__(self, segment: Segment, vehicle: Vehicle = vehicle_default, engine: Engine = engine_default, torque: float = 0, Fb: float = 0):
        super().__init__(segment, vehicle, engine)

        self.torque = torque
        self.Fb = Fb

    def initialize(self, velocity: float = 0):
        self.velocity = velocity
        self.time = 0
        self.dist = 0
        self.energy = self.vehicle.battery_capacity

        self.Fm_calc()
        self.Fd_calc(velocity)
        self.Frr_calc()
        self.Fg_calc()
        self.Ft_calc()
        self.Power_calc(velocity)


    def solve_DynamicNode(self, initial_DynamicNode: DynamicNode):
        self.Fm_calc()
        self.Fd_calc(initial_DynamicNode.velocity)
        self.Frr_calc()
        self.Fg_calc()
        self.Ft_calc()
        self.Power_calc(initial_DynamicNode.velocity)
        if abs(self.acc) < self.engine.MIN_ACCELERATION:
            return False

        self.dt = self.adaptive_timestep(initial_DynamicNode.velocity)
        if self.dt <= 0:
            return False

        self.calculate_accumulated_values(initial_DynamicNode)
        return True

    def calculate_accumulated_values(self, initial_DynamicNode: DynamicNode):
        self.velocity = initial_DynamicNode.velocity + self.acc * self.dt
        if self.velocity < 0:
            raise ValueError("DynamicNode velocity cannot be negative")

        self.time = initial_DynamicNode.time + self.dt
        self.dist = initial_DynamicNode.dist + initial_DynamicNode.velocity * self.dt + 0.5 * self.acc * self.dt ** 2
        self.energy = initial_DynamicNode.energy - self.Power * self.dt

    def interpolate(self, next_node: DynamicNode, velocity : None | float = None , distance : None | float = None) -> DynamicNode:
        if distance is not None:
            if math.isclose(next_node.dist, distance):
                return copy(next_node)
            elif math.isclose(self.dist, distance):
                raise ValueError("Cannot interpolate to the same distance as the current node.")
            interpolated_node = copy(next_node)
            interpolated_node.dt = (distance - self.dist) / (next_node.dist - self.dist) * next_node.dt
            interpolated_node.calculate_accumulated_values(self)
            interpolated_node.dist = distance
        elif velocity is not None:
            if math.isclose(next_node.velocity, velocity):
                return copy(next_node)
            elif math.isclose(self.velocity, velocity):
                raise ValueError("Cannot interpolate to the same velocity as the current node.")
            interpolated_node = copy(next_node)
            interpolated_node.dt = (velocity - self.velocity) / (next_node.velocity - self.velocity) * next_node.dt
            interpolated_node.calculate_accumulated_values(self)
            interpolated_node.velocity = velocity
        return interpolated_node



    def add(self, other_node: DynamicNode) -> DynamicNode:
        """Return a profile node offset by this node's accumulated state."""
        result = copy(other_node)
        result.time += self.time
        result.dist += self.dist
        result.energy += self.energy
        return result

    def subtract(self, other_node: DynamicNode) -> DynamicNode:
        """Return a copy with another node's accumulated state removed."""
        result = copy(self)
        result.time -= other_node.time
        result.dist -= other_node.dist
        result.energy -= other_node.energy
        return result

    def __add__(self, other_node: DynamicNode) -> DynamicNode:
        return self.add(other_node)

    def __sub__(self, other_node: DynamicNode) -> DynamicNode:
        return self.subtract(other_node)

    def adaptive_timestep(self, initial_velocity: float) -> float:
        dir = 1 if self.acc > 0 else -1
        dt = min(self.engine.time_step, self.engine.velocity_step / abs(self.acc))
        proposed_velocity = initial_velocity + self.acc * dt

        velocity_boundary = dir * (math.floor(dir * initial_velocity / self.engine.velocity_interval) + 1) * self.engine.velocity_interval
        
        if dir * proposed_velocity >= dir * velocity_boundary:
            dt = (velocity_boundary - initial_velocity) / self.acc

        return dt

    def __repr__(self):
        return f"DynamicNode(velocity={self.velocity:.2f}, time={self.time:.2f}, dist={self.dist:.2f}, acc={self.acc:.2f})"
