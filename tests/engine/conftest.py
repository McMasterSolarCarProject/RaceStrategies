import pytest
from dataclasses import replace

from src.engine.segment_simulator import SegmentSimulator
from src.config import vehicle_default, engine_default

@pytest.fixture
def sample_segment_simulator(sample_route):
    vehicle = vehicle_default
    engine = replace(
        engine_default,
        time_step=0.1,
        velocity_step=0.5,
        velocity_interval=5.0,
        MAX_TORQUE=200,
        BRAKE=1000,
        MIN_ACCELERATION=0.1,
    )
    route = sample_route
    return SegmentSimulator(vehicle, engine, route)