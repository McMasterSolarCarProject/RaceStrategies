import math

import pytest

from src.engine.dynamic_profile import DynamicProfile
from tests.engine.plotting import plot_dynamic_nodes, plot_efficiency_vs_speed


x_parameter = "time"
y_parameters = ["velocity", "torque"]#, "Fb", "acc", "dist", "soc"]


def test_simulate_profile_returns_indexed_profile(sample_segment_simulator):
    profile = sample_segment_simulator.simulate_profile(
        initial_velocity=0,
        dir=1,
        torque=sample_segment_simulator.engine.MAX_TORQUE,
    )

    assert isinstance(profile, DynamicProfile)
    assert len(profile.nodes) > 1
    assert profile.nodes[0].velocity == 0
    assert profile.nodes[0].torque == sample_segment_simulator.engine.MAX_TORQUE
    assert profile.velocity_index
    assert profile.distance_index


def test_simulate_profile_braking_is_monotonic(sample_segment_simulator):
    profile = sample_segment_simulator.simulate_profile(
        initial_velocity=sample_segment_simulator.segment.speed_limit,
        dir=-1,
        Fb=sample_segment_simulator.engine.BRAKE,
    )

    assert profile.nodes[0].velocity == sample_segment_simulator.segment.speed_limit
    assert all(
        previous.velocity > current.velocity
        for previous, current in zip(profile.nodes, profile.nodes[1:])
    )


def test_simulate_all_populates_acceleration_braking_and_regen(sample_segment_simulator):
    result = sample_segment_simulator.simulate_all()

    assert result is None
    assert sample_segment_simulator.acceleration_profile
    assert sample_segment_simulator.braking_profile
    assert sample_segment_simulator.regen_profile
    assert all(
        isinstance(profile, DynamicProfile)
        for profile in (
            sample_segment_simulator.acceleration_profile
            + sample_segment_simulator.braking_profile
            + sample_segment_simulator.regen_profile
        )
    )


def test_simulate_cruise_contains_feasible_steady_states(sample_segment_simulator):
    profile = sample_segment_simulator.simulate_cruise()

    assert profile
    assert profile[0].velocity == 0
    assert profile[-1].velocity <= sample_segment_simulator.segment.speed_limit
    assert all(
        0 <= state.torque <= sample_segment_simulator.engine.MAX_TORQUE
        for state in profile
    )
    assert all(abs(state.acc) < 1e-12 for state in profile)


@pytest.mark.graph
def test_segment_simulator_efficiency_vs_speed(sample_segment_simulator):
    profile = sample_segment_simulator.simulate_profile(
        initial_velocity=0,
        dir=1,
        torque=sample_segment_simulator.engine.MAX_TORQUE,
    )

    figure, axis = plot_efficiency_vs_speed(profile.nodes)

    assert len(axis.lines) == 1
    assert len(axis.lines[0].get_xdata()) == len(profile.nodes)
    assert math.isnan(axis.lines[0].get_ydata()[0])


@pytest.mark.graph
def test_segment_simulator_cruise_efficiency_vs_speed(sample_segment_simulator):
    profile = sample_segment_simulator.simulate_cruise()

    figure, axis = plot_efficiency_vs_speed(profile)

    assert len(axis.lines) == 1
    assert len(axis.lines[0].get_xdata()) == len(profile)
    assert math.isnan(axis.lines[0].get_ydata()[0])
    assert all(value >= 0 for value in axis.lines[0].get_ydata()[1:])


@pytest.mark.graph
def test_segment_simulator_cruise_resistive_forces(sample_segment_simulator):
    profile = sample_segment_simulator.simulate_cruise()

    figure, axis = plot_dynamic_nodes(
        {"cruise": profile},
        x_parameter="velocity",
        y_parameters=("Frr", "Fd", "Fg", "Ft"),
        title="Cruise Resistive Forces",
    )

    assert len(axis.lines) == 4
    assert all(len(line.get_xdata()) == len(profile) for line in axis.lines)


@pytest.mark.graph
def test_segment_simulator_acceleration(sample_segment_simulator):
    simulator = sample_segment_simulator
    simulator.simulate_all()
    acceleration_profile = simulator.acceleration_profile[0].nodes
    braking_profile = simulator.braking_profile[0].nodes
    print(*acceleration_profile[:50], sep="\n")
    plot_dynamic_nodes(
        {
            "acceleration": acceleration_profile,
            "braking": braking_profile,
        },
        x_parameter=x_parameter,
        y_parameters=y_parameters,
        title="Acceleration and Braking Profiles",
    )
    assert len(acceleration_profile) > 1
    assert acceleration_profile[0].velocity == 0
    assert acceleration_profile[0].torque == simulator.engine.MAX_TORQUE
    assert acceleration_profile[1].torque == simulator.engine.MAX_TORQUE
    assert all(
        previous.velocity < current.velocity
        for previous, current in zip(acceleration_profile, acceleration_profile[1:])
    )


@pytest.mark.graph
def test_segment_simulator_braking(sample_segment_simulator):
    simulator = sample_segment_simulator
    simulator.simulate_all()
    profile = simulator.braking_profile[0].nodes
    plot_dynamic_nodes(
        {"braking": profile},
        x_parameter=x_parameter,
        y_parameters=y_parameters,
        title="Braking Profile",
    )
    assert len(profile) > 1
    assert profile[0].velocity == simulator.segment.speed_limit
    assert profile[1].Fb == simulator.engine.BRAKE
    assert all(
        previous.velocity > current.velocity
        for previous, current in zip(profile, profile[1:])
    )
