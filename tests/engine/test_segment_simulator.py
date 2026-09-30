from dataclasses import replace

from src.engine.nodes import StateNode, DynamicNode
from src.engine.segment_simulator import SegmentSimulator
from src.config import engine_default, vehicle_default
# from src.


def test_segment_simulator_acceleration(sample_segment_simulator):
    simulator = sample_segment_simulator
    # simulator.engine = replace(engine_default, MAX_TORQUE=200, MIN_ACCELERATION=0.01)
    profile = simulator.simulate_acceleration(simulator.route.segments[0])
    print(*profile[:50], sep="\n")
    assert len(profile) > 1
    assert profile[0].velocity == 0
    assert profile[0].torque == 0
    assert profile[1].torque == simulator.engine.MAX_TORQUE
    assert all(
        previous.velocity < current.velocity
        for previous, current in zip(profile, profile[1:])
    )