from __future__ import annotations
import pandas as pd
import folium
import matplotlib.colors as mcolors
import numpy as np
from ..database.fetch_route_intervals import fetch_route_intervals
from ..engine.nodes import TimeNode, Segment
import time


class RouteMap:
    def __init__(self):
        self.folium_map = folium.Map()
        colormap = mcolors.LinearSegmentedColormap.from_list("speed_gradient", ["#0000FF", "#FF0000", "#00FF00"])(np.linspace(0, 1, 200))
        self.speed_colors = [mcolors.to_hex(color) for color in colormap]

    def generate_from_placemark(self, placemark_name: str, color: str = "#FF0000", db_path: str = "ASC_2024.sqlite"):
        route = fetch_route_intervals(placemark_name, db_path=db_path)
        coordinates = route.get_coordinate_pairs()
        # for coordinate in coordinates:
        #     folium.Marker(coordinate).add_to(self.folium_map)
        folium.PolyLine(coordinates, weight=5, opacity=1, color=color).add_to(self.folium_map)
        self.set_bounding_box(coordinates)

    def generate_from_time_nodes(
        self,
        segments: list[Segment],
        time_node_list: list[TimeNode],
        show_markers: bool = False,
        hover_tooltips: bool = True,
    ):
        """
        Draws colored segments between consecutive time nodes.
        - show_markers: if True, adds small dots at nodes (still slower than lines-only).
        - hover_tooltips: if True, shows a tooltip with key values when hovering segments (and dots if enabled).
        """
        # Interpolate coordinates for each time node along the route
        coordinates = self.get_time_node_coords(segments, time_node_list)
        coordinate_points = [pt for (pt, _tn) in coordinates]
        nodes = [tn for (_pt, tn) in coordinates]

        # Colors are based on the *starting* node's speed for each segment
        # (there are N-1 segments between N nodes)
        coordinate_colors = [self.get_speed_color(tn) for tn in nodes[:-1]]

        # Helper: build tooltip HTML safely
        def _fmt_tooltip(tn: TimeNode) -> str:
            # Pull what we can; missing attrs are skipped
            parts = []
            try:
                dist = getattr(tn, "dist", None)
                if dist is not None:
                    parts.append(f"<b>Dist:</b> {dist/1000:.3f} km")
            except Exception:
                pass

            try:
                t = getattr(tn, "time", None)
                if t is not None:
                    parts.append(f"<b>Time:</b> {t:.1f} s")
            except Exception:
                pass

            try:
                kmph = getattr(getattr(tn, "speed", None), "kmph", None)
                if kmph is not None:
                    parts.append(f"<b>Speed:</b> {kmph:.2f} km/h")
            except Exception:
                pass

            try:
                accel = getattr(tn, "accel", None)
                if accel is not None:
                    parts.append(f"<b>Accel:</b> {accel:.3f} m/s²")
            except Exception:
                pass

            try:
                torque = getattr(tn, "torque", None)
                # if torque not in (None, 0):
                #     parts.append(f"<b>Torque:</b> {torque:.0f} Nm")
            except Exception:
                pass

            try:
                Fb = getattr(tn, "Fb", None)
                if Fb not in (None, 0):
                    parts.append(f"<b>Brake F:</b> {Fb:.0f} N")
            except Exception:
                pass

            try:
                soc = getattr(tn, "soc", None)
                # if soc is not None:
                #     parts.append(f"<b>SOC:</b> {soc:.1f}%")
            except Exception:
                pass

            return "<br>".join(parts) if parts else "Node"

        # Draw segments and optional node dots with tooltips
        for start, end, tn, color in zip(
            coordinate_points[:-1],
            coordinate_points[1:],
            nodes[:-1],
            coordinate_colors,
        ):
            tip = folium.Tooltip(_fmt_tooltip(tn), sticky=True) if hover_tooltips else None

            # Optional tiny dots at each node (cheaper than full Markers, but still extra geometry)
            if show_markers:
                folium.CircleMarker(
                    location=start,
                    radius=2,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    tooltip=tip,
                ).add_to(self.folium_map)

            folium.PolyLine(
                (start, end),
                weight=5,
                opacity=1,
                color=color,
                tooltip=tip,  # hover over the segment to see values
            ).add_to(self.folium_map)

        # Fit bounds to all points
        self.set_bounding_box(coordinates=[pt for pt, _ in coordinates])

    def get_speed_color(self, time_node: TimeNode):
        try:
            color = self.speed_colors[min(int(time_node.speed.kmph) + 100, len(self.speed_colors) - 1)]
        except IndexError:
            color = self.speed_colors[0]
        return color

    def get_time_node_coords(self, segments: list[Segment], time_node_list: list[TimeNode]):
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

    def set_bounding_box(self, coordinates: list[tuple]):
        """
        Sets the bounding box of the folium map to fit all given coordinates.
        """
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
        if cur is None or not hasattr(cur, part):
            return default
        cur = getattr(cur, part)
    return cur


