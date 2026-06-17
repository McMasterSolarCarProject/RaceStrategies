from .nodes import Segment, StateNode
from .kinematics import Speed
from ..utils.graph import plot_multiple_datasets


def node_epm(node: StateNode) -> float:
    """Compute energy-per-meter from power draw and speed."""
    if node.speed.mps <= 0:
        return float("inf")
    return node.P_in / node.speed.mps


def simulate_speed_profile(
    segment: Segment,
    min_speed_lim: Speed = Speed(kmph=10),
    max_speed_lim: Speed = Speed(kmph=60),
    resolution_step_mps: float = 0.01,
) -> list[StateNode]:
    min_speed = min_speed_lim
    max_speed = max_speed_lim
    velocity_nodes: list[StateNode] = []
    speed = min_speed

    while speed.mps < max_speed.mps:
        state_node = StateNode(segment, speed=speed)
        if state_node.solve_cruise_state():
            velocity_nodes.append(state_node)
        speed = Speed(mps=speed.mps + resolution_step_mps)

    return velocity_nodes


def choose_closest_epm_node(nodes: list[StateNode], epm_target: float) -> StateNode | None:
    """Return the node whose computed EPM is closest to the target."""
    if not nodes:
        return None

    valid_nodes = [node for node in nodes if node.speed.mps > 0]
    if not valid_nodes:
        return None

    return min(valid_nodes, key=lambda node: abs(node_epm(node) - epm_target))


def simulate_speed_profile_with_mass(segment: Segment, min_speed_lim: Speed = Speed(mph=0), max_speed_lim: Speed = Speed(mph=40), resolution_step_mps: float = 0.01):
    """
    Simulate speed profile for a given segment with specified mass override.
    
    :param segment: Segment to simulate
    :param mass: Car mass (in kg)
    :param min_speed_lim: Minimum speed limit
    :param max_speed_lim: Maximum speed limit
    :param RESOLUTION: Speed resolution step
    :return: List of StateNode objects
    """
    min_speed = min_speed_lim
    max_speed = max_speed_lim
    velocity_nodes = []
    speed = min_speed
    while speed.mps < max_speed.mps:
        state_node = StateNode(segment, speed=speed)
        if state_node.solve_cruise_state():
            velocity_nodes.append(state_node)
        speed = Speed(mps=speed.mps + resolution_step_mps)
    return velocity_nodes


def simulate_speed_profiles_multiple_masses(segment: Segment, masses: list, min_speed_lim: Speed = Speed(mph=0), max_speed_lim: Speed = Speed(mph=40), resolution_step_mps: float = 0.01):
    """
    Simulate speed profiles for multiple car masses.
    
    :param segment: Segment to simulate
    :param masses: List of masses (in kg) to simulate
    :param min_speed_lim: Minimum speed limit
    :param max_speed_lim: Maximum speed limit
    :param RESOLUTION: Speed resolution step
    :return: List of node lists, one for each mass
    """
    from ..utils import constants
    
    original_profile = constants.get_active_profile()
    nodes_list = []
    for mass in masses:
        constants.set_active_profile(original_profile.override("vehicle.car_mass", mass))
        nodes = simulate_speed_profile_with_mass(segment, min_speed_lim, max_speed_lim, resolution_step_mps)
        nodes_list.append(nodes)
        print(f"Simulated for mass {mass} kg: {len(nodes)} nodes generated.")
    constants.set_active_profile(original_profile)  # restore original profile
    return nodes_list


# make tests for this
if __name__ == "__main__":
    from .kinematics import Coordinate, Displacement
    from .nodes import Segment
    p0 = Coordinate(39.092185, -94.417077, 0)
    # print(p1)
    p1 = Coordinate(39.092344, -94.423673, 0)
    # print(p3)
    d1 = Displacement(p0, p1)
    # d2 = Displacement(p1, p2)
    print(f"d1: {d1}")
    s1 = Segment(p0, p1, v_eff= Speed(kmph=40))
    nodes = simulate_speed_profile(s1)
    print(f"nodes[0].Fg: {nodes[0].Fg}, s1.gradient: {s1.gradient}")
    # plot_points(nodes, x_field="mph", y_field="epm", name="speed_vs_current")
    plot_multiple_datasets([nodes], "mph", "P_in", 'v_eff')
    
    # Test with multiple masses
    masses = [i for i in range(650, 701, 25)]  # Different car masses in kg
    nodes_list = simulate_speed_profiles_multiple_masses(s1, masses)
    labels = [f"Mass {mass} kg" for mass in masses]
    
    print(f"Generated {len(nodes_list)} datasets for masses: {masses}")
    plot_multiple_datasets(nodes_list, "mph", ["Fd", "Frr"], 'velocity_vs_power_multiple_masses', labels=labels)
    plot_multiple_datasets(nodes_list, "mph", ["P_in"], 'velocity_vs_power_multiple_masses', labels=labels)