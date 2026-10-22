from copy import copy
import math
from ..config import Vehicle, Engine
from ..models import Segment, Route
from .nodes import StateNode, DynamicNode

class SegmentSimulator:
    def __init__(self, vehicle: Vehicle, engine: Engine, route: Route):
        self.vehicle = vehicle
        self.engine = engine
        self.route = route

    def simulate_all(self) -> dict[str, list[StateNode]]:
        segments = self.route.segments
        acceleration_profiles = []
        braking_profiles = []
        cruise_profiles = []

        for segment in segments:
            acceleration_profiles.append(self.simulate_acceleration(segment))
            braking_profiles.append(self.simulate_braking(segment))
            cruise_profiles.append(self.simulate_cruise())

        exit_velocity = 0
        for segment in range(len(segments)-1, -1 , -1):
            exit_velocity, profile = self.backward_propagation(braking_profiles[segment], segments[segment].dist, exit_velocity)
            braking_profiles[segment] = profile

        return {
            "acceleration": acceleration_profiles,
            "braking": braking_profiles,
            "cruise": cruise_profiles,
        }

    def simulate(self, segment: Segment, torque: float = 0, Fb: float = 0) -> list[DynamicNode]:
        initial_node = DynamicNode(segment, self.vehicle, self.engine, torque=torque, Fb=Fb)
        initial_node.initialize()
        pass

    def simulate_acceleration(self, segment: Segment) -> list[DynamicNode]:
        initial_node = DynamicNode(segment, self.vehicle, self.engine) # sim to max speed
        initial_node.initialize()
        acceleration_profile = [initial_node]
        while segment.speed_limit > initial_node.velocity:
            current_node = DynamicNode(segment, self.vehicle, self.engine, torque=self.engine.MAX_TORQUE)
            if not current_node.solve_DynamicNode(initial_node):
                break
            acceleration_profile.append(current_node)
            initial_node = current_node

            if initial_node.acc < self.engine.MIN_ACCELERATION:
                if initial_node.acc < 0:
                    raise ValueError("Acceleration is negative during acceleration simulation.")
                break

        return acceleration_profile

    def simulate_braking(self, segment: Segment) -> list[DynamicNode]:
        initial_node = DynamicNode(segment, self.vehicle, self.engine) # sim to max speed
        initial_node.initialize(velocity = segment.speed_limit)
        braking_profile = [initial_node]
        while initial_node.velocity > 0:
            current_node = DynamicNode(segment, self.vehicle, self.engine, Fb=self.engine.BRAKE)
            if not current_node.solve_DynamicNode(initial_node):
                break
            braking_profile.append(current_node)
            initial_node = current_node

            if initial_node.acc > -self.engine.MIN_ACCELERATION:
                if initial_node.acc > 0:
                    raise ValueError("Acceleration is positive during braking simulation.")
                break

        return braking_profile


    def simulate_cruise(self) -> list[StateNode]:
        # Placeholder for cruise profile calculation
        return []

    @staticmethod
    def backward_propagation(profile: list[DynamicNode], distance, exit_velocity):
        if len(profile) < 2:
            # possible problem
            raise ValueError("Profile must contain at least two nodes for backward propagation.")
        
        dir = 1 if profile[1].acc > 0 else -1
        new_dynamic_profile = []

        if dir * exit_velocity < dir * profile[0].velocity or math.isclose(exit_velocity, profile[0].velocity):
            return profile[0].velocity, new_dynamic_profile
        elif dir * profile[-1].velocity < dir * exit_velocity:
            # asymptote problem, will happen
            raise ValueError(f"Profile Start Velocity {profile[0].velocity}, Profile Exit Velocity {profile[-1].velocity}, Target Exit Velocity {exit_velocity}")

        exit_node_index, exit_node = SegmentSimulator.linear_search(profile, velocity=exit_velocity)

        # assume node 0 has distance = 0
        if exit_node.dist < distance:
            entry_node_index = 0
            bias_node = profile[0] - profile[0]
            bias_node.dist = exit_node.dist - distance
        else:
            entry_node_index, entry_node = SegmentSimulator.linear_search(profile, distance=exit_node.dist - distance)
            bias_node = copy(entry_node)
            if not math.isclose(entry_node.dist, profile[entry_node_index].dist):
                new_dynamic_profile.append(entry_node - bias_node)

        for node in range(entry_node_index, exit_node_index):
            new_dynamic_profile.append(profile[node] - bias_node)

        new_dynamic_profile.append(exit_node - bias_node)
        return new_dynamic_profile[0].velocity, new_dynamic_profile

    @staticmethod
    def linear_search(profile: list[DynamicNode], distance: None | float = None, velocity: None | float = None) -> tuple[int, DynamicNode]:
        if distance is not None:
            for node in range(0, len(profile)):
                if math.isclose(profile[node].dist, distance):
                    return node, copy(profile[node])
                elif distance < profile[node].dist:
                    return node, profile[node - 1].interpolate(profile[node], distance=distance)

        elif velocity is not None:
            dir = 1 if profile[1].acc > 0 else -1
            for node in range(1, len(profile)):
                if math.isclose(profile[node].velocity, velocity):
                    return node, copy(profile[node])
                elif dir * velocity < dir * profile[node].velocity:
                    return node, profile[node - 1].interpolate(profile[node], velocity=velocity)
        raise ValueError("No matching node found.")