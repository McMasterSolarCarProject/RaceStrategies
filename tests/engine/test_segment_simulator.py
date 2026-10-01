from dataclasses import replace

from src.engine.nodes import StateNode, DynamicNode
from src.engine.segment_simulator import SegmentSimulator
from src.config import engine_default, vehicle_default
from tests.engine.plotting import plot_dynamic_nodes


x_parameter = "time"
y_parameters = ["velocity", "torque"]#, "Fb", "acc", "dist", "soc"]

def test_segment_simulator_acceleration(sample_segment_simulator):
    simulator = sample_segment_simulator
    # simulator.engine = replace(engine_default, MAX_TORQUE=200, MIN_ACCELERATION=0.01)
    acceleration_profile = simulator.simulate_acceleration(simulator.route.segments[0])
    braking_profile = simulator.simulate_braking(simulator.route.segments[0])
    # print(*acceleration_profile[:50], sep="\n")
    # plot_dynamic_nodes(
    #     {
    #         "acceleration": acceleration_profile,
    #         "braking": braking_profile,
    #     },
    #     x_parameter=x_parameter,
    #     y_parameters=y_parameters,
    #     title="Acceleration and Braking Profiles",
    # )
    assert len(acceleration_profile) > 1
    assert acceleration_profile[0].velocity == 0
    assert acceleration_profile[0].torque == 0
    assert acceleration_profile[1].torque == simulator.engine.MAX_TORQUE
    assert all(
        previous.velocity < current.velocity
        for previous, current in zip(acceleration_profile, acceleration_profile[1:])
    )


def test_segment_simulator_braking(sample_segment_simulator):
    simulator = sample_segment_simulator
    profile = simulator.simulate_braking(simulator.route.segments[0])
    # plot_dynamic_nodes(
    #     {"braking": profile},
    #     x_parameter=x_parameter,
    #     y_parameters=y_parameters,
    #     title="Braking Profile",
    # )
    assert len(profile) > 1
    assert profile[0].velocity == simulator.route.segments[0].speed_limit
    assert profile[1].Fb == simulator.engine.BRAKE
    assert all(
        previous.velocity > current.velocity
        for previous, current in zip(profile, profile[1:])
    )
