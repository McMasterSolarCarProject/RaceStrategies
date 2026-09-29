from src.models.route import Segment

from ..config import Vehicle, Engine
from ..models import Route

from .nodes import StateNode, DynamicNode

class SegmentSimulator:
    def __init__(self, vehicle: Vehicle, engine: Engine, route: Route):
        self.vehicle = vehicle
        self.engine = engine
        self.route = route

    def simulate_acceleration(self, segment: Segment) -> list[DynamicNode]:
        current_node = DynamicNode(segment, self.vehicle) # sim to max speed
        acceleration_profile = []
        while segment.speed_limit > current_node.velocity:
            next_node = current_node.adaptive_timestep()
            acceleration_profile.append(next_node)
            current_node = next_node

        # Placeholder for acceleration profile calculation
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