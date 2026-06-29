from __future__ import annotations

import csv
import math
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OFF_ROUTE_THRESHOLD_M = 120.0


@dataclass(frozen=True)
class RoutePoint:
    lat: float
    lon: float
    elevation_m: float
    distance_m: float
    speed_limit_kmh: float | None = None
    target_speed_kmh: float | None = None
    torque_nm: float | None = None
    power_w: float | None = None
    stop_type: str | None = None
    ghi: float | None = None
    wind_dir: float | None = None
    wind_speed: float | None = None


@dataclass(frozen=True)
class RouteSegment:
    route_name: str
    index: int
    start: RoutePoint
    end: RoutePoint

    @property
    def length_m(self) -> float:
        return max(self.end.distance_m - self.start.distance_m, haversine_m(self.start.lat, self.start.lon, self.end.lat, self.end.lon))

    @property
    def grade_percent(self) -> float:
        if self.length_m <= 0:
            return 0.0
        return (self.end.elevation_m - self.start.elevation_m) / self.length_m * 100.0

    @property
    def speed_limit_kmh(self) -> float | None:
        return self.start.speed_limit_kmh

    @property
    def target_speed_kmh(self) -> float | None:
        return self.start.target_speed_kmh


@dataclass(frozen=True)
class Route:
    name: str
    points: list[RoutePoint]
    segments: list[RouteSegment]

    @property
    def total_distance_m(self) -> float:
        return self.points[-1].distance_m if self.points else 0.0


@dataclass(frozen=True)
class RouteMatch:
    route_name: str
    segment_index: int
    along_route_m: float
    cross_track_m: float
    distance_to_end_m: float
    off_route: bool
    segment: RouteSegment


class RouteNotFoundError(ValueError):
    pass


