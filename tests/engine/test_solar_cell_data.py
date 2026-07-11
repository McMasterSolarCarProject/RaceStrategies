import datetime

from src.config import DEFAULT_PROFILE
from src.engine.kinematics import Coordinate, Speed
from src.engine.nodes import Segment
from src.engine.solar_cell_data import CarSolarCells, SolarCell


def make_segment(ghi=1000.0):
    return Segment(
        Coordinate(39.0, -94.0, 100.0),
        Coordinate(39.01, -94.0, 100.0),
        speed_limit=Speed(kmph=80.0),
        ghi=ghi,
    )


def test_solar_cell_converts_naive_time_to_utc_and_calculates_nonnegative_power():
    cell = SolarCell(make_segment(), tilt=0.0, time=datetime.datetime(2026, 6, 1, 18, 0, 0))

    assert cell.time.tzinfo is datetime.timezone.utc
    assert cell.cell_power_out >= 0
    assert cell.location.latitude == 39.0


def test_car_solar_cells_iterates_and_sums_cell_power():
    cells = CarSolarCells(
        make_segment(),
        tilt_list=[0.0, 20.0],
        time=datetime.datetime(2026, 6, 1, 18, 0, 0, tzinfo=datetime.timezone.utc),
    )

    assert list(cells) == cells.solar_cells
    assert cells.total_power_output() == sum(cell.cell_power_out for cell in cells.solar_cells)


def test_car_solar_cells_update_changes_segment_and_time():
    cells = CarSolarCells(
        make_segment(ghi=1000.0),
        tilt_list=[0.0],
        time=datetime.datetime(2026, 6, 1, 18, 0, 0, tzinfo=datetime.timezone.utc),
        profile=DEFAULT_PROFILE.override("solar.cell_area", 0.02),
    )
    new_segment = make_segment(ghi=500.0)
    new_time = datetime.datetime(2026, 6, 1, 19, 0, 0, tzinfo=datetime.timezone.utc)

    cells.update_cells(new_segment=new_segment, new_time=new_time)

    assert cells.solar_cells[0].segment is new_segment
    assert cells.solar_cells[0].time is new_time
