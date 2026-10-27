import math

import pytest

from src.config import engine_default, vehicle_default
from src.engine.nodes import DynamicNode
from src.engine.dynamic_profile import DynamicProfile
from src.engine.segment_simulator import SegmentSimulator


def make_profile(segment, velocities, distances, acceleration):
    profile = []
    for velocity, distance in zip(velocities, distances):
        node = DynamicNode(segment, vehicle_default, engine_default)
        node.initialize(velocity=velocity)
        node.acc = acceleration
        node.dist = distance
        node.dt = 1.0
        profile.append(node)
    dynamic_profile = DynamicProfile(engine_default, profile)
    dynamic_profile.indexing(velocity_interval=5, distance_interval=5)
    return dynamic_profile


def assert_profile_span(profile, distance):
    assert math.isclose(profile[0].dist, 0.0)
    assert math.isclose(profile[-1].dist, distance)


def test_interpolate_by_velocity_snaps_requested_velocity(sample_segment):
    profile = make_profile(sample_segment, [50, 40], [0, 49.5], -1)

    result = profile.nodes[0].interpolate(profile.nodes[1], velocity=45)

    assert result.velocity == 45
    assert result.dist > profile.nodes[0].dist
    assert result.dist < profile.nodes[1].dist


def test_interpolate_by_distance_snaps_requested_distance(sample_segment):
    profile = make_profile(sample_segment, [50, 40], [0, 10], -1)

    result = profile.nodes[0].interpolate(profile.nodes[1], distance=4)

    assert result.dist == 4
    assert profile.nodes[0].dist == 0
    assert profile.nodes[1].dist == 10


def test_backward_propagation_uses_exact_exit_node(sample_segment):
    profile = make_profile(sample_segment, [50, 40, 30, 20], [0, 10, 20, 30], -1)

    entry_velocity, result = SegmentSimulator.backward_propagation(
        profile,
        distance=15,
        exit_velocity=30,
    )

    assert result[-1].velocity == 30
    assert_profile_span(result, 15)
    assert entry_velocity == result[0].velocity


def test_backward_propagation_interpolates_exit_node(sample_segment):
    profile = make_profile(sample_segment, [50, 40, 30, 20], [0, 10, 20, 30], -1)

    _, result = SegmentSimulator.backward_propagation(
        profile,
        distance=10,
        exit_velocity=35,
    )

    assert result[-1].velocity == 35
    assert_profile_span(result, 10)


def test_backward_propagation_interpolates_entry_node(sample_segment):
    profile = make_profile(sample_segment, [50, 40, 30, 20], [0, 10, 20, 30], -1)

    _, result = SegmentSimulator.backward_propagation(
        profile,
        distance=12,
        exit_velocity=30,
    )

    assert result[-1].velocity == 30
    assert_profile_span(result, 12)


def test_backward_propagation_supports_distance_longer_than_profile(sample_segment):
    profile = make_profile(sample_segment, [50, 40, 30], [0, 10, 20], -1)

    _, result = SegmentSimulator.backward_propagation(
        profile,
        distance=30,
        exit_velocity=30,
    )

    assert result[-1].velocity == 30
    assert math.isclose(result[-1].dist - result[0].dist, 20)
    assert result[0].dist > 0


def test_backward_propagation_returns_no_profile_when_no_update_is_needed(sample_segment):
    profile = make_profile(sample_segment, [50, 40, 30], [0, 10, 20], -1)

    entry_velocity, result = SegmentSimulator.backward_propagation(
        profile,
        distance=10,
        exit_velocity=50,
    )

    assert entry_velocity == 50
    assert result == []


def test_backward_propagation_rejects_unreachable_exit_velocity(sample_segment):
    profile = make_profile(sample_segment, [50, 40, 30], [0, 10, 20], -1)

    with pytest.raises(ValueError, match="Target Exit Velocity"):
        SegmentSimulator.backward_propagation(
            profile,
            distance=10,
            exit_velocity=10,
        )


def test_backward_propagation_rejects_one_node_profile(sample_segment):
    profile = make_profile(sample_segment, [50], [0], -1)

    with pytest.raises(ValueError, match="at least two nodes"):
        SegmentSimulator.backward_propagation(
            profile,
            distance=10,
            exit_velocity=30,
        )


def test_backward_propagation_handles_acceleration_direction(sample_segment):
    profile = make_profile(sample_segment, [0, 10, 20], [0, 10, 20], 1)

    entry_velocity, result = SegmentSimulator.backward_propagation(
        profile,
        distance=10,
        exit_velocity=0,
    )

    assert entry_velocity == 0
    assert result == []


def test_backward_propagation_does_not_mutate_original_profile(sample_segment):
    profile = make_profile(sample_segment, [50, 40, 30], [0, 10, 20], -1)
    original_values = [(node.velocity, node.dist, node.time) for node in profile.nodes]

    SegmentSimulator.backward_propagation(
        profile,
        distance=12,
        exit_velocity=35,
    )

    assert [(node.velocity, node.dist, node.time) for node in profile.nodes] == original_values


# def test_simulate_all_runs_backward_propagation(sample_segment_simulator):
#     simulations = sample_segment_simulator.simulate_all()

#     assert set(simulations) == {"acceleration", "braking", "cruise"}
#     assert len(simulations["acceleration"]) == len(sample_segment_simulator.route.segments)
#     assert len(simulations["braking"]) == len(sample_segment_simulator.route.segments)
#     assert len(simulations["cruise"]) == len(sample_segment_simulator.route.segments)