class RouteRepository:
    """Loads routes and maps positions onto route segments.

    The mapping here is geometric route-position lookup only. It is intentionally
    separate from future route-update or optimization logic.
    """

    def __init__(
        self,
        project_root: Path | None = None,
        db_paths: list[Path] | None = None,
        generated_dir: Path | None = None,
        limits_dir: Path | None = None,
    ) -> None:
        self.project_root = project_root or PROJECT_ROOT
        self.db_paths = db_paths or [
            self.project_root / "data.sqlite",
            self.project_root / "ASC_2024.sqlite",
        ]
        self.generated_dir = generated_dir or self.project_root / "data" / "generated"
        self.limits_dir = limits_dir or self.project_root / "data" / "limits"
        self._route_cache: dict[str, Route] = {}

    def list_routes(self) -> list[str]:
        names: set[str] = set()
        for db_path in self.db_paths:
            names.update(self._list_db_routes(db_path))
        if self.generated_dir.exists():
            for csv_path in self.generated_dir.glob("*.csv"):
                name = self._csv_route_name(csv_path)
                if name:
                    names.add(name)
        return sorted(names)

    def load_route(self, route_name: str) -> Route:
        if route_name in self._route_cache:
            return self._route_cache[route_name]

        points = self._load_points_from_db(route_name)
        if not points:
            points = self._load_points_from_csv(route_name)
        if len(points) < 2:
            raise RouteNotFoundError(f"Route '{route_name}' was not found or has fewer than two points")

        segments = [RouteSegment(route_name, i, points[i], points[i + 1]) for i in range(len(points) - 1)]
        route = Route(route_name, points, segments)
        self._route_cache[route_name] = route
        return route

    def default_route_name(self) -> str:
        routes = self.list_routes()
        if not routes:
            raise RouteNotFoundError("No routes are available from SQLite or data/generated")
        return routes[0]

    def map_position(
        self,
        route_name: str,
        lat: float,
        lon: float,
        off_route_threshold_m: float = DEFAULT_OFF_ROUTE_THRESHOLD_M,
    ) -> RouteMatch:
        """Project a GPS point onto the nearest route segment.

        This returns the current route position used by the API placeholder
        adapters; it does not optimize or update the route plan.
        """
        route = self.load_route(route_name)
        best: tuple[float, float, RouteSegment] | None = None

        for segment in route.segments:
            along_m, cross_track_m = project_onto_segment(lat, lon, segment)
            if best is None or cross_track_m < best[1]:
                best = (along_m, cross_track_m, segment)

        if best is None:
            raise RouteNotFoundError(f"Route '{route_name}' has no segments")

        along_m, cross_track_m, segment = best
        return RouteMatch(
            route_name=route.name,
            segment_index=segment.index,
            along_route_m=along_m,
            cross_track_m=cross_track_m,
            distance_to_end_m=max(route.total_distance_m - along_m, 0.0),
            off_route=cross_track_m > off_route_threshold_m,
            segment=segment,
        )

    def _list_db_routes(self, db_path: Path) -> set[str]:
        if not db_path.exists():
            return set()
        try:
            with sqlite3.connect(db_path) as conn:
                route_col = self._route_column(conn)
                if route_col is None:
                    return set()
                rows = conn.execute(f"SELECT DISTINCT {route_col} FROM route_data").fetchall()
                return {str(row[0]) for row in rows if row[0]}
        except sqlite3.Error:
            return set()

    def _load_points_from_db(self, route_name: str) -> list[RoutePoint]:
        for db_path in self.db_paths:
            if not db_path.exists():
                continue
            try:
                with sqlite3.connect(db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    route_col = self._route_column(conn)
                    if route_col is None:
                        continue
                    columns = {row[1] for row in conn.execute("PRAGMA table_info(route_data)").fetchall()}
                    rows = conn.execute(
                        f"SELECT * FROM route_data WHERE {route_col} = ? ORDER BY id",
                        (route_name,),
                    ).fetchall()
                    if rows:
                        return [self._point_from_db_row(row, columns) for row in rows]
            except sqlite3.Error:
                continue
        return []

    def _route_column(self, conn: sqlite3.Connection) -> str | None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(route_data)").fetchall()}
        if "placemark_name" in columns:
            return "placemark_name"
        if "segment_id" in columns:
            return "segment_id"
        return None

    def _point_from_db_row(self, row: sqlite3.Row, columns: set[str]) -> RoutePoint:
        return RoutePoint(
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            elevation_m=float(row["elevation"] or 0.0),
            distance_m=float(row["distance"] or 0.0),
            speed_limit_kmh=_optional_float(row["speed_limit"] if "speed_limit" in columns else None),
            target_speed_kmh=_optional_float(row["speed"] if "speed" in columns else None),
            torque_nm=_optional_float(row["torque"] if "torque" in columns else None),
            power_w=_optional_float(row["power"] if "power" in columns else None),
            stop_type=_optional_str(row["stop_type"] if "stop_type" in columns else None),
            ghi=_optional_float(row["ghi"] if "ghi" in columns else None),
            wind_dir=_optional_float(row["wind_dir"] if "wind_dir" in columns else None),
            wind_speed=_optional_float(row["wind_speed"] if "wind_speed" in columns else None),
        )

    def _load_points_from_csv(self, route_name: str) -> list[RoutePoint]:
        csv_path = self._csv_path_for_route(route_name)
        if csv_path is None:
            return []

        limits = self._load_speed_limits(route_name)
        points: list[RoutePoint] = []
        with csv_path.open(newline="") as file:
            next(file, None)
            reader = csv.DictReader(file)
            for row in reader:
                distance_m = float(row["Distance"])
                points.append(
                    RoutePoint(
                        lat=float(row["Lat"]),
                        lon=float(row["Lon"]),
                        elevation_m=float(row.get("Elevation") or 0.0),
                        distance_m=distance_m,
                        speed_limit_kmh=self._speed_limit_at(limits, distance_m),
                        ghi=_optional_float(row.get("Cloud Cover")),
                        wind_dir=_optional_float(row.get("Wind Direction")),
                        wind_speed=_optional_float(row.get("Wind Speed")),
                    )
                )
        return points

    def _csv_path_for_route(self, route_name: str) -> Path | None:
        direct = self.generated_dir / f"{route_name}.csv"
        if direct.exists():
            return direct
        if not self.generated_dir.exists():
            return None
        for csv_path in self.generated_dir.glob("*.csv"):
            if self._csv_route_name(csv_path) == route_name:
                return csv_path
        return None

    def _csv_route_name(self, csv_path: Path) -> str | None:
        try:
            with csv_path.open(newline="") as file:
                first_line = file.readline().strip()
            return first_line or csv_path.stem
        except OSError:
            return None

    def _load_speed_limits(self, route_name: str) -> list[tuple[float, float]]:
        limits_path = self.limits_dir / f"{route_name} Limits.csv"
        if not limits_path.exists():
            return []
        limits: list[tuple[float, float]] = []
        with limits_path.open(newline="") as file:
            for row in csv.reader(file):
                if len(row) >= 3:
                    limits.append((float(row[1]), float(row[2])))
        return sorted(limits)

    def _speed_limit_at(self, limits: list[tuple[float, float]], distance_m: float) -> float | None:
        if not limits:
            return None
        current = limits[0][1]
        for limit_distance_m, speed_limit_kmh in limits:
            if distance_m < limit_distance_m:
                break
            current = speed_limit_kmh
        return current


def project_onto_segment(lat: float, lon: float, segment: RouteSegment) -> tuple[float, float]:
    px, py = local_xy_m(lat, lon, segment.start.lat, segment.start.lon)
    ex, ey = local_xy_m(segment.end.lat, segment.end.lon, segment.start.lat, segment.start.lon)
    length_sq = ex * ex + ey * ey
    if length_sq <= 0:
        return segment.start.distance_m, haversine_m(lat, lon, segment.start.lat, segment.start.lon)

    t = max(0.0, min(1.0, (px * ex + py * ey) / length_sq))
    proj_x = t * ex
    proj_y = t * ey
    cross_track_m = math.hypot(px - proj_x, py - proj_y)
    along_m = segment.start.distance_m + segment.length_m * t
    return along_m, cross_track_m


def local_xy_m(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    lat_scale_m = 111_320.0
    lon_scale_m = lat_scale_m * math.cos(math.radians(origin_lat))
    return (lon - origin_lon) * lon_scale_m, (lat - origin_lat) * lat_scale_m


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


@lru_cache(maxsize=1)
def get_default_repository() -> RouteRepository:
    return RouteRepository()
