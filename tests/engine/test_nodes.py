from dataclasses import replace

import pytest

from src.config import engine_default, vehicle_default
from src.engine.nodes import DynamicNode


def make_engine(**changes):
    return replace(
        engine_default,
        time_step=1.0,
        velocity_step=100.0,
        **changes,
    )


def make_initialized_node(segment, engine, *, torque=0, Fb=0):
    node = DynamicNode(
        segment,
        vehicle_default,
        engine,
        torque=torque,
        Fb=Fb,
    )
    node.initialize()
    return node


def test_initialize_creates_zero_state_without_motor_torque(sample_segment):
    node = make_initialized_node(sample_segment, make_engine())

    assert node.velocity == 0
    assert node.time == 0
    assert node.dist == 0
    assert node.torque == 0


def test_solve_advances_positive_acceleration(sample_segment):
    engine = make_engine(MAX_TORQUE=200, MIN_ACCELERATION=0.01)
    initial_node = make_initialized_node(sample_segment, engine)
    next_node = DynamicNode(sample_segment,vehicle_default, engine,torque=engine.MAX_TORQUE)

    assert next_node.solve_DynamicNode(initial_node)
    assert next_node.dt > 0
    assert next_node.velocity > initial_node.velocity


def test_solve_clamps_acceleration_from_five_to_next_interval(sample_segment):
    engine = make_engine(MAX_TORQUE=200, MIN_ACCELERATION=0.01)
    initial_node = make_initialized_node(sample_segment, engine)
    initial_node.velocity = 9
    next_node = DynamicNode(
        sample_segment,
        vehicle_default,
        engine,
        torque=engine.MAX_TORQUE,
    )

    assert next_node.solve_DynamicNode(initial_node)
    assert next_node.velocity == 10
    assert next_node.dt > 0


def test_solve_clamps_braking_from_ten_to_next_lower_interval(sample_segment):
    engine = make_engine(MIN_ACCELERATION=0.01, velocity_interval=5)
    initial_node = make_initialized_node(sample_segment, engine)
    initial_node.velocity = 10
    next_node = DynamicNode(sample_segment,vehicle_default,engine,Fb=10_000)
    
    assert next_node.solve_DynamicNode(initial_node)
    assert next_node.velocity == 5
    assert next_node.dt > 0


def test_solve_clamps_braking_from_fifteen_to_next_lower_interval(sample_segment):
    engine = make_engine(MIN_ACCELERATION=0.01, velocity_interval=5)
    initial_node = make_initialized_node(sample_segment, engine)
    initial_node.velocity = 15
    next_node = DynamicNode(
        sample_segment,
        vehicle_default,
        engine,
        Fb=10_000,
    )

    assert next_node.solve_DynamicNode(initial_node)
    assert next_node.velocity == 10
    assert next_node.dt > 0


def test_solve_clamps_braking_from_three_to_zero(sample_segment):
    engine = make_engine(MIN_ACCELERATION=0.01, velocity_interval=5)
    initial_node = make_initialized_node(sample_segment, engine)
    initial_node.velocity = 3
    next_node = DynamicNode(
        sample_segment,
        vehicle_default,
        engine,
        Fb=10_000,
    )

    assert next_node.solve_DynamicNode(initial_node)
    assert next_node.velocity == 0
    assert next_node.dt > 0


def test_solve_rejects_braking_from_rest(sample_segment):
    engine = make_engine(MIN_ACCELERATION=0.01)
    initial_node = make_initialized_node(sample_segment, engine)
    next_node = DynamicNode(sample_segment, vehicle_default, engine, Fb=10_000)

    with pytest.raises(ValueError, match="velocity cannot be negative"):
        next_node.solve_DynamicNode(initial_node)


def test_solve_rejects_acceleration_below_minimum(sample_segment):
    engine = make_engine(MIN_ACCELERATION=1)
    initial_node = make_initialized_node(sample_segment, engine)
    next_node = DynamicNode(sample_segment, vehicle_default, engine)

    assert not next_node.solve_DynamicNode(initial_node)
    assert not hasattr(next_node, "velocity")