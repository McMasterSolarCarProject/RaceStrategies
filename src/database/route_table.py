import sqlite3
from dataclasses import dataclass

ROUTE_TABLE_NAME = "route_table"
ROUTE_COLUMN_DEFS: tuple[tuple[str, str], ...] = (
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

ROUTE_ROW_COLUMNS: tuple[str, ...] = (tuple(column_name for column_name, _ in ROUTE_COLUMN_DEFS))


class RouteTable:
    @staticmethod
    def insert_sql() -> str:
        columns = ",".join(ROUTE_ROW_COLUMNS)
        placeholders = ",".join(f":{column_name}" for column_name in ROUTE_ROW_COLUMNS)
        return f"INSERT INTO {ROUTE_TABLE_NAME} ({columns}) VALUES ({placeholders})"

    @staticmethod
    def update_rows_sql() -> str:
        update_columns = [column_name for column_name in ROUTE_ROW_COLUMNS if column_name not in ROUTE_ROW_PRIMARY_KEY]
        assignments = ", ".join(f"{column_name} = :{column_name}" for column_name in update_columns)
        conditions = " AND ".join(f"{column_name} = :{column_name}" for column_name in ROUTE_ROW_PRIMARY_KEY)
        return f"UPDATE {ROUTE_TABLE_NAME} SET {assignments} WHERE {conditions}"

    @staticmethod
    def update_rows(rows: list["RouteRow"], cursor: sqlite3.Cursor) -> None:
        cursor.executemany(RouteTable.update_rows_sql(),[row.to_db_params() for row in rows])

    @staticmethod
    def create_table_sql() -> str:
        column_def_sql = ",\n        ".join(
            f"{column_name} {column_type}" for column_name, column_type in ROUTE_COLUMN_DEFS
        )
        primary_key_sql = ", ".join(ROUTE_ROW_PRIMARY_KEY)
        return (
            f"CREATE TABLE {ROUTE_TABLE_NAME} (\n"
            f"        {column_def_sql},\n"
            f"        PRIMARY KEY ({primary_key_sql})\n"
            f"    );"
        )

    @staticmethod
    def create_table(cursor: sqlite3.Cursor) -> None:
        cursor.execute(RouteTable.create_table_sql())
    
    @staticmethod
    def get_table_columns(cursor: sqlite3.Cursor) -> list[str]:
        cursor.execute(f"PRAGMA table_info({ROUTE_TABLE_NAME})")
        return [row[1] for row in cursor.fetchall()]

    @staticmethod
    def validate_schema(cursor: sqlite3.Cursor) -> None:
        actual_columns = RouteTable.get_table_columns(cursor)
        expected_columns = list(ROUTE_ROW_COLUMNS)
        if actual_columns != expected_columns:
            raise ValueError(
                f"{ROUTE_TABLE_NAME} schema mismatch. "
                f"Expected columns {expected_columns}, got {actual_columns}."
            )

    @staticmethod
    def fetch_route_rows(placemark_name: str, cursor: sqlite3.Cursor) -> list["RouteRow"]:
        cursor.execute(f"SELECT * FROM {ROUTE_TABLE_NAME} WHERE placemark_name = ? ORDER BY id", (placemark_name,))
        rows = cursor.fetchall()
        return [RouteRow(*row) for row in rows]
    
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