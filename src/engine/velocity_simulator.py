from .nodes import Segment, VelocityNode
from .kinematics import Speed, UNIT_VEC, Vec, Velocity
from ..utils.graph import plot_points, plot_multiple_datasets
from .motor_calcs import motor


def simulate_speed_profile(segment: Segment, min_speed_lim: Speed = Speed(mph=0), max_speed_lim: Speed = Speed(mph=40), RESOLUTION: float = 0.01):
    min_speed = min_speed_lim
    max_speed = max_speed_lim
    velocityNodes = []
    speed = min_speed
    while speed.mps < max_speed.mps:
        v = VelocityNode(segment, speed)
        if v.solve_velocity():
            velocityNodes.append(v)
            speed = Speed(mps=speed.mps + RESOLUTION)
        else:
            break
    return velocityNodes


def simulate_speed_profile_with_mass(segment: Segment, mass: float, min_speed_lim: Speed = Speed(mph=0), max_speed_lim: Speed = Speed(mph=40), RESOLUTION: float = 0.01):
    """
    Simulate speed profile for a given segment with specified mass override.
    
    :param segment: Segment to simulate
    :param mass: Car mass (in kg)
    :param min_speed_lim: Minimum speed limit
    :param max_speed_lim: Maximum speed limit
    :param RESOLUTION: Speed resolution step
    :return: List of VelocityNode objects
    """
    min_speed = min_speed_lim
    max_speed = max_speed_lim
    velocityNodes = []
    speed = min_speed
    while speed.mps < max_speed.mps:
        v = VelocityNode(segment, speed=speed, mass=mass)
        if v.solve_velocity():
            velocityNodes.append(v)
            speed = Speed(mps=speed.mps + RESOLUTION)
        else:
            break
    return velocityNodes


def simulate_speed_profiles_multiple_masses(segment: Segment, masses: list, min_speed_lim: Speed = Speed(mph=0), max_speed_lim: Speed = Speed(mph=40), RESOLUTION: float = 0.01):
    """
    Simulate speed profiles for multiple car masses.
    
    :param segment: Segment to simulate
    :param masses: List of masses (in kg) to simulate
    :param min_speed_lim: Minimum speed limit
    :param max_speed_lim: Maximum speed limit
    :param RESOLUTION: Speed resolution step
    :return: List of node lists, one for each mass
    """
    nodes_list = []
    for mass in masses:
        nodes = simulate_speed_profile_with_mass(segment, mass, min_speed_lim, max_speed_lim, RESOLUTION)
        nodes_list.append(nodes)
        print(f"Simulated for mass {mass} kg: {len(nodes)} nodes generated.")
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
    plot_multiple_datasets([nodes], "mph", "epm", 'v_eff')
    
    # Test with multiple masses
    masses = [i for i in range(600, 700, 5)]  # Different car masses in kg
    nodes_list = simulate_speed_profiles_multiple_masses(s1, masses)
    labels = [f"Mass {mass} kg" for mass in masses]
    
    print(f"Generated {len(nodes_list)} datasets for masses: {masses}")
    plot_multiple_datasets(nodes_list, "mph", "epm", 'velocity_vs_epm_multiple_masses', labels=labels)