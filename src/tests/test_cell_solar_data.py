import pytest
from engine.cell_solar_data import CellSolarData
from engine.checkpoint import Checkpoint
from astral import LocationInfo
from astral.sun import noon
import math
import datetime


@pytest.fixture
def create_checkpoint():
    def _create(
        lat=34.0522,
        lon=-118.2437,
        distance=305,
        azimuth=180,
        elevation=45,
        ghi=800,
        winddir=270,
        windspeed=5,
        speedlimit=65,
    ):
        return Checkpoint(lat, lon, distance, azimuth, elevation, ghi, winddir, windspeed, speedlimit)

    return _create


@pytest.fixture
def create_cell_solar_data(create_checkpoint):
    def _create(
        lat=34.0522,
        lon=-118.2437,
        distance=305,
        azimuth=180,
        elevation=45,
        ghi=800,
        winddir=270,
        windspeed=5,
        speedlimit=65,
        tilt=30,
        time=datetime.datetime(2023, 10, 1, 12, 0, 0),
        tzinfo=datetime.timezone(datetime.timedelta(hours=-5)),
    ):
        checkpoint = create_checkpoint(lat, lon, distance, azimuth, elevation, ghi, winddir, windspeed, speedlimit)
        # checkpoint = Checkpoint(lat, lon, distance, azimuth, elevation, ghi, winddir, windspeed, speedlimit)
        time = time.replace(tzinfo=tzinfo) if time else None
        return CellSolarData(checkpoint, tilt, time)

    return _create


def test_location(create_cell_solar_data):
    cell = create_cell_solar_data()
    loc = cell.location
    assert isinstance(loc, LocationInfo)
    assert loc.name == "Location at (34.0522, -118.2437)"
    assert loc.latitude == 34.0522
    assert loc.longitude == -118.2437
    assert loc.region == "United States"
    assert loc.timezone.utcoffset(None).total_seconds() == -18000
    print(f"Location: {loc}")


def test_sun_directly_overhead(create_cell_solar_data):
    # Equator, longitude 0, equinox
    location = LocationInfo(latitude=0, longitude=0)
    solar_noon = noon(observer=location.observer, date=datetime.date(2023, 3, 21), tzinfo=datetime.timezone.utc)
    cell = create_cell_solar_data(lat=0, lon=0, time=solar_noon, tzinfo=datetime.timezone.utc)
    # Sun elevation should be close to 90°
    assert abs(cell._sun_elevation_angle - 90) < 1, f"Sun elevation: {cell._sun_elevation_angle}"
    print(f"Sun elevation at equator on equinox at solar noon: {cell._sun_elevation_angle}°")


@pytest.mark.parametrize("tilt1, tilt2", [(0, 30), (0, -30), (30, 60), (30, -60), (60, 90), (60, -90)])
def test_tilt_differences(create_cell_solar_data, tilt1, tilt2):
    location = LocationInfo(latitude=0, longitude=0)
    solar_noon = noon(observer=location.observer, date=datetime.date(2023, 3, 21), tzinfo=datetime.timezone.utc)
    cell1 = create_cell_solar_data(lat=0, lon=0, time=solar_noon, tzinfo=datetime.timezone.utc, tilt=tilt1)
    cell2 = create_cell_solar_data(lat=0, lon=0, time=solar_noon, tzinfo=datetime.timezone.utc, tilt=tilt2)

    assert cell1.cell_power_out > cell2.cell_power_out


def test_time(create_cell_solar_data):
    cell = create_cell_solar_data()
    assert cell.time.tzinfo.utcoffset(None).total_seconds() == -18000
    print(f"Time: {cell.time.isoformat()}")


def test_time_now(create_cell_solar_data):
    cell = create_cell_solar_data(time=None)
    delta = (datetime.datetime.now(tz=datetime.timezone.utc) - cell.time).total_seconds()
    assert abs(delta) < 0.5, "Time should be within 0.5 seconds from now"
    assert cell.time.tzinfo.utcoffset(None).total_seconds() == 0
    print(f"Time: {cell.time.isoformat()}")


@pytest.mark.parametrize("lat,lon", [(-90, -90), (-60, -60), (-30, -30), (0, 0), (30, 30), (60, 60), (90, 90)])
def test_sun_angles(create_cell_solar_data, lat, lon):
    cell = create_cell_solar_data(lat=lat, lon=lon)
    assert 0 <= cell._sun_elevation_angle <= 90
    assert 0 <= cell._sun_azimuth_angle < 360
    print(f"Sun Elevation Angle: {cell._sun_elevation_angle} degrees")
    print(f"Sun Azimuth Angle: {cell._sun_azimuth_angle} degrees")


def test_cell_power_out(create_cell_solar_data):
    cell = create_cell_solar_data()
    power_out = round(cell.cell_power_out, 5)
    assert power_out == 2.20773, f"Power output expected 2.20773 W, actual: {power_out}"
    print(f"Cell Power Out: {cell.cell_power_out} W is approximately 2.20773 W")


@pytest.mark.parametrize("ghi", [0, -100])
def test_cell_power_out_zero(create_cell_solar_data, ghi):
    cell = create_cell_solar_data(ghi=ghi)
    assert cell.cell_power_out == 0


def test_cell_power_out_changes_with_ghi(create_cell_solar_data):
    cell1 = create_cell_solar_data(ghi=500)
    cell2 = create_cell_solar_data(ghi=1000)
    assert cell2.cell_power_out > cell1.cell_power_out


def test_update_power(create_cell_solar_data, create_checkpoint):
    cell = create_cell_solar_data()
    initial_power = cell.cell_power_out
    new_coord = create_checkpoint(lat=35.0, lon=-120.0, ghi=900)
    new_time = datetime.datetime(2023, 10, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)
    updated_power = cell.update_power(new_coord=new_coord, new_time=new_time)
    assert updated_power != initial_power
    print(f"Initial Power: {initial_power} W | Updated Power: {updated_power} W")


def test_update_power_zero_power(create_cell_solar_data, create_checkpoint):
    cell = create_cell_solar_data()
    initial_power = cell.cell_power_out
    # GHI is set to 0, which should result in no power output
    new_coord = create_checkpoint(ghi=0)
    updated_power = cell.update_power(new_coord=new_coord)
    assert updated_power != initial_power
    assert updated_power == 0


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
