from .nodes import VelocityNode
from .kinematics import Speed, UNIT_VEC, Vec, Velocity
from ..utils.graph import plot_points, plot_multiple_datasets
from .models import Motor


def simulate_speed_profile(segment: Segment, min_speed_lim: Speed = Speed(mph=10), max_speed_lim: Speed = Speed(mph=60), RESOLUTION: float = 1):
    min_speed = min_speed_lim
    max_speed = max_speed_lim
    velocityNodes = []
    speed = min_speed.mps
    motor = Motor(torque = 0)
    while speed < max_speed.mps:
        v = VelocityNode(segment, motor, Velocity(segment.unit_vector(), Speed(speed)))
        if v.solve_velocity(segment):
            velocityNodes.append(v)
            speed += RESOLUTION
        else:
            break
    return velocityNodes


# make tests for this
if __name__ == "__main__":
    from .kinematics import Coordinate, Displacement
    from .nodes import Segment
    p0 = Coordinate(39.092185, -94.417077, 10)
    # print(p1)
    p1 = Coordinate(39.092344, -94.423673, 0)
    # print(p3)
    d1 = Displacement(p0, p1)
    # d2 = Displacement(p1, p2)
    print(d1)
    s1 = Segment(p0, p1, v_eff= Speed(kmph=40))
    nodes = simulate_speed_profile(s1)
    print(nodes[0].Fg, s1.gradient)
    # plot_points(nodes, x_field="speed", y_field="current", name="speed_vs_current")
    plot_multiple_datasets([nodes], "mph", "epm", 'v_eff')