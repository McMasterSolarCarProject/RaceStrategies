from .nodes import VelocityNode
from .kinematics import Speed, UNIT_VEC, Vec, Velocity
from ..utils.graph import plot_points, plot_multiple_datasets

RESOLUTION = 1

def sim_velocity_an_shi(segment):
    min_speed = Speed(mph= -10)
    max_speed = Speed(mph= 60)
    velocityNodes = []
    speed = min_speed.mps
    while speed < max_speed.mps:
        v = VelocityNode(Velocity(UNIT_VEC, Speed(speed)))
        v.solve_velocity(segment)
        velocityNodes.append(v)
        speed += RESOLUTION
    return velocityNodes

if __name__ == "__main__":
    from .kinematics import Coordinate, Displacement
    from .nodes import Segment
    p0 = Coordinate(-94.417077, 39.092185, 0)
    # print(p0)
    p1 = Coordinate(-94.423673, 39.092344, 0)
    # print(p1)
    d1 = Displacement(p0, p1)
    print(d1)
    s1 = Segment(p0, p1, v_eff= Speed(kmph=40))
    nodes = sim_velocity_an_shi(s1)
    print(nodes[0].Fg, s1.gradient)
    # plot_points(nodes, x_field="speed", y_field="current", name="speed_vs_current")
    plot_multiple_datasets([nodes], "mph", "epm", 'v_eff')