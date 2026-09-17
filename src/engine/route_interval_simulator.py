from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from src.config import CarProfile, DEFAULT_PROFILE

from .nodes import DynamicNode, Segment
from .segment_simulator import SegmentSimulator
from ..utils.graph import plot_RouteInterval, _resolve_value


class RouteIntervalSimulator:
    """Simulate a full route by chaining segment simulations together."""

    def __init__(
        self,
        route_or_segments,
        profile: CarProfile | None = None,
        target_profile: np.ndarray | None = None,
        time_step: float = 1.0,
        velocity_step_mps: float = 0.1,
        max_torque: float = 10000.0,
        brake_force: float = 10000.0,
    ):
        if hasattr(route_or_segments, "segments"):
            self.segments = list(route_or_segments.segments)
            route_profile = getattr(route_or_segments, "profile", None)
            route_targets = getattr(route_or_segments, "target_profile", None)
        else:
            self.segments = list(route_or_segments)
            route_profile = None
            route_targets = None

        self.profile = profile or route_profile or DEFAULT_PROFILE
        if target_profile is not None:
            self.target_profile = np.asarray(target_profile, dtype=float)
        elif route_targets is not None:
            self.target_profile = np.asarray(route_targets, dtype=float)
        else:
            self.target_profile = np.array(
                [
                    [segment.id, segment.speed_limit.mps if getattr(segment, "speed_limit", None) is not None else 0.0, 0.0]
                    for segment in self.segments
                ],
                dtype=float,
            )

        self.TIME_STEP = time_step
        self.VELOCITY_STEP_MPS = velocity_step_mps
        self.MAX_TORQUE = max_torque
        self.BRAKE_FORCE = brake_force

        self.route_nodes: list[DynamicNode] = []
        self.segment_nodes: list[list[DynamicNode]] = []
        self.segment_simulators: list[SegmentSimulator] = []
        self.start_node: DynamicNode | None = None
        self.end_node: DynamicNode | None = None

    def _build_seed_node(self, segment: Segment, previous_node: DynamicNode | None) -> DynamicNode:
        initial_speed = previous_node.speed_mps if previous_node is not None else 0.0
        seed_node = DynamicNode(segment=segment, speed_mps=initial_speed, profile=self.profile)
        if previous_node is not None:
            seed_node.time = previous_node.time
            seed_node.dist = previous_node.dist
            seed_node.soc = previous_node.soc
        else:
            seed_node.time = 0.0
            seed_node.dist = 0.0
            seed_node.soc = 100.0
        return seed_node

    def _segment_target_speed(self, segment_index: int) -> float:
        if segment_index < len(self.target_profile):
            target_speed = float(self.target_profile[segment_index, 1])
        else:
            target_speed = float(self.segments[segment_index].speed_limit.mps)

        segment_speed_limit = getattr(self.segments[segment_index], "speed_limit", None)
        if segment_speed_limit is not None and segment_speed_limit.mps > 0:
            target_speed = min(target_speed, segment_speed_limit.mps)

        return target_speed

    def _segment_exit_speed(self, segment_index: int, default_exit_speed_mps: float) -> float:
        if segment_index + 1 < len(self.segments):
            next_target_speed = self._segment_target_speed(segment_index + 1)
            return max(0.0, next_target_speed)
        return max(0.0, default_exit_speed_mps)

    def _segment_peak_speed(self, segment_simulator: SegmentSimulator, initial_speed_mps: float, target_speed_mps: float, exit_speed_mps: float) -> float:
        if initial_speed_mps > target_speed_mps:
            return target_speed_mps
        return segment_simulator.solve_feasible_peak_speed(initial_speed_mps, target_speed_mps, exit_speed_mps)

    def simulate_route(self, initial_speed_mps: float = 0.0, exit_speed_mps: float = 0.0) -> list[DynamicNode]:
        if not self.segments:
            self.route_nodes = []
            self.start_node = None
            self.end_node = None
            return self.route_nodes

        self.route_nodes = []
        self.segment_nodes = []
        self.segment_simulators = []

        current_node = DynamicNode(segment=self.segments[0], speed_mps=initial_speed_mps, profile=self.profile)
        current_node.time = 0.0
        current_node.dist = 0.0
        current_node.soc = 100.0
        self.start_node = current_node
        self.route_nodes.append(current_node)

        for segment_index, segment in enumerate(self.segments):
            segment_simulator = SegmentSimulator(segment, self.profile)
            segment_simulator.TIME_STEP = self.TIME_STEP
            segment_simulator.VELOCITY_STEP_MPS = self.VELOCITY_STEP_MPS
            segment_simulator.MAX_TORQUE = self.MAX_TORQUE
            segment_simulator.BRAKE_FORCE = self.BRAKE_FORCE

            target_speed_mps = self._segment_target_speed(segment_index)
            exit_speed = self._segment_exit_speed(segment_index, exit_speed_mps)
            peak_speed_mps = self._segment_peak_speed(segment_simulator, current_node.speed_mps, target_speed_mps, exit_speed)

            seed_node = self._build_seed_node(segment, current_node)
            segment_nodes = segment_simulator.simulate_speed_profile(
                initial_speed_mps=seed_node.speed_mps,
                target_speed_mps=peak_speed_mps,
                exit_speed_mps=exit_speed,
                initial_node=seed_node,
            )

            self.segment_simulators.append(segment_simulator)
            self.segment_nodes.append(segment_nodes)

            if segment_index == 0:
                self.route_nodes.extend(segment_nodes[1:])
            else:
                self.route_nodes.extend(segment_nodes[1:])

            current_node = segment_nodes[-1]

        self.end_node = current_node
        return self.route_nodes

    def simulate_segments(self, initial_speed_mps: float = 0.0, exit_speed_mps: float = 0.0) -> list[DynamicNode]:
        """Alias for the route-level interval solve."""
        return self.simulate_route(initial_speed_mps=initial_speed_mps, exit_speed_mps=exit_speed_mps)

    def simulate_interval(self, initial_speed_mps: float = 0.0, exit_speed_mps: float = 0.0) -> list[DynamicNode]:
        """Interval-style alias for simulate_route()."""
        return self.simulate_route(initial_speed_mps=initial_speed_mps, exit_speed_mps=exit_speed_mps)

    def plot_route_nodes(
        self,
        x_field: str = "dist",
        y_fields: str | list[str] = "speed_kmph",
        name: str = "route_nodes",
        ax=None,
        xlabel=None,
        ylabel=None,
        title=None,
        show_segment_boundaries: bool = True,
        annotate_segment_boundaries: bool = True,
        highlight_node_indices: list[int] | None = None,
    ):
        if not self.route_nodes:
            raise ValueError("No route nodes available. Run simulate_route() first.")

        if xlabel is None:
            xlabel = "Distance (m)"
        if ylabel is None:
            ylabel = "Speed (km/h)"
        if title is None:
            title = "Route Distance vs Speed"

        fig, ax = plot_RouteInterval(
            [self.route_nodes],
            x_field,
            y_fields,
            name,
            labels=["Route Nodes"],
            ax=ax,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )

        if show_segment_boundaries:
            boundary_positions = []
            for segment_index, segment_nodes in enumerate(self.segment_nodes[1:], start=1):
                if segment_nodes:
                    boundary_positions.append((segment_nodes[0].dist, self.segments[segment_index].id))

            if boundary_positions:
                y_limits = ax.get_ylim()
                label_y = y_limits[1] - 0.05 * (y_limits[1] - y_limits[0])
                for boundary_x, segment_id in boundary_positions:
                    ax.axvline(boundary_x, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
                    if annotate_segment_boundaries:
                        ax.text(
                            boundary_x,
                            label_y,
                            f"S{segment_id}",
                            rotation=90,
                            va="top",
                            ha="right",
                            fontsize=8,
                            color="gray",
                        )

        if highlight_node_indices:
            if isinstance(y_fields, str):
                y_field = y_fields
            else:
                y_field = y_fields[0]
            x_values = np.array([_resolve_value(node, x_field) for node in self.route_nodes], dtype=float)
            y_values = np.array([_resolve_value(node, y_field) for node in self.route_nodes], dtype=float)

            for node_index in highlight_node_indices:
                if node_index < 0 or node_index >= len(self.route_nodes):
                    continue
                node = self.route_nodes[node_index]
                ax.scatter([x_values[node_index]], [y_values[node_index]], color="orange", s=60, zorder=5)
                ax.annotate(
                    f"N{node_index} / S{node.segment.id}",
                    (x_values[node_index], y_values[node_index]),
                    textcoords="offset points",
                    xytext=(6, 6),
                    fontsize=8,
                    color="darkorange",
                )

        return fig, ax

    def plot_segments(self, x_field: str = "dist", y_fields: str | list[str] = "speed_kmph", name: str = "segments", ax=None, xlabel=None, ylabel=None, title=None):
        """Alias for plot_route_nodes()."""
        return self.plot_route_nodes(
            x_field=x_field,
            y_fields=y_fields,
            name=name,
            ax=ax,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )

    def plot_interval_nodes(
        self,
        x_field: str = "dist",
        y_fields: str | list[str] = "speed_kmph",
        name: str = "interval_nodes",
        ax=None,
        xlabel=None,
        ylabel=None,
        title=None,
    ):
        """Interval-style alias for plot_route_nodes()."""
        return self.plot_route_nodes(
            x_field=x_field,
            y_fields=y_fields,
            name=name,
            ax=ax,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title,
        )


if __name__ == "__main__":
    from ..database.fetch_route_intervals import fetch_route_intervals

    route_interval = fetch_route_intervals("A. Independence to Topeka", max_nodes=100)
    simulator = RouteIntervalSimulator(route_interval)
    route_nodes = simulator.simulate_route()

    print(f"Simulated {len(route_nodes)} route nodes across {len(simulator.segments)} segments")
    if simulator.start_node is not None:
        print(
            f"Start: time={simulator.start_node.time:.3f}s, "
            f"speed={simulator.start_node.speed_mps:.3f}m/s, dist={simulator.start_node.dist:.3f}m"
        )
    if simulator.end_node is not None:
        print(
            f"End: time={simulator.end_node.time:.3f}s, "
            f"speed={simulator.end_node.speed_mps:.3f}m/s, dist={simulator.end_node.dist:.3f}m"
        )

    fig, ax = plt.subplots(figsize=(10, 6))
    simulator.plot_route_nodes(ax=ax)
    fig.tight_layout()
    plt.show()
