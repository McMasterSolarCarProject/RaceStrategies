import copy
import math

from src.config.schema import CarProfile

from .nodes import DynamicNode, Segment
from ..utils.graph import plot_RouteInterval


class SegmentSimulator:
    def __init__(self, segment: Segment, profile: CarProfile):
        self.segment = segment
        self.profile = profile
        self.TIME_STEP = 1.0  # seconds
        self.VELOCITY_STEP_MPS = 0.1  # m/s
        self.MAX_TORQUE = 1000
        self.BRAKE_FORCE = 1000

        self.acceleration_nodes: list[DynamicNode] = []
        self.braking_nodes: list[DynamicNode] = []
        self.acceleration_speed_lookup: list[DynamicNode] = []
        self.braking_speed_lookup: list[DynamicNode] = []
        self.cruise_node: DynamicNode | None = None
        self.profile_nodes: list[DynamicNode] = []
        self.last_peak_speed_mps = 0.0

    def _seed_node(
        self,
        speed_mps: float,
        torque: float = 0.0,
        Fb: float = 0.0,
        initial_node: DynamicNode | None = None,
    ) -> DynamicNode:
        node = DynamicNode(segment=self.segment, speed_mps=speed_mps, torque=torque, Fb=Fb, profile=self.profile)
        if initial_node is not None:
            node.time = initial_node.time
            node.dist = initial_node.dist
            node.soc = initial_node.soc
            node.target_speed_mps = initial_node.target_speed_mps
            node.target_torque = initial_node.target_torque
        return node

    def simulate_segment(self) -> list[DynamicNode]:
        """Simulate acceleration from 0 m/s to the segment speed limit."""
        speed_limit = getattr(self.segment, "speed_limit", None)
        if speed_limit is None:
            raise ValueError(f"Segment {self.segment.id} has no speed_limit")

        self.acceleration_nodes = self._simulate_acceleration_leg(0.0, speed_limit.mps, self.MAX_TORQUE)
        return self.acceleration_nodes

    def simulate_braking(self) -> list[DynamicNode]:
        """Simulate forward braking from the segment speed limit down to 0 m/s."""
        speed_limit = getattr(self.segment, "speed_limit", None)
        if speed_limit is None:
            raise ValueError(f"Segment {self.segment.id} has no speed_limit")

        self.braking_nodes = self._simulate_braking_leg(speed_limit.mps, 0.0, self.BRAKE_FORCE)
        return self.braking_nodes

    def _simulate_acceleration_leg(self, initial_speed_mps: float, target_speed_mps: float, torque: float, initial_node: DynamicNode | None = None) -> list[DynamicNode]:
        nodes: list[DynamicNode] = []
        current_node = self._seed_node(initial_speed_mps, torque=torque, initial_node=initial_node)
        nodes.append(current_node)

        if target_speed_mps <= initial_speed_mps:
            self.acceleration_speed_lookup = self._build_speed_lookup(nodes)
            return nodes

        while current_node.speed_mps < target_speed_mps:
            next_node = DynamicNode(segment=self.segment, torque=torque, profile=self.profile)
            self.adaptive_timestep(next_node, current_node)

            if next_node.speed_mps <= current_node.speed_mps:
                break

            if next_node.speed_mps > target_speed_mps and current_node.acc > 0:
                dt = (target_speed_mps - current_node.speed_mps) / current_node.acc
                if dt > 0:
                    next_node.solve_DynamicNode(current_node, dt)

            nodes.append(next_node)
            current_node = next_node

        self.acceleration_speed_lookup = self._build_speed_lookup(nodes)
        return nodes

    def _simulate_braking_leg(self, initial_speed_mps: float, exit_speed_mps: float, brake_force: float, initial_node: DynamicNode | None = None) -> list[DynamicNode]:
        nodes: list[DynamicNode] = []
        current_node = self._seed_node(initial_speed_mps, Fb=brake_force, initial_node=initial_node)
        nodes.append(current_node)

        if initial_speed_mps <= exit_speed_mps:
            self.braking_speed_lookup = self._build_speed_lookup(nodes)
            return nodes

        while current_node.speed_mps > exit_speed_mps:
            next_node = DynamicNode(segment=self.segment, Fb=brake_force, profile=self.profile)
            self.adaptive_timestep(next_node, current_node)

            if next_node.speed_mps >= current_node.speed_mps:
                break

            if next_node.speed_mps < exit_speed_mps:
                next_node.speed_mps = exit_speed_mps

            nodes.append(next_node)
            current_node = next_node

        self.braking_speed_lookup = self._build_speed_lookup(nodes)
        return nodes

    def required_distance_for_profile(self, initial_speed_mps: float, peak_speed_mps: float, exit_speed_mps: float) -> float:
        """Return the distance needed for a candidate accel/cruise/brake profile on this segment."""
        if initial_speed_mps > peak_speed_mps:
            lead_nodes = self._simulate_braking_leg(initial_speed_mps, peak_speed_mps, self.BRAKE_FORCE)
        else:
            lead_nodes = self._simulate_acceleration_leg(initial_speed_mps, peak_speed_mps, self.MAX_TORQUE)
        brake_nodes = self._simulate_braking_leg(peak_speed_mps, exit_speed_mps, self.BRAKE_FORCE)
        lead_distance = lead_nodes[-1].dist - lead_nodes[0].dist
        brake_distance = brake_nodes[-1].dist - brake_nodes[0].dist
        return lead_distance + brake_distance

    def solve_feasible_peak_speed(self, initial_speed_mps: float, target_speed_mps: float, exit_speed_mps: float) -> float:
        low = max(initial_speed_mps, exit_speed_mps)
        high = target_speed_mps

        if low >= high:
            return low

        best_speed = low
        for _ in range(30):
            midpoint = 0.5 * (low + high)
            required_distance = self.required_distance_for_profile(initial_speed_mps, midpoint, exit_speed_mps)

            if required_distance <= self.segment.dist:
                best_speed = midpoint
                low = midpoint
            else:
                high = midpoint

            if abs(high - low) <= self.VELOCITY_STEP_MPS:
                break

        return best_speed

    def _offset_nodes(self, nodes: list[DynamicNode], time_offset: float, dist_offset: float) -> list[DynamicNode]:
        shifted_nodes: list[DynamicNode] = []
        for node in nodes:
            new_node = copy.copy(node)
            new_node.time += time_offset
            new_node.dist += dist_offset
            shifted_nodes.append(new_node)
        return shifted_nodes

    def simulate_speed_profile(self, initial_speed_mps: float, target_speed_mps: float, exit_speed_mps: float, initial_node: DynamicNode | None = None) -> list[DynamicNode]:
        if initial_node is not None:
            initial_speed_mps = initial_node.speed_mps

        peak_speed_mps = max(target_speed_mps, exit_speed_mps)

        if initial_speed_mps > peak_speed_mps:
            lead_nodes = self._simulate_braking_leg(initial_speed_mps, peak_speed_mps, self.BRAKE_FORCE, initial_node=initial_node)
        else:
            lead_nodes = self._simulate_acceleration_leg(initial_speed_mps, peak_speed_mps, self.MAX_TORQUE, initial_node=initial_node)

        brake_nodes = self._simulate_braking_leg(peak_speed_mps, exit_speed_mps, self.BRAKE_FORCE)

        lead_distance = lead_nodes[-1].dist - lead_nodes[0].dist
        brake_distance = brake_nodes[-1].dist - brake_nodes[0].dist
        required_distance = lead_distance + brake_distance

        cruise_distance = max(0.0, self.segment.dist - required_distance)
        cruise_time = cruise_distance / peak_speed_mps if peak_speed_mps > 1e-12 else 0.0

        self.cruise_node = None

        combined_nodes = list(lead_nodes)
        if cruise_distance > 1e-12:
            cruise_node = DynamicNode(
                segment=self.segment,
                speed_mps=peak_speed_mps,
                torque=0.0,
                Fb=0.0,
                profile=self.profile,
            )
            cruise_node.time = lead_nodes[-1].time + cruise_time
            cruise_node.dist = lead_nodes[-1].dist + cruise_distance
            cruise_node.target_speed_mps = peak_speed_mps
            cruise_node.soc = lead_nodes[-1].soc
            self.cruise_node = cruise_node
            combined_nodes.append(cruise_node)
            brake_offset_node = cruise_node
        else:
            brake_offset_node = lead_nodes[-1]

        shifted_braking_nodes = self._offset_nodes(brake_nodes[1:], brake_offset_node.time, brake_offset_node.dist)
        combined_nodes.extend(shifted_braking_nodes)

        self.acceleration_nodes = lead_nodes if initial_speed_mps <= peak_speed_mps else []
        self.braking_nodes = brake_nodes
        self.profile_nodes = combined_nodes
        self.last_peak_speed_mps = peak_speed_mps

        self.acceleration_speed_lookup = self._build_speed_lookup(self.acceleration_nodes)
        self.braking_speed_lookup = self._build_speed_lookup(self.braking_nodes)

        return combined_nodes

    def _build_speed_lookup(self, nodes: list[DynamicNode]) -> list[DynamicNode]:
        if not nodes:
            return []

        ordered_nodes = sorted(nodes, key=lambda node: node.speed_mps)
        max_speed_mps = ordered_nodes[-1].speed_mps
        max_bucket = int(math.ceil(max_speed_mps / self.VELOCITY_STEP_MPS))
        lookup: list[DynamicNode] = []

        node_index = 0
        for bucket in range(max_bucket + 1):
            target_speed_mps = bucket * self.VELOCITY_STEP_MPS

            while node_index + 1 < len(ordered_nodes) and ordered_nodes[node_index + 1].speed_mps <= target_speed_mps:
                node_index += 1

            previous_node = ordered_nodes[node_index]
            next_node = ordered_nodes[min(node_index + 1, len(ordered_nodes) - 1)]

            if abs(previous_node.speed_mps - target_speed_mps) <= abs(next_node.speed_mps - target_speed_mps):
                lookup.append(previous_node)
            else:
                lookup.append(next_node)

        return lookup

    def _lookup_speed_node(self, speed_mps: float, lookup: list[DynamicNode], label: str) -> DynamicNode:
        if not lookup:
            raise ValueError(f"No {label} lookup available. Run the corresponding simulation first.")

        clamped_speed_mps = max(0.0, speed_mps)
        bucket = int(round(clamped_speed_mps / self.VELOCITY_STEP_MPS))
        bucket = min(bucket, len(lookup) - 1)
        return lookup[bucket]

    def get_acceleration_node_at_speed(self, speed_mps: float) -> DynamicNode:
        return self._lookup_speed_node(speed_mps, self.acceleration_speed_lookup, "acceleration")

    def get_braking_node_at_speed(self, speed_mps: float) -> DynamicNode:
        return self._lookup_speed_node(speed_mps, self.braking_speed_lookup, "braking")

    def adaptive_timestep(self, current_dynamic_node: DynamicNode, initial_dynamic_node: DynamicNode):
        dt = self.TIME_STEP
        current_dynamic_node.solve_DynamicNode(initial_dynamic_node, dt)

        if abs(current_dynamic_node.acc) > 1e-12 and abs(current_dynamic_node.acc * dt) > self.VELOCITY_STEP_MPS:
            dt = min(self.TIME_STEP, abs(self.VELOCITY_STEP_MPS / current_dynamic_node.acc))
            current_dynamic_node.solve_DynamicNode(initial_dynamic_node, dt)

        current_dynamic_node.time = initial_dynamic_node.time + dt
        return dt

    def plot_acceleration_nodes(self, x_field: str = "dist", y_fields: str | list[str] = "speed_kmph", name: str = "acceleration_nodes", ax=None, xlabel=None, ylabel=None, title=None):
        if not self.acceleration_nodes:
            raise ValueError("No acceleration nodes available. Run simulate_segment() first.")

        if xlabel is None:
            xlabel = "Distance (m)"
        if ylabel is None:
            ylabel = "Speed (km/h)"
        if title is None:
            title = "Distance vs Speed"

        return plot_RouteInterval(
            [self.acceleration_nodes],
            x_field,
            y_fields,
            name,
            labels=["Acceleration Nodes"],
            ax=ax,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )

    def plot_braking_nodes(self, x_field: str = "dist", y_fields: str | list[str] = "speed_kmph", name: str = "braking_nodes", ax=None, xlabel=None, ylabel=None, title=None):
        if not self.braking_nodes:
            raise ValueError("No braking nodes available. Run simulate_braking() first.")

        if xlabel is None:
            xlabel = "Distance (m)"
        if ylabel is None:
            ylabel = "Speed (km/h)"
        if title is None:
            title = "Distance vs Speed During Braking"

        return plot_RouteInterval(
            [self.braking_nodes],
            x_field,
            y_fields,
            name,
            labels=["Braking Nodes"],
            ax=ax,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )

    def plot_speed_profile_nodes(self, x_field: str = "dist", y_fields: str | list[str] = "speed_kmph", name: str = "speed_profile_nodes", ax=None, xlabel=None, ylabel=None, title=None):
        if not self.profile_nodes:
            raise ValueError("No combined profile nodes available. Run simulate_speed_profile() first.")

        if xlabel is None:
            xlabel = "Distance (m)"
        if ylabel is None:
            ylabel = "Speed (km/h)"
        if title is None:
            title = "Distance vs Speed"

        return plot_RouteInterval(
            [self.profile_nodes],
            x_field,
            y_fields,
            name,
            labels=["Combined Profile"],
            ax=ax,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )


