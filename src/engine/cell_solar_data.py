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

    def __init__(self, coord: Checkpoint, tilt: float, time: datetime.datetime = None):
        assert isinstance(coord, Checkpoint), "coord must be an instance of Checkpoint"
        assert isinstance(tilt, (int, float)), "tilt must be a number"
        if time:
            assert isinstance(time, datetime.datetime), "time must be a datetime object"
            assert hasattr(time, "tzinfo"), "time must have timezone information"
        else:
            time = datetime.datetime.now(datetime.timezone.utc)

        self._EFF = 0.24
        self._coord = coord
        self._tilt = abs(tilt)
        if time:
            self._time = time
        else:
            self._time = datetime.datetime.now(datetime.timezone.utc)

        self._calculate_cell_power_out()

    def _calculate_cell_power_out(self) -> float:
        """
        Calculates the power output of the solar cell based on the current conditions.
        """

        self._lat = self._coord.get_lat()
        self._lon = self._coord.get_lon()
        self._elevation = self._coord.get_elevation() / 1000  # Convert to km
        self._heading_azimuth_angle = (self._coord.get_azimuth() + (180 if self._tilt < 0 else 0)) % 360
        self._incident_diffuse = self._coord.get_ghi()  # W/m^2

        self._location = LocationInfo(f"{self._lat},{self._lon}", "United States", self._time.tzinfo, self._lat, self._lon)
        self._sun_elevation_angle = max(0, elevation(self._location.observer, self._time))
        self._sun_azimuth_angle = azimuth(self._location.observer, self._time)

        self._cell_irradiance = self._incident_diffuse * (
            math.cos(math.radians(self._sun_elevation_angle)) * math.sin(math.radians(self._tilt)) * math.cos(math.radians(self._heading_azimuth_angle - self._sun_azimuth_angle))
            + math.sin(math.radians(self._sun_elevation_angle)) * math.cos(math.radians(self._tilt))
        )

        if isinstance(self._incident_diffuse, complex):
            print(self._incident_diffuse, self._sun_elevation_angle, self._tilt, self._heading_azimuth_angle, self._sun_azimuth_angle, self._time)

        # change to use irradiance data from API
        self._cell_power_out = max(0, self._cell_irradiance * self._EFF * CELL_AREA)  # watts

    def update_power(self, new_coord: Checkpoint = None, new_time: datetime.datetime = None) -> float:
        """
        Updates the coordinate and time for the solar cell data, and recalculates the power output.
        """
        if new_coord:
            assert isinstance(new_coord, Checkpoint), "new_coord must be an instance of Checkpoint"
            self._coord = new_coord
        if new_time:
            assert isinstance(new_time, datetime.datetime), "new_time must be a datetime object"
            assert hasattr(new_time, "tzinfo"), "new_time must have timezone information"
            self._time = new_time
        else:
            self._time = datetime.datetime.now(datetime.timezone.utc)

        self._calculate_cell_power_out()
        return self.get_cell_power_out()

    def get_coord(self) -> Checkpoint:
        """
        Returns the coord instance variable.
        """
        return self._coord

    def get_time(self) -> datetime.datetime:
        """
        Returns the time instance variable.
        """
        return self._time

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
