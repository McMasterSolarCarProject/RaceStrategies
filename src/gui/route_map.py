from __future__ import annotations
import folium
import matplotlib.colors as mcolors
import numpy as np
from ..database.fetch_route_intervals import fetch_route_intervals
from ..engine.nodes import DynamicNode, Segment
from ..engine.interval_simulator import RouteInterval, join_intervals
import time


class RouteMap:
    def __init__(self):
        self.folium_map = folium.Map()
        colormap = mcolors.LinearSegmentedColormap.from_list("speed_gradient", ["#0000FF", "#FF0000", "#00FF00"])(np.linspace(0, 1, 60))
        self.speed_colors = [mcolors.to_hex(color) for color in colormap] # List of colors in a gradient of blue to red to green
        self.all_coordinates: list[tuple[float, float]] = []

    def generate_no_simulation_map(self, placemark_name: str, db_path: str = "ASC_2024.sqlite", split_at_stops: bool = False):
        """
        Generate a layered map from a placemark without simulation.
        Each route interval (or all intervals if not split) is shown as a single or multiple layers.
        """
        route_intervals = fetch_route_intervals(placemark_name, db_path=db_path, split_at_stops=split_at_stops)
        if route_intervals and not isinstance(route_intervals, list):
            route_intervals = [route_intervals]
        self._generate_layered_map(route_intervals, is_simulated=False)

    def generate_simulation_map(self, placemark_name: str, time_step: float, velocity_step: float = 1.0, hover: bool = True, db_path: str = "ASC_2024.sqlite", split_at_stops: bool = False) -> RouteInterval:
        """
        Generate a layered simulation map from a placemark.
        Each route interval is simulated and displayed as a separate layer.
        """
        route_intervals = fetch_route_intervals(placemark_name, db_path=db_path, split_at_stops=split_at_stops)
        if route_intervals and not isinstance(route_intervals, list):
            route_intervals = [route_intervals]

        # Simulate all route intervals
        for interval in route_intervals:
            interval.TIME_STEP = time_step
            interval.VELOCITY_STEP_MPS = velocity_step
            interval.simulate_interval()
        self._generate_layered_map(route_intervals, is_simulated=True, hover_tooltips=hover)
        return join_intervals(route_intervals)

    def _generate_layered_map(self, route_intervals: list[RouteInterval], is_simulated: bool, hover_tooltips: bool = True):
        """
        Generic layered map generator for both simulated and non-simulated routes.
        Creates a feature group for each interval, adds polylines/markers, and sets bounding box.
        """
        self.all_coordinates = []

        for i, interval in enumerate(route_intervals):
            layer = folium.FeatureGroup(name=f"Route interval {i + 1}", show=(i == 0))
            polylines = self._get_polylines(interval, is_simulated, hover_tooltips)

            for polyline in polylines:
                polyline.add_to(layer)

            layer.add_to(self.folium_map)

        folium.LayerControl().add_to(self.folium_map)
        self.set_bounding_box()

    def _get_polylines(self, route_interval: RouteInterval, is_simulated: bool, hover_tooltips: bool = True) -> list[folium.PolyLine]:
        """
        Generate polylines for an interval.
        For simulated: interpolates through time nodes and colors by speed.
        For non-simulated: simple polyline from segment coordinates.
        """
        if is_simulated:
            return self._get_simulated_path(route_interval, hover_tooltips)
        else:
            # Non-simulated: simple polyline from segment start/end points
            coordinates = route_interval.get_coordinate_pairs()
            self.all_coordinates.extend(coordinates)
            polyline = folium.PolyLine(coordinates, weight=5, opacity=1, color="#FF0000")
            return [polyline]

    def _get_simulated_path(self, route_interval: RouteInterval, hover_tooltips: bool = True) -> list[folium.PolyLine]:
        """
        Draws colored segments between consecutive time nodes.
        Returns list of polylines.
        """
        DECIMATION_INTERVAL = 8
        DECIMATED_NODES = route_interval.time_nodes[::DECIMATION_INTERVAL]

        coordinates = self.get_time_node_coords(route_interval.segments, DECIMATED_NODES)
        coordinate_points = [pt for (pt, _tn) in coordinates]
        self.all_coordinates.extend(coordinate_points)
        nodes = [tn for (_pt, tn) in coordinates]

        speeds = [max(0.0, tn.speed_mps * 3.6) for tn in nodes]
        min_speed = min(speeds, default=0.0)
        max_speed = max(speeds, default=1.0)
        coordinate_colors = [self.get_speed_color(tn, min_speed, max_speed) for tn in nodes[:-1]]

        polylines = []

        for start, end, tn, color in zip(
            coordinate_points[:-1],
            coordinate_points[1:],
            nodes[:-1],
            coordinate_colors,
        ):
            tip = folium.Tooltip(self._format_tooltip(tn), sticky=True) if hover_tooltips else None

            polyline = folium.PolyLine(
                (start, end),
                weight=5,
                opacity=1,
                color=color,
                tooltip=tip,
            )
            polylines.append(polyline)

        return polylines

    def _format_tooltip(self, tn: DynamicNode) -> str:
        """Build tooltip HTML for a time node."""
        parts = []

        dist = _safe_get(tn, "dist", None)
        if dist is not None:
            parts.append(f"<b>Dist:</b> {dist/1000:.3f} km")
        t = _safe_get(tn, "time", None)
        if t is not None:
            parts.append(f"<b>Time:</b> {t:.1f} s")
        speed_mps = _safe_get(tn, "speed_mps", None)
        if speed_mps is not None:
            parts.append(f"<b>Speed:</b> {speed_mps * 3.6:.2f} km/h")
        acc = _safe_get(tn, "acc", None)
        if acc is not None:
            parts.append(f"<b>Accel:</b> {acc:.3f} m/s²")
        Fb = _safe_get(tn, "Fb", None)
        if Fb not in (None, 0):
            parts.append(f"<b>Brake F:</b> {Fb:.0f} N")

        return "<br>".join(parts) if parts else "Node"

    def get_speed_color(self, time_node: DynamicNode, min_speed: float = 0.0, max_speed: float = 120.0):
        span = max(max_speed - min_speed, 1.0)
        ratio = max(0.0, min((time_node.speed_mps * 3.6 - min_speed) / span, 1.0))
        return self.speed_colors[round(ratio * (len(self.speed_colors) - 1))]

    def get_time_node_coords(self, segments: list[Segment], time_node_list: list[DynamicNode]) -> list[tuple[tuple[float, float], DynamicNode]]:
        seg_ends = np.array([seg.tdist for seg in segments])
        seg_dists = np.array([seg.dist for seg in segments])
        seg_start_dists = seg_ends - seg_dists
        p1_lat = np.array([seg.p1.lat for seg in segments])
        p2_lat = np.array([seg.p2.lat for seg in segments])
        p1_lon = np.array([seg.p1.lon for seg in segments])
        p2_lon = np.array([seg.p2.lon for seg in segments])

        tn_dist = np.array([tn.dist for tn in time_node_list])
        idxs = np.searchsorted(seg_ends, tn_dist, side="right")
        idxs = np.clip(idxs, 0, len(segments) - 1)

        frac = (tn_dist - seg_start_dists[idxs]) / seg_dists[idxs]
        lat = p1_lat[idxs] + frac * (p2_lat[idxs] - p1_lat[idxs])
        lon = p1_lon[idxs] + frac * (p2_lon[idxs] - p1_lon[idxs])

        return list(zip(zip(lat, lon), time_node_list))

    def set_bounding_box(self, coordinates: list[tuple] = []):
        """
        Sets the bounding box of the folium map to fit all given coordinates.
        """
        if len(coordinates) == 0:
            coordinates = self.all_coordinates
        arr = np.array(coordinates)
        sw = arr.min(axis=0).tolist()
        ne = arr.max(axis=0).tolist()
        self.folium_map.fit_bounds([sw, ne])

    def save_map(self, filepath: str):
        self.folium_map.save(f"{filepath}.html")


