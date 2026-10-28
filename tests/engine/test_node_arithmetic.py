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


def test_add_offsets_profile_accumulated_state_without_mutating_nodes(sample_segment):
    engine = make_engine()
    initial_node = make_initialized_node(sample_segment, engine)
    profile_node = make_initialized_node(
        sample_segment,
        engine,
        torque=engine.MAX_TORQUE,
    )
    initial_node.time = 10
    initial_node.dist = 100
    initial_node.energy = 0.2
    profile_node.velocity = 12
    profile_node.time = 3
    profile_node.dist = 25
    profile_node.energy = 0.05

    result = initial_node + profile_node

    assert result is not profile_node
    assert (result.time, result.dist, result.energy) == (13, 125, 0.25)
    assert result.velocity == profile_node.velocity
    assert (profile_node.time, profile_node.dist, profile_node.energy) == (3, 25, 0.05)


def test_subtract_removes_accumulated_state_without_mutating_node(sample_segment):
    engine = make_engine()
    node = make_initialized_node(sample_segment, engine)
    offset = make_initialized_node(sample_segment, engine)
    node.time, node.dist, node.energy = 13, 125, 0.25
    offset.time, offset.dist, offset.energy = 10, 100, 0.2

    result = node - offset

    assert result is not node
    assert (result.time, result.dist) == (3, 25)
    assert result.energy == pytest.approx(0.05)
    assert (node.time, node.dist, node.energy) == (13, 125, 0.25)