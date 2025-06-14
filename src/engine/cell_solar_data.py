from __future__ import annotations
from .checkpoint import Checkpoint
from astral import LocationInfo
from astral.sun import azimuth, elevation
from utils.constants import CELL_AREA
import math
import datetime


class CellSolarData:
    """
    This class calculates the power output of a solar cell based on the location, time, and tilt angle.
    """
    def __init__(self, coord: Checkpoint, time: datetime.datetime, tilt: float):
        assert isinstance(coord, Checkpoint), "coord must be an instance of Checkpoint"
        assert isinstance(time, datetime.datetime), "time must be a datetime object"
        assert isinstance(tilt, (int, float)), "tilt must be a number"

        self._EFF = 0.24
        self._coord = coord
        self._heading_azimuth_angle = (coord.get_azimuth() + (180 if tilt < 0 else 0)) % 360
        self._tilt = abs(tilt)

        self._lat = coord.get_lat()
        self._lon = coord.get_lon()
        self._elevation = coord.get_elevation() / 1000  # Convert to km
        self._time = time  # make this dynamic

        self._location = LocationInfo(f"{self._lat},{self._lon}", "United States", self._time.tzinfo, self._lat, self._lon)
        self._sun_elevation_angle = max(0, elevation(self._location.observer, self._time))
        self._sun_azimuth_angle = azimuth(self._location.observer, self._time)

        self._incident_diffuse = coord.get_ghi()  # W/m^2
        self._cell_irradiance = self._incident_diffuse * (
            math.cos(math.radians(self._sun_elevation_angle)) * math.sin(math.radians(self._tilt)) * math.cos(math.radians(self._heading_azimuth_angle - self._sun_azimuth_angle))
            + math.sin(math.radians(self._sun_elevation_angle)) * math.cos(math.radians(self._tilt))
        )

        if isinstance(self._incident_diffuse, complex):
            print(self._incident_diffuse, self._sun_elevation_angle, self._tilt, self._heading_azimuth_angle, self._sun_azimuth_angle, self._time)

        # change to use irradiance data from API
        self._cell_power_out = max(0, self._cell_irradiance * self._EFF * CELL_AREA)  # watts

    def get_location(self) -> float:
        """
        Returns the location information of the vehicle.
        """
        return self._location

    def get_cell_power_out(self) -> float:
        """
        Returns the power output of the solar cell in watts.
        """
        return self._cell_power_out

    def __repr__(self) -> str:
        return (
            f"CellSolarData(coord={self._coord}, lon={self._lon}, elevation={self._elevation}, "
            f"time={self._time}, tilt={self._tilt}, heading_azimuth_angle={self._heading_azimuth_angle}, "
            f"sun_elevation_angle={self._sun_elevation_angle}, sun_azimuth_angle={self._sun_azimuth_angle}, "
            f"incident_diffuse={self._incident_diffuse}, cell_irradiance={self._cell_irradiance}, "
            f"cell_power_out={self._cell_power_out})"
        )
