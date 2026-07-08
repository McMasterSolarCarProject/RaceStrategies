from __future__ import annotations
from .nodes import INITIAL_DYNAMIC_NODE, Segment, DynamicNode
import copy
import matplotlib.pyplot as plt
import numpy as np
from .kinematics import Speed
from ..config import CarProfile, DEFAULT_PROFILE

P_STALL = 100
MAX_TORQUE = 25
BRAKE = 1000


class RouteInterval:
    """Represents a contiguous route interval made of road segments and dynamic nodes."""

    def __init__(self, segments: list[Segment], profile: CarProfile = DEFAULT_PROFILE, target_profile: np.ndarray | None = None):
        self.segments = segments
        self.profile = profile
        self.segments[0].tdist = self.segments[0].dist
        for seg_id in range(1, len(self.segments)):
            self.segments[seg_id].tdist = self.segments[seg_id - 1].tdist + self.segments[seg_id].dist
        self.total_dist = self.segments[-1].tdist
        self.target_profile = self._build_target_profile(target_profile)
        # print(self.total_dist)

        self.start_speed_mps = 0.0
        self.stop_speed_mps = 0.0
        self.TIME_STEP = 1
        self.VELOCITY_STEP_MPS = Speed(kmph=1).mps

    def _build_target_profile(self, target_profile: np.ndarray | None) -> np.ndarray:
        default_profile = np.array([[seg.id, 0.0, 0.0] for seg in self.segments], dtype=float)
        if target_profile is None:
            return default_profile

        profile = np.asarray(target_profile, dtype=float)
        if profile.ndim != 2 or profile.shape[1] != 3:
            raise ValueError("target_profile must be a 2D array with columns [segment_id, target_speed_mps, target_torque]")
        if profile.shape[0] != len(self.segments):
            raise ValueError(f"target_profile row count ({profile.shape[0]}) does not match segments ({len(self.segments)})")
        return profile

    def set_target_profile(self, target_speed_kmph: list[float], target_torque: list[float] | None = None) -> None:
        if len(target_speed_kmph) != len(self.segments):
            raise ValueError(f"target_speed list length ({len(target_speed_kmph)}) != segments ({len(self.segments)})")

        target_torque = target_torque if target_torque is not None else [0.0] * len(self.segments)
        if len(target_torque) != len(self.segments):
            raise ValueError(f"target_torque list length ({len(target_torque)}) != segments ({len(self.segments)})")

        for index, (segment, speed_kmph, torque) in enumerate(zip(self.segments, target_speed_kmph, target_torque)):
            speed_mps = Speed(kmph=min(speed_kmph, segment.speed_limit.kmph) if segment.speed_limit.mps > 0 else speed_kmph).mps
            self.target_profile[index, 0] = segment.id
            self.target_profile[index, 1] = speed_mps
            self.target_profile[index, 2] = torque

    def simulate_interval(self):
        initial_dynamic_node = copy.deepcopy(INITIAL_DYNAMIC_NODE)
        initial_dynamic_node.profile = self.profile
        initial_dynamic_node.speed_mps = self.start_speed_mps
        if len(self.target_profile) > 0:
            initial_dynamic_node.target_speed_mps = float(self.target_profile[0, 1])
            initial_dynamic_node.target_torque = float(self.target_profile[0, 2])
        self.time_nodes = [initial_dynamic_node]
        self.simulate_braking()
        # print(f"# Braking Nodes: {len(self.braking_nodes)}")
        braking_node_index = 0
        stopped = False
        for segment_index, segment in enumerate(self.segments):
            if stopped:
                break

            target_speed_mps = float(self.target_profile[segment_index, 1])
            target_torque = float(self.target_profile[segment_index, 2])

            while initial_dynamic_node.dist <= segment.tdist:
                current_dynamic_node = DynamicNode(segment, profile=self.profile)
                current_dynamic_node.target_speed_mps = target_speed_mps
                current_dynamic_node.target_torque = target_torque

                while initial_dynamic_node.speed_mps > self.braking_nodes[braking_node_index].speed_mps and braking_node_index + 1 < len(self.braking_nodes):
                    # index to the braking node with the same velocity
                    braking_node_index += 1

                while initial_dynamic_node.speed_mps < self.braking_nodes[braking_node_index - 1].speed_mps and braking_node_index > 0:
                    # index to the braking node with the same velocity
                    braking_node_index -= 1

                if initial_dynamic_node.dist >= self.braking_nodes[braking_node_index].dist:
                    current_dynamic_node.Fb = BRAKE

                elif initial_dynamic_node.speed_mps < target_speed_mps:
                    current_dynamic_node.torque = MAX_TORQUE
                    # current_DynamicNode.torque = motor.torque_from_speed(initial_DynamicNode.speed)*10

                else:
                    current_dynamic_node.torque = target_torque

                self.adaptive_timestep(current_dynamic_node, initial_dynamic_node)

                # # Stall detection: motor can't overcome hill, skip to next segment
                # if current_dynamic_node.speed.mps <= 0 and initial_dynamic_node.speed.mps <= 0:
                #     Fg = self.profile.vehicle.car_mass * self.profile.physics.accel_g * segment.gradient.sin()
                #     Fm_max = MAX_TORQUE / self.profile.motor.wheel_radius * self.profile.motor.num_motors
                #     if Fm_max < Fg:
                #         print(f"Stall: segment {segment.id} too steep (Fg={Fg:.1f}N > Fm_max={Fm_max:.1f}N), skipping")
                #         # Jump the car to the end of this segment so the while loop advances
                #         current_dynamic_node.dist = segment.tdist
                #         current_dynamic_node.speed = Speed(0)
                #         self.time_nodes.append(current_dynamic_node)
                #         initial_dynamic_node = self.time_nodes[-1]
                #         break

                self.time_nodes.append(current_dynamic_node)

                initial_dynamic_node = self.time_nodes[-1]
                # print(brakingNode)
                # print(initial_DynamicNode.dist)

                if initial_dynamic_node.speed_mps <= self.stop_speed_mps:
                    # break out of both while and for loops
                    stopped = True
                    break

        # print(initial_DynamicNode.time)
        # print(f"Overshoot: {initial_DynamicNode.dist - self.total_dist}, Speed (kmph): {initial_DynamicNode.speed.kmph}")
        for node in self.braking_nodes:
            node.time += initial_dynamic_node.time

    def simulate_braking(self):
        initial_dynamic_node = copy.deepcopy(INITIAL_DYNAMIC_NODE)
        initial_dynamic_node.profile = self.profile
        initial_dynamic_node.dist = self.total_dist
        initial_dynamic_node.speed_mps = self.stop_speed_mps

        self.braking_nodes = [initial_dynamic_node]
        for segment in self.segments[::-1]:
            while initial_dynamic_node.dist >= segment.tdist - segment.dist:
                if initial_dynamic_node.speed_mps <= segment.speed_limit.mps:  # if the velocity is under
                    current_dynamic_node = DynamicNode(segment, initial_dynamic_node.time - self.TIME_STEP, Fb=BRAKE, profile=self.profile)
                    self.adaptive_timestep(current_dynamic_node, initial_dynamic_node, backward=True)

                    self.braking_nodes.append(current_dynamic_node)

                    initial_dynamic_node = self.braking_nodes[-1]

                    # print(initial_DynamicNode)
                else:
                    return
        return

    def adaptive_timestep(self, current_dynamic_node: DynamicNode, initial_dynamic_node: DynamicNode, backward: bool = False):
        direction = -1 if backward else 1
        current_dynamic_node.solve_DynamicNode(initial_dynamic_node, direction * self.TIME_STEP)

        if abs(current_dynamic_node.acc * self.TIME_STEP) > self.VELOCITY_STEP_MPS:
            dt = direction * abs(self.VELOCITY_STEP_MPS / current_dynamic_node.acc)
            current_dynamic_node.solve_DynamicNode(initial_dynamic_node, dt)
            # current_dynamic_node.time = initial_dynamic_node.time + dt

    def get_coordinate_pairs(self) -> list[tuple]:
        pair_list = []
        pair_list.append((self.segments[0].p1.lat, self.segments[0].p1.lon))

        for segment in self.segments:
            pair_list.append((segment.p2.lat, segment.p2.lon))
        return pair_list

    def plot(self, x: str, y: str, name: str, brake: bool = True, xlabel=None, ylabel=None, title=None):
        from ..utils.graph import plot_RouteInterval

        if not brake:
            return plot_RouteInterval(
                [self.time_nodes],
                x,
                y,
                name,
                xlabel=xlabel,
                ylabel=ylabel,
                title=title,
            )
        return plot_RouteInterval(
            [self.time_nodes, self.braking_nodes if hasattr(self, "braking_nodes") else []],
            x,
            y,
            name,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )

    def __iadd__(self, other: RouteInterval):
        if not (hasattr(self, "time_nodes") and hasattr(other, "time_nodes")):
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

        if hasattr(other, "braking_nodes"):
            if not hasattr(self, "braking_nodes"):
                self.braking_nodes = []
            for node in other.braking_nodes:
                new_node = copy.copy(node)
                new_node.time += time_offset
                new_node.dist += dist_offset
                self.braking_nodes.append(new_node)

        # Add segments and recalculate in-place tdists
        self.segments += other.segments
        self.target_profile = np.concatenate([self.target_profile, other.target_profile], axis=0)
        self.segments[0].tdist = self.segments[0].dist
        for seg_id in range(1, len(self.segments)):
            self.segments[seg_id].tdist = self.segments[seg_id - 1].tdist + self.segments[seg_id].dist

        self.total_dist = self.segments[-1].tdist

        return self


