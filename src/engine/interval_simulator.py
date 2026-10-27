from ..config import Vehicle, Engine
from ..models import Route
from .segment_simulator import SegmentSimulator

class RouteInterval:
    def __init__(self, vehicle: Vehicle, engine: Engine, route: Route):
        self.vehicle = vehicle
        self.engine = engine
        self.route = route
        self.segment_simulators = [SegmentSimulator(vehicle, engine, segment) for segment in route.segments]

        for simulator in self.segment_simulators:
            simulator.simulate_all()

        self._backward_propagate_braking()

    def _backward_propagate_braking(self, exit_velocity: float = 0.0) -> None:
        for index in range(len(self.segment_simulators) - 1, -1, -1):
            simulator = self.segment_simulators[index]
            exit_velocity = simulator.propagate_braking(
                distance=simulator.segment.dist,
                exit_velocity=exit_velocity,
            )