def _safe_get(obj, path, default=None):
    """Dot-path getattr with a default."""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return default
        cur = getattr(cur, part, None)
        if cur is None:
            return default
    return cur


def format_time_node_tooltip(time_node, segment=None):
    # Basics
    dist_m = _safe_get(time_node, "dist", None)
    t_s = _safe_get(time_node, "time", None)
    mps = _safe_get(time_node, "speed_mps", None)
    acc = _safe_get(time_node, "acc", None)
    # torque   = _safe_get(time_node, "torque", None)
    Fb = _safe_get(time_node, "Fb", None)  # braking force (N)
    # soc      = _safe_get(time_node, "soc", None)
    e_j = _safe_get(time_node, "energy_j", None)  # if you accumulate per node
    e_wh = _safe_get(time_node, "energy_wh", None)  # or in Wh
    e_kwh = (e_wh / 1000.0) if e_wh is not None else (e_j / 3.6e6 if e_j is not None else None)

    # Segment constraints / context
    # Grade (%) if coordinates have altitude
    grade_pct = None
    if segment is not None:
        try:
            z1 = _safe_get(segment, "p1.alt", None) or _safe_get(segment, "p1.elev", None) or _safe_get(segment, "p1.h", None)
            z2 = _safe_get(segment, "p2.alt", None) or _safe_get(segment, "p2.elev", None) or _safe_get(segment, "p2.h", None)
            seg_len = _safe_get(segment, "dist", None)
            if z1 is not None and z2 is not None and seg_len and seg_len > 0:
                grade_pct = 100.0 * (z2 - z1) / seg_len
        except Exception:
            pass

    lines = []
    if dist_m is not None:
        lines.append(f"<b>Dist:</b> {dist_m/1000:.3f} km")
    if t_s is not None:
        lines.append(f"<b>Time:</b> {t_s:.1f} s")
    if mps is not None:
        lines.append(f"<b>Speed:</b> {mps * 3.6:.2f} km/h")
    if acc is not None:
        lines.append(f"<b>Accel:</b> {acc:.3f} m/s²")
    # if torque is not None: lines.append(f"<b>Torque:</b> {torque:.0f} Nm")
    if Fb is not None and Fb != 0:
        lines.append(f"<b>Brake F:</b> {Fb:.0f} N")
    if grade_pct is not None:
        lines.append(f"<b>Grade:</b> {grade_pct:+.1f}%")
    if e_kwh is not None:
        lines.append(f"<b>Energy:</b> {e_kwh:.3f} kWh")
    # if soc    is not None: lines.append(f"<b>SOC:</b> {soc:.1f}%")

    return "<br>".join(lines) if lines else "Node"


if __name__ == "__main__":
    route_map = RouteMap()
    route_map.generate_no_simulation_map("A. Independence to Topeka")
    route_map.save_map("maps/route_map")

    start = time.time()
    route_interval = fetch_route_intervals("A. Independence to Topeka")
    if route_interval is RouteInterval:
        route_interval.TIME_STEP = 0.5
        route_interval.simulate_interval()
    end = time.time()
    print(f"simulation done! took {end - start} seconds")

    start = time.time()
    route_map2 = RouteMap()
    route_map2.generate_simulation_map("A. Independence to Topeka", time_step=0.5, hover=True)
    route_map2.save_map("maps/route_map_simulated")
    end = time.time()
    print(f"Map generation took {end - start} seconds")
    print("done")
