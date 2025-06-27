# import sys
# import os

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pytest

from src.engine.solar_cell_data import SolarCell, CarSolarCells
from src.engine.nodes import Segment
from src.engine.kinematics import Coordinate
from src.utils.constants import CELL_DATA
from astral import LocationInfo
from astral.sun import noon
import math
import datetime


@pytest.fixture
def create_segment():
    def _create(
        lat=34.0522,
        lat2=44.0522,
        lon=-118.2437,
        lon2=-119.2437,
        elevation=45,
        elevation2=50,
        azimuth=180,
        ghi=800,
    ):
        p1 = Coordinate(lat, lon, elevation)
        p2 = Coordinate(lat2, lon2, elevation2)
        s = Segment(p1, p2, ghi=ghi)
        s.azimuth = azimuth
        return s

    return _create


@pytest.fixture
def create_solar_cell(create_segment):
    def _create(
        lon=-118.2437,
        lon2=-119.2437,
        lat=34.0522,
        lat2=44.0522,
        elevation=45,
        elevation2=50,
        azimuth=180,
        ghi=800,
        tilt=30,
        cell_eff=0.24,
        time=datetime.datetime(2023, 10, 1, 12, 0, 0),
        tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
    ):
        segment = create_segment(lat, lat2, lon, lon2, elevation, elevation2, azimuth, ghi)
        time = time.replace(tzinfo=tzinfo) if time else None
        return SolarCell(segment, tilt, time, cell_eff=cell_eff)

    return _create


@pytest.fixture
def create_car_solar_cells(create_segment):
    def _create(
        lon=-118.2437,
        lon2=-119.2437,
        lat=34.0522,
        lat2=44.0522,
        elevation=45,
        elevation2=50,
        azimuth=180,
        ghi=800,
        tilt=30,
        time=datetime.datetime(2023, 10, 1, 12, 0, 0),
        tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
    ):
        segment = create_segment(lat, lat2, lon, lon2, elevation, elevation2, azimuth, ghi)
        time = time.replace(tzinfo=tzinfo) if time else None
        print(type(segment))
        return CarSolarCells(segment, time)

    return _create


def test_create_solar_cell(create_solar_cell):
    cell = create_solar_cell()
    print(f"Created SolarCell: {cell}")
    assert isinstance(cell, SolarCell)


def test_create_car_solar_cells(create_car_solar_cells, create_solar_cell):
    car_cells = create_car_solar_cells()
    print(f"Created CarSolarCells: {car_cells}")
    assert isinstance(car_cells, CarSolarCells)

    cell_hood_a = create_solar_cell(tilt=CELL_DATA["section_hood"]["tilt"], cell_eff=CELL_DATA["me3_eff"])
    cell_hood_b = create_solar_cell(tilt=CELL_DATA["section_hood"]["tilt"], cell_eff=CELL_DATA["ne3_eff"])
    cell_top = create_solar_cell(tilt=CELL_DATA["section_top"]["tilt"], cell_eff=CELL_DATA["me3_eff"])
    cell_rear = create_solar_cell(tilt=CELL_DATA["section_rear"]["tilt"], cell_eff=CELL_DATA["me3_eff"])
    calculated_total_power = (
        cell_hood_a.cell_power_out * CELL_DATA["section_hood"]["num_me3"]
        + cell_hood_b.cell_power_out * CELL_DATA["section_hood"]["num_ne3"]
        + cell_top.cell_power_out * CELL_DATA["section_top"]["num_me3"]
        + cell_rear.cell_power_out * CELL_DATA["section_rear"]["num_me3"]
    )
    assert abs(car_cells.total_power_output() - calculated_total_power) < 0.01


def test_location(create_solar_cell):
    cell = create_solar_cell()
    loc = cell.location
    assert isinstance(loc, LocationInfo)
    assert loc.name == "Location at (34.0522, -118.2437)"
    assert loc.latitude == 34.0522
    assert loc.longitude == -118.2437
    assert loc.region == "United States"
    assert loc.timezone.utcoffset(None).total_seconds() == -18000
    print(f"Location: {loc}")


def test_sun_directly_overhead(create_solar_cell):
    # Equator, longitude 0, equinox
    location = LocationInfo(latitude=0, longitude=0)
    solar_noon = noon(observer=location.observer, date=datetime.date(2023, 3, 21), tzinfo=datetime.timezone.utc)
    cell = create_solar_cell(lat=0, lon=0, time=solar_noon, tzinfo=datetime.timezone.utc)
    # Sun elevation should be close to 90°
    assert abs(cell._sun_elevation_angle - 90) < 1, f"Sun elevation: {cell._sun_elevation_angle}"
    print(f"Sun elevation at equator on equinox at solar noon: {cell._sun_elevation_angle}°")


@pytest.mark.parametrize("tilt1, tilt2", [(0, 30), (0, -30), (30, 60), (30, -60), (60, 90), (60, -90)])
def test_tilt_differences(create_solar_cell, tilt1, tilt2):
    location = LocationInfo(latitude=0, longitude=0)
    solar_noon = noon(observer=location.observer, date=datetime.date(2023, 3, 21), tzinfo=datetime.timezone.utc)
    cell1 = create_solar_cell(lat=0, lon=0, time=solar_noon, tzinfo=datetime.timezone.utc, tilt=tilt1)
    cell2 = create_solar_cell(lat=0, lon=0, time=solar_noon, tzinfo=datetime.timezone.utc, tilt=tilt2)

    assert cell1.cell_power_out > cell2.cell_power_out


