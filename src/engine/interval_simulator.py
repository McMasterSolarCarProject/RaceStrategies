from ..config import Vehicle, Engine
from ..models import Route
from .segment_simulator import SegmentSimulator

class RouteInterval:
    def __init__(self, vehicle: Vehicle, engine: Engine, route: Route):
        self.vehicle = vehicle
        self.engine = engine
        self.route = route
        segment_simulations = SegmentSimulator(vehicle, engine, route).simulate_all()
        self.acceleration_profile = segment_simulations["acceleration"]
        self.braking_profile = segment_simulations["braking"]
        self.cruise_profile = segment_simulations["cruise"]
        self.regen_profile = segment_simulations["regen"]

    

