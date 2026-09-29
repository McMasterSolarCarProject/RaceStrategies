from src.engine.nodes import StateNode, DynamicNode
from src.engine.segment_simulator import SegmentSimulator
from src.config import Vehicle, Engine, vehicle_default, engine_default
# from src.

def test_segment_simulator_acceleration(sample_segment_simulator):
    simulator = sample_segment_simulator
    simulator.simulate_acceleration(simulator.route.segments[0])