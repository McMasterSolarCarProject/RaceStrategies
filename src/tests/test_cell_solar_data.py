import pytest
from engine import cell_solar_data as c
from astral import LocationInfo
from astral.sun import azimuth, elevation
import math
import datetime


@pytest.fixture
def create_cell_solar_data():
    def _create(lat=34.0522, lon=-118.2437, distance=305, azimuth=180, elevation=45, ghi=800, winddir=270, windspeed=5, speedlimit=65):
        return c.CellSolarData(
            c.Checkpoint(lat, lon, distance, azimuth, elevation, ghi, winddir, windspeed, speedlimit),
            datetime.datetime(2023, 10, 1, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-5))),
            30,
        )

    return _create


def test_location(create_cell_solar_data):
    cell = create_cell_solar_data()
    loc = cell.get_location()
    assert isinstance(loc, LocationInfo)
    assert loc.name == "34.0522,-118.2437"
    assert loc.latitude == 34.0522
    assert loc.longitude == -118.2437
    assert loc.region == "United States"
    assert loc.timezone.utcoffset(None).total_seconds() == -18000


@pytest.mark.parametrize("lat,lon", [(-90, -90), (-60, -60), (-30, -30), (0, 0), (30, 30), (60, 60), (90, 90)])
def test_sun_angles(create_cell_solar_data, lat, lon):
    cell = create_cell_solar_data(lat=lat, lon=lon)
    assert 0 <= cell._sun_elevation_angle <= 90
    assert 0 <= cell._sun_azimuth_angle < 360
    print(f"Sun Elevation Angle: {cell._sun_elevation_angle} degrees")
    print(f"Sun Azimuth Angle: {cell._sun_azimuth_angle} degrees")


def test_cell_power_out(create_cell_solar_data):
    cell = create_cell_solar_data()
    power_out = round(cell.get_cell_power_out(), 5)
    assert power_out == 2.20773, "Power output should be approximately 2.20773 W"
    print(f"Cell Power Out: {cell.get_cell_power_out()} W is approximately 2.20773 W")


@pytest.mark.parametrize("ghi", [0, -100])
def test_cell_power_out_zero(create_cell_solar_data, ghi):
    cell = create_cell_solar_data(ghi=ghi)
    assert cell.get_cell_power_out() == 0


def test_cell_power_out_changes_with_ghi(create_cell_solar_data):
    cell1 = create_cell_solar_data(ghi=500)
    cell2 = create_cell_solar_data(ghi=1000)
    assert cell2.get_cell_power_out() > cell1.get_cell_power_out()


def test_repr(create_cell_solar_data):
    cell = create_cell_solar_data()
    repr_str = repr(cell)
    assert "CellSolarData" in repr_str
    assert "coord=" in repr_str
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
