import pytest
from src.engine.segment_simulator import SegmentSimulator
from src.models import Route, NULL_SEGMENT
from src.config import Vehicle, Engine, vehicle_default, engine_default

@pytest.fixture
def sample_segment_simulator(sample_route):
    vehicle = vehicle_default
    engine = engine_default
    route = sample_route
    return SegmentSimulator(vehicle, engine, route)