def format_time_node_tooltip(time_node, segment=None):
    # Basics
    dist_m = _safe_get(time_node, "dist", None)
    t_s = _safe_get(time_node, "time", None)
    kmph = _safe_get(time_node, "speed.kmph", None)
    mps = _safe_get(time_node, "speed.mps", None)
    accel = _safe_get(time_node, "accel", None)  # if you store it
    # torque   = _safe_get(time_node, "torque", None)
    Fb = _safe_get(time_node, "Fb", None)  # braking force (N)
    # soc      = _safe_get(time_node, "soc", None)
    e_j = _safe_get(time_node, "energy_j", None)  # if you accumulate per node
    e_wh = _safe_get(time_node, "energy_wh", None)  # or in Wh
    e_kwh = (e_wh / 1000.0) if e_wh is not None else (e_j / 3.6e6 if e_j is not None else None)

    # Segment constraints / context
    v_eff_k = _safe_get(segment, "v_eff.kmph", None) if segment is not None else None

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
    if kmph is not None:
        lines.append(f"<b>Speed:</b> {kmph:.2f} km/h")
    elif mps is not None:
        lines.append(f"<b>Speed:</b> {mps:.2f} m/s")
    if accel is not None:
        lines.append(f"<b>Accel:</b> {accel:.3f} m/s²")
    # if torque is not None: lines.append(f"<b>Torque:</b> {torque:.0f} Nm")
    if Fb is not None and Fb != 0:
        lines.append(f"<b>Brake F:</b> {Fb:.0f} N")
    if v_eff_k is not None:
        lines.append(f"<b>Target v:</b> {v_eff_k:.1f} km/h")
    if grade_pct is not None:
        lines.append(f"<b>Grade:</b> {grade_pct:+.1f}%")
    if e_kwh is not None:
        lines.append(f"<b>Energy:</b> {e_kwh:.3f} kWh")
    # if soc    is not None: lines.append(f"<b>SOC:</b> {soc:.1f}%")

    return "<br>".join(lines) if lines else "Node"


if __name__ == "__main__":
    route_map = RouteMap()
    route_map.generate_from_placemark("A. Independence to Topeka")
    route_map.save_map("maps/route_map")

    start = time.time()
    a = fetch_route_intervals("A. Independence to Topeka")
    a.simulate_interval(TIME_STEP=0.5)
    end = time.time()
    print(f"simulation done! took {end - start} seconds")

    start = time.time()
    route_map2 = RouteMap()
    route_map2.generate_from_time_nodes(a.segments, a.time_nodes[::1])
    route_map2.save_map("maps/route_map2")
    end = time.time()
    print(end - start)  # 1.219120979309082

    start = time.time()
    route_map3 = RouteMap()
    route_map3.generate_from_time_nodes(a.segments, a.time_nodes[::1], show_markers=True)
    route_map3.save_map("maps/route_map3")
    end = time.time()
    print(end - start)  # 11.331728458404541

    # start = time.time()
    # route_map4 = RouteMap()
    # route_map4.generate_from_time_nodes(a.segments, a.time_nodes[::1000])
    # route_map4.save_map("maps/route_map4")
    # end = time.time()
    # print(end - start) #1113
    print("done")
