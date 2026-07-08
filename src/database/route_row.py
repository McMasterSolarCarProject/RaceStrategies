from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import sqlite3
import numpy as np
from ..engine.kinematics import Coordinate, Speed, Velocity
from ..engine.nodes import Segment


ROUTE_ROW_TABLE_NAME = "route_row"
ROUTE_ROW_COLUMN_DEFS: tuple[tuple[str, str], ...] = (
    ("placemark_name", "TEXT NOT NULL"),
    ("id", "INTEGER NOT NULL"),
    ("lat", "FLOAT NOT NULL"),
    ("lon", "FLOAT NOT NULL"),
    ("elevation", "FLOAT NOT NULL"),
    ("distance", "FLOAT NOT NULL"),
    ("speed_limit", "FLOAT NOT NULL"),
    ("stop_type", "STRING"),
    ("ghi", "INT"),
    ("wind_dir", "FLOAT"),
    ("wind_speed", "FLOAT"),
    ("speed", "FLOAT"),
    ("torque", "FLOAT"),
)
ROUTE_ROW_PRIMARY_KEY: tuple[str, ...] = ("placemark_name", "id")

ROUTE_ROW_COLUMNS: tuple[str, ...] = (
    tuple(column_name for column_name, _ in ROUTE_ROW_COLUMN_DEFS)
)


def create_route_row_table_sql() -> str:
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


def insert_route_row_sql() -> str:
    columns = ",".join(ROUTE_ROW_COLUMNS)
    placeholders = ",".join(f":{column_name}" for column_name in ROUTE_ROW_COLUMNS)
    return f"INSERT INTO {ROUTE_ROW_TABLE_NAME} ({columns}) VALUES ({placeholders})"


def get_route_row_table_columns(cursor: sqlite3.Cursor) -> list[str]:
    cursor.execute(f"PRAGMA table_info({ROUTE_ROW_TABLE_NAME})")
    return [row[1] for row in cursor.fetchall()]


def validate_route_row_schema(cursor: sqlite3.Cursor) -> None:
    actual_columns = get_route_row_table_columns(cursor)
    expected_columns = list(ROUTE_ROW_COLUMNS)
    if actual_columns != expected_columns:
        raise ValueError(
            f"{ROUTE_ROW_TABLE_NAME} schema mismatch. "
            f"Expected columns {expected_columns}, got {actual_columns}."
        )


@dataclass
class RouteRow:
    placemark_name: str
    id: int
    lat: float
    lon: float
    elevation: float
    distance: float
    speed_limit: float
    stop_type: Any
    ghi: Any
    wind_dir: Any
    wind_speed: Any
    speed: float
    torque: float

    def to_db_params(self) -> dict:
        return {column_name: getattr(self, column_name) for column_name in ROUTE_ROW_COLUMNS}

    @classmethod
    def from_sql_row(cls, row) -> "RouteRow":
        return cls(**{column_name: row[column_name] for column_name in ROUTE_ROW_COLUMNS})

    def to_segment(self, next_row: "RouteRow") -> Segment:
        current_coord = Coordinate(self.lat, self.lon, self.elevation)
        next_coord = Coordinate(next_row.lat, next_row.lon, next_row.elevation)
        wind = Velocity()
        return Segment(
            current_coord,
            next_coord,
            self.id,
            Speed(kmph=self.speed_limit),
            self.ghi,
            wind,
        )

    def to_target_profile_row(self) -> np.ndarray:
        return np.array([self.id, Speed(kmph=self.speed).mps, self.torque], dtype=float)
