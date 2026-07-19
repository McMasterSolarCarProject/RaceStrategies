import sqlite3

from src.database.route_row import (
    ROUTE_ROW_COLUMNS,
    RouteRow,
    create_route_row_table_sql,
    validate_route_row_schema,
)


def test_route_row_schema_matches_contract():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(create_route_row_table_sql())

    # Raises if table columns drift from contract order/names.
    validate_route_row_schema(cur)

    conn.close()


def test_route_row_db_params_keys_match_contract():
    row = RouteRow(
        placemark_name="test",
        id=1,
        lat=0.0,
        lon=0.0,
        elevation=0.0,
        distance=0.0,
        speed_limit=0.0,
        stop_type=None,
        ghi=None,
        wind_dir=None,
        wind_speed=None,
        speed=-1,
        torque=-1,
    )

    assert list(row.to_db_params().keys()) == list(ROUTE_ROW_COLUMNS)
