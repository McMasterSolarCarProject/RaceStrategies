from ..config import Vehicle, Engine
from ..models import Segment, Route
from .nodes import StateNode, DynamicNode

class SegmentSimulator:
    def __init__(self, vehicle: Vehicle, engine: Engine, route: Route):
        self.vehicle = vehicle
        self.engine = engine
        self.route = route

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
                break

        return acceleration_profile

    def simulate_braking(self) -> list[DynamicNode]:
        # Placeholder for brake profile calculation
        return []

    def simulate_cruise(self) -> list[StateNode]:
        # Placeholder for cruise profile calculation
        return []

    def simulate_regen(self) -> list[DynamicNode]:
        # Placeholder for regen profile calculation
        return []