from __future__ import annotations
from .nodes import Segment, TimeNode
import copy
import matplotlib.pyplot as plt
from .kinematics import Speed, Velocity
from .motor_calcs import motor

P_STALL = 100
MAX_TORQUE = 20
BRAKE = 1000


class SSInterval:
    """Represents a chain of road segments between two stop signs"""
    def __init__(self, segments: list[Segment]):
        self.segments = segments
        self.segments[0].tdist = self.segments[0].dist
        for seg_id in range(1, len(self.segments)):
            self.segments[seg_id].tdist = self.segments[seg_id - 1].tdist + self.segments[seg_id].dist

        self.startSpeed = Velocity(self.segments[0].unit_vector(), Speed(kmph=0))
        self.stopSpeed = Velocity(self.segments[-1].unit_vector(), Speed(kmph=0))
        self.total_dist = self.segments[-1].tdist
        # print(self.total_dist)

    def __iadd__(self, other: SSInterval):
        if not (hasattr(self, 'time_nodes') and hasattr(other, 'time_nodes')):
            print("sim interval first you goof")
            return self
        
        # Calculate offsets from current end
        time_offset = self.time_nodes[-1].time
        dist_offset = self.time_nodes[-1].dist
        
        # Add copies of other's nodes with shifted values
        for node in other.time_nodes:
            new_node = copy.copy(node)
            new_node.time += time_offset
            new_node.dist += dist_offset
            self.time_nodes.append(new_node)
            
        if hasattr(other, 'brakingNodes'):
            if not hasattr(self, 'brakingNodes'):
                self.brakingNodes = []
            for node in other.brakingNodes:
                new_node = copy.copy(node)
                new_node.time += time_offset
                new_node.dist += dist_offset
                self.brakingNodes.append(new_node)
            
        # Add segments and recalculate in-place tdists
        self.segments += other.segments
        self.segments[0].tdist = self.segments[0].dist
        for seg_id in range(1, len(self.segments)):
            self.segments[seg_id].tdist = self.segments[seg_id - 1].tdist + self.segments[seg_id].dist
            
        self.total_dist = self.segments[-1].tdist
        
        return self

    def simulate_interval(self, TIME_STEP: float = 0.1, VELOCITY_STEP: Speed = Speed(kmph=0.1)):
        initial_TimeNode = TimeNode(self.segments[0], speed=self.startSpeed, soc= 100)
        self.time_nodes = [initial_TimeNode]
        self.simulate_braking(-TIME_STEP, VELOCITY_STEP)
        print(f"{len(self.brakingNodes)}")
        print("Braking Calculations End Here\n")
        brakingNode = 0
        self.segments[-1].tdist += 20  # avoids edgecase error: velocity doesn't reach stop v
        for segment in self.segments:
            # calc solar power here
            
            while initial_TimeNode.dist <= segment.tdist:
                current_TimeNode = TimeNode(segment, initial_TimeNode.time + TIME_STEP, soc=initial_TimeNode.soc)

                if initial_TimeNode.dist >= self.brakingNodes[brakingNode].dist:
                    current_TimeNode.Fb = BRAKE

                elif initial_TimeNode.speed.mps < segment.v_eff.mps:
                    current_TimeNode.torque = MAX_TORQUE
                    # current_TimeNode.torque = motor.torque_from_speed(initial_TimeNode.speed)*10

                else:
                    current_TimeNode.torque = segment.t_eff

                current_TimeNode.solve_TimeNode(initial_TimeNode, TIME_STEP)
                if abs(current_TimeNode.acc * TIME_STEP) > VELOCITY_STEP.mps:
                    actual_dt = abs(VELOCITY_STEP.mps / current_TimeNode.acc)
                    current_TimeNode.solve_TimeNode(initial_TimeNode, actual_dt)
                    current_TimeNode.time = initial_TimeNode.time + actual_dt

                self.time_nodes.append(current_TimeNode)

                while current_TimeNode.speed.mps > self.brakingNodes[brakingNode].speed.mps and brakingNode + 1 < len(self.brakingNodes):
                    # index to the braking node with the same velocity
                    brakingNode += 1

                initial_TimeNode = self.time_nodes[-1]
                # print(brakingNode)
                # print(initial_TimeNode.dist)

                if initial_TimeNode.speed.mps <= self.stopSpeed.mps:
                    # assume this may only happen during last segment (allows to break out of for & while loop)
                    break

        print(initial_TimeNode.time)
        print(f"Overshoot: {initial_TimeNode.dist - self.total_dist}")
        for node in self.brakingNodes:
            node.time += initial_TimeNode.time

    def simulate_braking(self, TIME_STEP: float = -0.1, VELOCITY_STEP: Speed = Speed(kmph=0.1)):
        initial_TimeNode = TimeNode(self.segments[-1], dist=self.total_dist, speed=self.stopSpeed)
        self.brakingNodes = [initial_TimeNode]
        for segment in self.segments[::-1]:
            while initial_TimeNode.dist >= segment.tdist - segment.dist:
                if initial_TimeNode.speed.mps <= segment.speed_limit.mps:  # if the velocity is under
                    current_TimeNode = TimeNode(segment, initial_TimeNode.time + TIME_STEP, Fb=BRAKE)
                    current_TimeNode.solve_TimeNode(initial_TimeNode, TIME_STEP)

                    if abs(current_TimeNode.acc * TIME_STEP) > VELOCITY_STEP.mps:
                        actual_dt = -abs(VELOCITY_STEP.mps / current_TimeNode.acc)
                        current_TimeNode.solve_TimeNode(initial_TimeNode, actual_dt)
                        current_TimeNode.time = initial_TimeNode.time + actual_dt

                    self.brakingNodes.append(current_TimeNode)
                    
                    initial_TimeNode = self.brakingNodes[-1]

                    # print(initial_TimeNode)
                else:
                    return
        return
    
    def get_coordinate_pairs(self) -> list[tuple]:
        pair_list = []
        pair_list.append((self.segments[0].p1.lat, self.segments[0].p1.lon))
    
        for segment in self.segments:
            pair_list.append((segment.p2.lat, segment.p2.lon))
        return pair_list

    def plot(self, x: str, y: str, name: str):
        from ..utils.graph import plot_SSInterval
        return plot_SSInterval([self.time_nodes if hasattr(self, 'brakingNodes') else []], x, y, name)


