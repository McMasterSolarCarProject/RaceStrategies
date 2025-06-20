from .nodes import *
import matplotlib.pyplot as plt

P_STALL = 100
P_CONST = 2500
BRAKE = 100


class SSInterval:
    """Represents a chain of road segments between two stop signs"""
    def __init__(self, segments: list[Segment]):
        self.segments = segments
        self.segments[0].tdist = self.segments[0].dist
        for seg_id in range(1, len(self.segments)):
            self.segments[seg_id].tdist += self.segments[seg_id - 1].tdist

        self.startSpeed = Velocity(self.segments[-1].unit_vector(), Speed(kmph=0))
        self.stopSpeed = Velocity(self.segments[-1].unit_vector(), Speed(kmph=0))
        self.total_dist = self.segments[-1].tdist

    def simulate_interval(self, TIME_STEP: float = 0.1):
        self.time_nodes = [TimeNode(torque=max_torque, velocity=self.startSpeed, soc= 100)]
        self.simulate_braking(-TIME_STEP)
        print(f"{len(self.brakingNodes)}")
        print("Braking Calculations End Here\n")
        brakingNode = 0
        initial_TimeNode = self.time_nodes[-1]
        self.segments[-1].tdist += 20  # avoids edgecase error: velocity doesn't reach stop v
        for segment in self.segments:
            # calc solar power here
            
            while initial_TimeNode.dist <= segment.tdist:
                current_TimeNode = TimeNode(initial_TimeNode.time + TIME_STEP, soc=initial_TimeNode.soc)

                if initial_TimeNode.dist >= self.brakingNodes[brakingNode].dist:
                    current_TimeNode.Fb = BRAKE

                elif initial_TimeNode.velocity.mag < segment.v_eff.mag:
                    max_torque = 1000
                    current_TimeNode.torque = max_torque

                else:
                    current_TimeNode.torque = segment.t_eff

                current_TimeNode.solve_TimeNode(initial_TimeNode, segment, TIME_STEP)
                self.time_nodes.append(current_TimeNode)

                while current_TimeNode.velocity.mag > self.brakingNodes[
                    brakingNode].velocity.mag and brakingNode + 1 < len(self.brakingNodes):
                    # index to the braking node with the same velocity
                    brakingNode += 1

                initial_TimeNode = self.time_nodes[-1]
                # print(brakingNode)
                # print(initial_TimeNode)

                if initial_TimeNode.velocity.mps <= self.stopSpeed.mps:
                    # assume this may only happen during last segment (allows to break out of for & while loop)
                    break

        print(initial_TimeNode.time)
        print(f"Overshoot: {initial_TimeNode.dist - self.total_dist}")
        for node in self.brakingNodes:
            node.time += initial_TimeNode.time

    def simulate_braking(self, TIME_STEP: float = -1):
        self.brakingNodes = [TimeNode(dist=self.total_dist, Fb=BRAKE, velocity=self.stopSpeed)]
        initial_TimeNode = self.brakingNodes[-1]
        for segment in self.segments[::-1]:
            while initial_TimeNode.dist >= segment.tdist - segment.dist:
                if initial_TimeNode.velocity.mag <= segment.v_eff.mag:  # if the velocity is under
                    current_TimeNode = TimeNode(initial_TimeNode.time + TIME_STEP, Fb=BRAKE)
                    current_TimeNode.solve_TimeNode(initial_TimeNode, segment, TIME_STEP)
                    self.brakingNodes.append(current_TimeNode)
                    initial_TimeNode = self.brakingNodes[-1]

                    # print(initial_TimeNode)
                else:
                    return
        return

def plot_multiple_datasets(datasets, x_field, y_field, name, labels=None):
    import matplotlib.pyplot as plt

    def resolve_attr(obj, attr_path):
        for attr in attr_path.split('.'):
            obj = getattr(obj, attr)
        return obj

    colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']  # Color cycle for different datasets
    plt.figure(figsize=(8, 6))  # Set figure size

    for i, points in enumerate(datasets):
        x_coords = [resolve_attr(point, x_field) for point in points]
        y_coords = [resolve_attr(point, y_field) for point in points]

        label = labels[i] if labels else f'Dataset {i + 1}'
        plt.plot(x_coords, y_coords, marker='o', linestyle='-', color=colors[i % len(colors)], label=label)

    # Labels and titles
    plt.xlabel(x_field)
    plt.ylabel(y_field)
    plt.title(f'Graph of {x_field} vs {y_field}')
    plt.legend()
    plt.grid()

    plt.show()
    plt.close()


if __name__ == "__main__":
    # from .kinematics import *
    # p0 = Coordinate( 39.092185,-94.417077, 98.4698903750406)
    # # print(p1)
    # p1 = Coordinate( 39.092344,-94.423673, 96.25006372299582)
    # # print(p2)
    # p2 = Coordinate( 39.091094, -94.42873, 95.14149119999635)
    # # print(p3)
    # d1 = Displacement(p0, p1)
    # d2 = Displacement(p1, p2)
    # print(d1)
    # s1 = Segment(p0, p1, v_eff= Speed(kmph=40), p_eff= 275)
    # s2 = Segment(p1, p2, v_eff= Speed(kmph=40), p_eff= 275)
    # a = SSInterval([s1, s2])
    from ..database.parse_route_table import parse_route_table
    a = parse_route_table("A. Independence to Topeka")
    a.simulate_interval()
    print(len(a.time_nodes))

    # from ..utils.graph import plot_multiple_datasets
    # graph.plot_points(a.time_nodes, "dist", "kmph", 'whole')
    plot_multiple_datasets([a.time_nodes, a.brakingNodes], "dist", "velocity.kmph", 'd_v')
    plot_multiple_datasets([a.time_nodes, a.brakingNodes], "time", "soc", 't_v')

