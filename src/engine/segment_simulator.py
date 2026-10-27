from copy import copy
import math

from ..config import Vehicle, Engine
from ..models import Segment
from .nodes import StateNode, DynamicNode
from .dynamic_profile import DynamicProfile

class SegmentSimulator:
    def __init__(self, vehicle: Vehicle, engine: Engine, segment: Segment):
        self.vehicle = vehicle
        self.engine = engine
        self.segment = segment

    def simulate_all(self):
        state_node = StateNode(self.segment, self.vehicle, self.engine)
        # acceleration
        self.acceleration_terminal_velocity = state_node.terminal_velocity(torque=self.engine.MAX_TORQUE)
        if self.acceleration_terminal_velocity is None:
            raise ValueError("Acceleration terminal velocity is None. Check engine and vehicle parameters.")
        self.acceleration_profile = []
        if 0 < self.acceleration_terminal_velocity:
            self.acceleration_profile.append(self.simulate_profile(initial_velocity=0, dir=1, torque=self.engine.MAX_TORQUE))
        if self.acceleration_terminal_velocity < self.segment.speed_limit:
            self.acceleration_profile.append(self.simulate_profile(initial_velocity=self.segment.speed_limit, dir=-1, torque=self.engine.MAX_TORQUE))

        # braking
        self.braking_terminal_velocity = state_node.terminal_velocity(torque=0, Fb=self.engine.BRAKE)
        if self.braking_terminal_velocity:
            raise ValueError("Braking terminal velocity is not 0. Check engine and vehicle parameters.")
        self.braking_profile = [self.simulate_profile(initial_velocity=self.segment.speed_limit, dir=-1, Fb=self.engine.BRAKE)]

        regen_force = 0
        self.regen_terminal_velocity = state_node.terminal_velocity(torque=0, Fb=regen_force)
        self.regen_profile = []
        if self.regen_terminal_velocity is not None and 0 < self.regen_terminal_velocity:
            self.regen_profile.append(self.simulate_profile(initial_velocity=0, dir=1, Fb=regen_force))
        if self.regen_terminal_velocity is None or self.regen_terminal_velocity < self.segment.speed_limit:
            self.regen_profile.append(self.simulate_profile(initial_velocity=self.segment.speed_limit, dir=-1, Fb=regen_force))

    def propagate_braking(self, distance: float, exit_velocity: float) -> float:
        entry_velocity, self.propagated_braking_profile = self.backward_propagation(
            self.braking_profile[0],
            distance=distance,
            exit_velocity=exit_velocity,
        )
        return entry_velocity
    
    def simulate_profile(self, initial_velocity: float = 0, dir: int = 1, torque: float = 0, Fb: float = 0) -> DynamicProfile:
        segment = self.segment
        initial_node = DynamicNode(segment, self.vehicle, self.engine, torque=torque, Fb=Fb)
        initial_node.initialize(velocity=initial_velocity)
        profile = [initial_node]
        while dir * initial_node.velocity < max(0, dir * self.segment.speed_limit):
            current_node = DynamicNode(segment, self.vehicle, self.engine, torque=torque, Fb=Fb)
            if not current_node.solve_DynamicNode(initial_node):
                break
            profile.append(current_node)
            initial_node = current_node

            if abs(initial_node.acc) < self.engine.MIN_ACCELERATION:
                break
        dynamic_profile = DynamicProfile(self.engine, profile)
        dynamic_profile.indexing(velocity_interval=self.engine.profile_velocity_interval, distance_interval=self.engine.profile_distance_interval)
        return dynamic_profile



    def simulate_cruise(self) -> list[StateNode]:
        cruise_profile = []
        velocity = 0.0
        interval = self.engine.profile_velocity_interval

        while True:
            state = StateNode(self.segment, self.vehicle, self.engine)
            state.solve_cruise_state(velocity)
            if 0 <= state.torque <= self.engine.MAX_TORQUE:
                cruise_profile.append(state)

            if math.isclose(velocity, self.segment.speed_limit):
                break
            velocity = min(velocity + interval, self.segment.speed_limit)

        return cruise_profile

    @staticmethod
    def backward_propagation(profile: DynamicProfile, distance, exit_velocity):
        nodes = profile.nodes
        if len(nodes) < 2:
            # possible problem
            raise ValueError("Profile must contain at least two nodes for backward propagation.")

        direction = profile.dir
        new_dynamic_profile = []

        if direction * exit_velocity < direction * profile.start_velocity or math.isclose(exit_velocity, profile.start_velocity):
            return profile.start_velocity, new_dynamic_profile
        elif direction * profile.end_velocity < direction * exit_velocity:
            # asymptote problem, will happen
            raise ValueError(f"Profile Start Velocity {profile.start_velocity}, Profile Exit Velocity {profile.end_velocity}, Target Exit Velocity {exit_velocity}")

        exit_bucket = profile.index_at(velocity=exit_velocity)
        exit_node_index = profile._binary_upper_node(exit_velocity, "velocity", direction, profile.velocity_index, exit_bucket)
        exit_node = profile.node_at(velocity=exit_velocity, precise=True)

        # assume node 0 has distance = 0
        if exit_node.dist < distance:
            entry_node_index = 0
            bias_node = nodes[0] - nodes[0]
            bias_node.dist = exit_node.dist - distance
        else:
            entry_distance = exit_node.dist - distance
            entry_bucket = profile.index_at(distance=entry_distance)
            entry_node_index = profile._binary_upper_node(entry_distance, "dist", 1, profile.distance_index, entry_bucket)
            entry_node = profile.node_at(distance=entry_distance, precise=True)
            bias_node = copy(entry_node)
            if not math.isclose(entry_node.dist, nodes[entry_node_index].dist):
                new_dynamic_profile.append(entry_node - bias_node)

        for node in range(entry_node_index, exit_node_index):
            new_dynamic_profile.append(nodes[node] - bias_node)

        new_dynamic_profile.append(exit_node - bias_node)
        return new_dynamic_profile[0].velocity, new_dynamic_profile