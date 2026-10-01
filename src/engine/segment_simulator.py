from ..config import Vehicle, Engine
from ..models import Segment, Route
from .nodes import StateNode, DynamicNode

class SegmentSimulator:
    def __init__(self, vehicle: Vehicle, engine: Engine, route: Route):
        self.vehicle = vehicle
        self.engine = engine
        self.route = route

    def simulate_all(self) -> dict[str, list[StateNode]]:
        acceleration_profile = []
        braking_profile = []
        cruise_profile = []
        regen_profile = []

        for segment in self.route.segments:
            acceleration_profile.extend(self.simulate_acceleration(segment))
            braking_profile.extend(self.simulate_braking(segment))
            cruise_profile.extend(self.simulate_cruise())
            regen_profile.extend(self.simulate_regen())

        return {
            "acceleration": acceleration_profile,
            "braking": braking_profile,
            "cruise": cruise_profile,
            "regen": regen_profile,
        }

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
        initial_node.initialize()
        initial_node.velocity = segment.speed_limit
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

    def simulate_regen(self) -> list[DynamicNode]:
        # Placeholder for regen profile calculation
        return []