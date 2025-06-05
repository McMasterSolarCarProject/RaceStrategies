from .nodes import *

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

        self.startSpeed = Velocity(self.segments[-1].unit_vector(), kmph=10)
        self.stopSpeed = Velocity(self.segments[-1].unit_vector(), kmph=10)
        self.total_dist = self.segments[-1].tdist

    def simulate_interval(self, TIME_STEP: float = 0.1):
        self.time_nodes = [TimeNode(power=P_STALL, velocity=self.startSpeed)]
        self.simulate_braking(-TIME_STEP)
        print(f"{len(self.brakingNodes)}")
        print("Braking Calculations End Here\n")
        brakingNode = 0
        initial_TimeNode = self.time_nodes[-1]
        self.segments[-1].tdist += 20  # avoids edgecase error: velocity doesn't reach stop v
        for segment in self.segments:
            while initial_TimeNode.dist <= segment.tdist:
                current_TimeNode = TimeNode(initial_TimeNode.time + TIME_STEP)

                if initial_TimeNode.dist >= self.brakingNodes[brakingNode].dist:
                    current_TimeNode.braking_force = BRAKE

                elif initial_TimeNode.velocity.mag < segment.v_eff.mag:
                    current_TimeNode.power = P_CONST

                else:
                    current_TimeNode.power = segment.p_eff

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
        self.brakingNodes = [TimeNode(dist=self.total_dist, braking_force=BRAKE, velocity=self.stopSpeed)]
        initial_TimeNode = self.brakingNodes[-1]
        for segment in self.segments[::-1]:
            while initial_TimeNode.dist >= segment.tdist - segment.dist:
                if initial_TimeNode.velocity.mag <= segment.v_eff.mag:  # if the velocity is under
                    current_TimeNode = TimeNode(initial_TimeNode.time + TIME_STEP, braking_force=BRAKE)
                    current_TimeNode.solve_TimeNode(initial_TimeNode, segment, TIME_STEP)
                    self.brakingNodes.append(current_TimeNode)
                    initial_TimeNode = self.brakingNodes[-1]

                    # print(initial_TimeNode)
                else:
                    return
        return


if __name__ == "__main__":
    p0 = Coordinate(-94.417077, 39.092185, 98.4698903750406)
    # print(p1)
    p1 = Coordinate(-94.423673, 39.092344, 96.25006372299582)
    # print(p2)
    p2 = Coordinate(-94.42873, 39.091094, 95.14149119999635)
    # print(p3)
    d1 = Displacement(p0, p1)
    d2 = Displacement(p1, p2)
    print(d1)
    s1 = Segment(p0, p1, Velocity(d1.unit_vector(), kmph=40), 275)
    s2 = Segment(p1, p2, Velocity(d2.unit_vector(), kmph=40), 275)
    a = SSInterval([s1, s2])
    a.simulate_interval()
    print(len(a.time_nodes))
    from ..utils.graph import plot_multiple_datasets
    # graph.plot_points(a.time_nodes, "dist", "kmph", 'whole')
    plot_multiple_datasets([a.time_nodes, a.brakingNodes], "dist", "kmph", 'd_v')
    plot_multiple_datasets([a.time_nodes, a.brakingNodes], "time", "kmph", 't_v')

