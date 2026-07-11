import math

import numpy as np
import pytest

from src.engine.interval_simulator import RouteInterval, join_intervals
from src.engine.kinematics import Coordinate, Speed
from src.engine.nodes import DynamicNode, Segment


def make_segments():
    p0 = Coordinate(39.0, -94.0, 100.0)
    p1 = Coordinate(39.01, -94.0, 100.0)
    p2 = Coordinate(39.02, -94.0, 101.0)
    return [
        Segment(p0, p1, id=1, speed_limit=Speed(kmph=50.0)),
        Segment(p1, p2, id=2, speed_limit=Speed(kmph=70.0)),
    ]


def test_route_interval_builds_cumulative_distances_and_default_targets():
    segments = make_segments()
    interval = RouteInterval(segments)

    assert math.isclose(segments[0].tdist, segments[0].dist)
    assert math.isclose(segments[1].tdist, segments[0].dist + segments[1].dist)
    assert interval.total_dist == segments[-1].tdist
    assert interval.target_profile.tolist() == [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]


def test_route_interval_rejects_bad_target_profile_shape():
    with pytest.raises(ValueError, match="columns"):
        RouteInterval(make_segments(), target_profile=np.array([[1.0, 2.0]]))

    with pytest.raises(ValueError, match="row count"):
        RouteInterval(make_segments(), target_profile=np.array([[1.0, 2.0, 3.0]]))


def test_set_target_profile_clamps_to_segment_speed_limits():
    interval = RouteInterval(make_segments())

    interval.set_target_profile([60.0, 65.0], target_torque=[1.5, 2.5])

    assert math.isclose(interval.target_profile[0, 1], Speed(kmph=50.0).mps)
    assert math.isclose(interval.target_profile[1, 1], Speed(kmph=65.0).mps)
    assert interval.target_profile[:, 2].tolist() == [1.5, 2.5]


def test_get_coordinate_pairs_includes_start_and_each_segment_end():
    interval = RouteInterval(make_segments())

    assert interval.get_coordinate_pairs() == [(39.0, -94.0), (39.01, -94.0), (39.02, -94.0)]


def test_join_intervals_combines_segments_and_target_profiles():
    first = RouteInterval(make_segments()[:1])
    second = RouteInterval(make_segments()[1:])
    first.set_target_profile([45.0], [3.0])
    second.set_target_profile([55.0], [4.0])
    first.time_nodes = [DynamicNode(first.segments[0])]
    first.braking_nodes = []
    second.time_nodes = [DynamicNode(second.segments[0])]
    second.braking_nodes = []

    joined = join_intervals([first, second])

    assert len(joined.segments) == 2
    assert joined.target_profile[:, 0].tolist() == [1.0, 2.0]
    assert joined.target_profile[:, 2].tolist() == [3.0, 4.0]
    assert math.isclose(joined.total_dist, joined.segments[-1].tdist)