def test_time(create_solar_cell):
    cell = create_solar_cell()
    assert cell.time.tzinfo.utcoffset(None).total_seconds() == -18000
    print(f"Time: {cell.time.isoformat()}")


def test_time_now(create_solar_cell):
    cell = create_solar_cell(time=None)
    delta = (datetime.datetime.now(tz=datetime.timezone.utc) - cell.time).total_seconds()
    assert abs(delta) < 0.5, "Time should be within 0.5 seconds from now"
    assert cell.time.tzinfo.utcoffset(None).total_seconds() == 0
    print(f"Time: {cell.time.isoformat()}")


@pytest.mark.parametrize("lat,lon", [(-90, -90), (-60, -60), (-30, -30), (0, 0), (30, 30), (60, 60), (90, 90)])
def test_sun_angles(create_solar_cell, lat, lon):
    cell = create_solar_cell(lat=lat, lon=lon)
    assert 0 <= cell._sun_elevation_angle <= 90
    assert 0 <= cell._sun_azimuth_angle < 360
    print(f"Sun Elevation Angle: {cell._sun_elevation_angle} degrees")
    print(f"Sun Azimuth Angle: {cell._sun_azimuth_angle} degrees")


def test_cell_power_out(create_solar_cell):
    cell = create_solar_cell()
    power_out = round(cell.cell_power_out, 5)
    assert power_out == 2.25102, f"Power output expected 2.25102 W, actual: {power_out}"
    print(f"Cell Power Out: {cell.cell_power_out} W is approximately 2.25102 W")


@pytest.mark.parametrize("ghi", [0, -100])
def test_cell_power_out_zero(create_solar_cell, ghi):
    cell = create_solar_cell(ghi=ghi)
    assert cell.cell_power_out == 0


def test_cell_power_out_changes_with_ghi(create_solar_cell):
    cell1 = create_solar_cell(ghi=500)
    cell2 = create_solar_cell(ghi=1000)
    assert cell2.cell_power_out > cell1.cell_power_out


def test_update_power(create_solar_cell, create_segment):
    cell = create_solar_cell()
    initial_power = cell.cell_power_out
    new_segment = create_segment(lat=35.0, lon=-120.0, ghi=900)
    new_time = datetime.datetime(2023, 10, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)
    updated_power = cell.update_power(new_segment=new_segment, new_time=new_time)
    assert updated_power != initial_power
    print(f"Initial Power: {initial_power} W | Updated Power: {updated_power} W")


def test_update_power_zero_power(create_solar_cell, create_segment):
    cell = create_solar_cell()
    initial_power = cell.cell_power_out
    # GHI is set to 0, which should result in no power output
    new_segment = create_segment(ghi=0)
    updated_power = cell.update_power(new_segment=new_segment)
    assert updated_power != initial_power
    assert updated_power == 0


def test_update_cells(create_car_solar_cells, create_segment):
    car_cells = create_car_solar_cells()
    initial_power = car_cells.total_power_output()
    initial_cell_powers = [cell.cell_power_out for cell in car_cells.solar_cells]
    new_segment = create_segment(lat=35.0, lon=-120.0, ghi=900)
    new_time = datetime.datetime(2023, 10, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)
    car_cells.update_cells(new_segment=new_segment, new_time=new_time)
    updated_power = car_cells.total_power_output()
    print(f"Initial Power: {initial_power} W | Updated Power: {updated_power} W")
    assert updated_power != initial_power
    assert all(updated != initial for updated, initial in zip(car_cells, initial_cell_powers))


def test_update_cells_zero_power(create_car_solar_cells, create_segment):
    car_cells = create_car_solar_cells()
    initial_power = car_cells.total_power_output()
    # GHI is set to 0, which should result in no power output
    new_segment = create_segment(ghi=0)
    car_cells.update_cells(new_segment=new_segment)
    updated_power = car_cells.total_power_output()
    print(f"Initial Power: {initial_power} W | Updated Power: {updated_power}")
    assert updated_power != initial_power
    assert updated_power == 0
    assert all(cell.cell_power_out == 0 for cell in car_cells.solar_cells)


def test_repr(create_solar_cell):
    cell = create_solar_cell()
    repr_str = repr(cell)
    assert "CellSolarData" in repr_str
    assert "segment=" in repr_str
    assert "lon=" in repr_str
    assert "elevation=" in repr_str
    assert "time=" in repr_str
    assert "tilt=" in repr_str
    assert "heading_azimuth_angle=" in repr_str
    assert "sun_elevation_angle=" in repr_str
    assert "sun_azimuth_angle=" in repr_str
    assert "incident_diffuse=" in repr_str
    assert "cell_irradiance=" in repr_str
    assert "cell_power_out=" in repr_str
    print(f"Repr: {repr_str}")