def join_intervals(intervals: list[SSInterval]) -> SSInterval:
    """Combines a list of intervals into a single master interval using proxies to save memory."""
    if not intervals:
        return None
    
    # Start with a copy of the first one to avoid modifying it
    result = SSInterval(intervals[0].segments[:])
    if hasattr(intervals[0], 'time_nodes'):
        result.time_nodes = intervals[0].time_nodes[:]
    if hasattr(intervals[0], 'brakingNodes'):
        result.brakingNodes = intervals[0].brakingNodes[:]
    
    for i in range(1, len(intervals)):
        result += intervals[i]
        
    return result


def test_1():
    from .kinematics import Coordinate, Displacement
    p0 = Coordinate( 39.092185,-94.417077, 98.4698903750406)
    # print(p1)
    p1 = Coordinate( 39.092344,-94.423673, 96.25006372299582)
    # print(p2)
    p2 = Coordinate( 39.091094, -94.42873, 95.14149119999635)
    # print(p3)
    d1 = Displacement(p0, p1)
    d2 = Displacement(p1, p2)
    print(d1)
    s1 = Segment(p0, p1, v_eff= Speed(kmph=40), p_eff= 275)
    s2 = Segment(p1, p2, v_eff= Speed(kmph=40), p_eff= 275)
    a = SSInterval([s1, s2])

def test_2():
    from ..database.fetch_route_intervals import fetch_route_intervals
    a = fetch_route_intervals("A. Independence to Topeka", max_nodes=100)
    a.simulate_interval()
    print(len(a.time_nodes))

    # from ..utils.graph import plot_multiple_datasets
    # graph.plot_points(a.time_nodes, "dist", "kmph", 'whole')
    a.plot("dist", ["speed.kmph"], 'd_v')
    a.plot("time", "soc", 't_v')
    # plot_multiple_datasets([a.time_nodes, a.brakingNodes], "dist", "velocity.kmph", 'd_v')
    # plot_multiple_datasets([a.time_nodes, a.brakingNodes], "time", "soc", 't_v')
    import matplotlib.pyplot as plt
    plt.show()    # finally block so they don’t vanish


if __name__ == "__main__":
    # test_1()
    test_2()

