import math

from src.engine.kinematics import Coordinate, Speed, Velocity, Vec
from src.engine.nodes import DynamicNode, Segment, StateNode


def flat_segment(speed_limit_kmph=80.0, wind=None):
    return Segment(
        Coordinate(39.0, -94.0, 100.0),
        Coordinate(39.01, -94.0, 100.0),
        id=7,
        speed_limit=Speed(kmph=speed_limit_kmph),
        wind=wind or Vec(0, 0),
    )


def test_segment_keeps_route_metadata_and_displacement():
    segment = flat_segment(speed_limit_kmph=72.0)

    assert segment.id == 7
    assert segment.dist > 0
    assert segment.speed_limit.kmph == 72.0
    assert segment.displacement.dist == segment.dist
    assert "Segment 7" in str(segment)


def test_state_node_force_calculations_on_flat_segment():
    segment = flat_segment()
    node = StateNode(segment)
    node.torque = 10.0

    node.Fm_calc()
    node.Fd_calc(initial_speed_mps=12.0)
    node.Frr_calc()
    node.Fg_calc()
    node.Ft_calc()

    profile = node.profile
    assert node.Fm == profile.motor.num_motors * node.torque / profile.motor.wheel_radius
    assert math.isclose(node.Fd, 0.5 * profile.physics.air_density * profile.vehicle.coef_drag * profile.vehicle.cross_section * 12.0**2)
    assert math.isclose(node.Frr, profile.vehicle.coef_rr * profile.vehicle.car_mass * profile.physics.accel_g, rel_tol=1e-6)
    assert math.isclose(node.Fg, 0.0, abs_tol=1e-9)
    assert math.isclose(node.acc, node.Ft / profile.vehicle.car_mass)


def test_dynamic_node_solves_speed_distance_and_soc_from_initial_state():
    segment = flat_segment()
    initial = DynamicNode(segment, speed_mps=5.0)
    initial.dist = 10.0
    initial.soc = 80.0

    current = DynamicNode(segment, torque=8.0)
    current.solve_DynamicNode(initial, time_step=2.0)

    assert math.isclose(current.speed_mps, initial.speed_mps + current.acc * 2.0)
    assert math.isclose(current.dist, initial.dist + initial.speed_mps * 2.0 + 0.5 * current.acc * 2.0**2)
    assert current.speed.mps == current.speed_mps
    assert current.soc < initial.soc


def test_state_and_dynamic_nodes_expose_numerical_metric_names():
    assert "speed_mps" in StateNode.get_numerical_metrics()
    assert "soc" in DynamicNode.get_numerical_metrics()