def join_intervals(intervals: list[RouteInterval]) -> RouteInterval:
    """Combines a list of intervals into a single master interval using proxies to save memory."""
    if not intervals:
        return None

    # Start with a copy of the first one to avoid modifying it
    result = RouteInterval(intervals[0].segments[:], profile=intervals[0].profile)
    if hasattr(intervals[0], "time_nodes"):
        result.time_nodes = intervals[0].time_nodes[:]
    if hasattr(intervals[0], "braking_nodes"):
        result.braking_nodes = intervals[0].braking_nodes[:]
    if hasattr(intervals[0], "target_profile"):
        result.target_profile = intervals[0].target_profile.copy()

    for i in range(1, len(intervals)):
        result += intervals[i]

    return result


def test_1():
    from .kinematics import Coordinate, Displacement

    p0 = Coordinate(39.092185, -94.417077, 98.4698903750406)
    # print(p1)
    p1 = Coordinate(39.092344, -94.423673, 96.25006372299582)
    # print(p2)
    # p2 = Coordinate( 39.091094, -94.42873, 95.14149119999635)
    # print(p3)
    d1 = Displacement(p0, p1)
    # d2 = Displacement(p1, p2)
    print(d1)
    # s1 = Segment(p0, p1)
    # s2 = Segment(p1, p2)
    # a = RouteInterval([s1, s2])


def test_2():
    from ..database.fetch_route_intervals import fetch_route_intervals

    a = fetch_route_intervals("A. Independence to Topeka", max_nodes=100)
    a.simulate_interval()
    print(len(a.time_nodes))

    # from ..utils.graph import plot_multiple_datasets
    # graph.plot_points(a.time_nodes, "dist", "kmph", 'whole')
    a.plot("dist", ["speed_kmph", "target_speed_kmph"], "d_v", ylabel="Speed (km/h)")
    a.plot("dist", ["speed_kmph", "target_torque", "torque"], "d_v")
    # a.plot("time", "soc", 't_v')
    # plot_multiple_datasets([a.time_nodes, a.brakingNodes], "dist", "velocity.kmph", 'd_v')
    # plot_multiple_datasets([a.time_nodes, a.brakingNodes], "time", "soc", 't_v')
    plt.show()  # finally block so they don’t vanish


if __name__ == "__main__":
    # test_1()
    test_2()
