import sqlite3
from dataclasses import dataclass
from ..models import Coordinate, Displacement
from .speed_limits import lookup_speed_limit

ROUTE_ROW_TABLE_NAME = "route_row"
ROUTE_ROW_COLUMN_DEFS: tuple[tuple[str, str], ...] = (
    ("placemark_name", "TEXT NOT NULL"),
    ("id", "INTEGER NOT NULL"),
    ("lat", "REAL NOT NULL"),
    ("lon", "REAL NOT NULL"),
    ("elevation", "REAL NOT NULL"),
    ("distance", "REAL NOT NULL"),
    ("speed_limit", "REAL"),
    ("stop_type", "INTEGER"),
    ("ghi", "REAL"),
    ("wind_dir", "REAL"),
    ("wind_speed", "REAL"),
    ("speed", "REAL"),
    ("torque", "REAL"),
)
ROUTE_ROW_PRIMARY_KEY: tuple[str, ...] = ("placemark_name", "id")

ROUTE_ROW_COLUMNS: tuple[str, ...] = (
    tuple(column_name for column_name, _ in ROUTE_ROW_COLUMN_DEFS)
)


@dataclass
class RouteRow:
    placemark_name: str
    id: int
    lat: float
    lon: float
    elevation: float
    distance: float
    speed_limit: float | None = None
    stop_type: bool | None = None
    ghi: float | None = None
    wind_dir: float | None = None
    wind_speed: float | None = None
    speed: float | None = None
    torque: float | None = None

    def to_db_params(self) -> dict:
        return {column_name: getattr(self, column_name) for column_name in ROUTE_ROW_COLUMNS}

    @classmethod
    def insert_sql(cls) -> str:
        columns = ",".join(ROUTE_ROW_COLUMNS)
        placeholders = ",".join(f":{column_name}" for column_name in ROUTE_ROW_COLUMNS)
        return f"INSERT INTO {ROUTE_ROW_TABLE_NAME} ({columns}) VALUES ({placeholders})"

    @classmethod
    def create_table_sql(cls) -> str:
        column_def_sql = ",\n        ".join(
            f"{column_name} {column_type}" for column_name, column_type in ROUTE_ROW_COLUMN_DEFS
        )
        primary_key_sql = ", ".join(ROUTE_ROW_PRIMARY_KEY)
        return (
            f"CREATE TABLE {ROUTE_ROW_TABLE_NAME} (\n"
            f"        {column_def_sql},\n"
            f"        PRIMARY KEY ({primary_key_sql})\n"
            f"    );"
        )

    @classmethod
    def get_table_columns(cls, cursor: sqlite3.Cursor) -> list[str]:
        cursor.execute(f"PRAGMA table_info({ROUTE_ROW_TABLE_NAME})")
        return [row[1] for row in cursor.fetchall()]

    @classmethod
    def validate_schema(cls, cursor: sqlite3.Cursor) -> None:
        actual_columns = cls.get_table_columns(cursor)
        expected_columns = list(ROUTE_ROW_COLUMNS)
        if actual_columns != expected_columns:
            raise ValueError(
                f"{ROUTE_ROW_TABLE_NAME} schema mismatch. "
                f"Expected columns {expected_columns}, got {actual_columns}."
            )

def build_rows(placemark_name: str, coords: list[Coordinate], speed_limits: list) -> list[RouteRow]:
    rows: list[RouteRow] = []
    limit_index = 0
    total_distance = 0
    for coord_index, coord in enumerate(coords[:-1]):
        total_distance += Displacement(coord, coords[coord_index + 1]).dist

        speed_limit, limit_index = lookup_speed_limit(speed_limits, total_distance, limit_index)
        rows.append(RouteRow(placemark_name=placemark_name, id=coord_index, lat=coord.lat, lon=coord.lon, elevation=coord.elevation, distance=total_distance, speed_limit=speed_limit))
    rows.append(RouteRow(placemark_name=placemark_name, id=rows[-1].id + 1, lat=coords[-1].lat, lon=coords[-1].lon, elevation=coords[-1].elevation, distance=total_distance, speed_limit=0))
    return rows