if __name__ == "__main__":
    from src.config.schema import CarProfile

    from ..database.fetch_route_intervals import fetch_route_intervals
    import matplotlib.pyplot as plt

    route = fetch_route_intervals("A. Independence to Topeka", max_nodes=100)
    segment = route.segments[0]
    profile = CarProfile()
    simulator = SegmentSimulator(segment, profile)

    initial_speed_mps = 0.0
    target_speed_mps = min(segment.speed_limit.mps, 20.0)
    exit_speed_mps = 0.0

    combined_nodes = simulator.simulate_speed_profile(initial_speed_mps, target_speed_mps, exit_speed_mps)

    print(f"Simulated combined speed profile for segment {segment.id}")
    print(f"Initial speed={initial_speed_mps:.3f}m/s, target speed={target_speed_mps:.3f}m/s, exit speed={exit_speed_mps:.3f}m/s")
    print(f"Peak speed used: {simulator.last_peak_speed_mps:.3f}m/s")
    print(
        "Final profile node: "
        f"time={combined_nodes[-1].time:.3f}s, "
        f"speed={combined_nodes[-1].speed_mps:.3f}m/s, "
        f"dist={combined_nodes[-1].dist:.3f}m"
    )

    fig, axes = plt.subplots(3, 1, figsize=(9, 12), sharex=True)
    simulator.plot_acceleration_nodes(ax=axes[0], title="Acceleration")
    simulator.plot_speed_profile_nodes(ax=axes[1], title="Combined Speed Profile")
    simulator.plot_braking_nodes(ax=axes[2], title="Braking")
    fig.tight_layout()
    plt.show()
