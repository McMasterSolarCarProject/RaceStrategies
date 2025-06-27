from __future__ import annotations
from .nodes import Segment
from astral import LocationInfo
from astral.sun import azimuth, elevation
from ..utils.constants import CELL_DATA
import math
import datetime


class CarSolarCells:
    """
    This class will contain all the solar cells for a car.
    """

    def __init__(self, segment: Segment, time: datetime.datetime = None):
        assert isinstance(segment, Segment), "segment must be an instance of Segment"
        if time:
            assert isinstance(time, datetime.datetime), "time must be a datetime object"
            if time.tzinfo is None:
                time = time.replace(tzinfo=datetime.timezone.utc)
        else:
            time = datetime.datetime.now(datetime.timezone.utc)

        self._segment = segment
        self._time = time
        self._solar_cells = []
        cell_types = ["me3", "ne3"]

        for section in CELL_DATA.keys():
            if section.startswith("section_"):
                for cell_type in cell_types:
                    for _ in range(CELL_DATA[section][f"num_{cell_type}"]):
                        cell = SolarCell(self._segment, CELL_DATA[section]["tilt"], self._time, CELL_DATA[f"{cell_type}_eff"])
                        self._solar_cells.append(cell)

    def update_cells(self, new_segment: Segment = None, new_time: datetime.datetime = None):
        """
        Updates the solar cells with new segment and time.
        """
        if new_segment:
            assert isinstance(new_segment, Segment), "new_segment must be an instance of Segment"
            self._segment = new_segment
        if new_time:
            assert isinstance(new_time, datetime.datetime), "new_time must be a datetime object"
            assert hasattr(new_time, "tzinfo"), "new_time must have timezone information"
            self._time = new_time
        else:
            self._time = datetime.datetime.now(datetime.timezone.utc)

        for cell in self._solar_cells:
            cell.update_power(new_segment, new_time)

    @property
    def solar_cells(self) -> list[SolarCell]:
        """
        Returns the list of solar cells.
        """
        return self._solar_cells

    def total_power_output(self) -> float:
        """
        Calculates the total power output of all solar cells.
        """
        return sum(cell.cell_power_out for cell in self._solar_cells)

    def __iter__(self):
        """
        Returns an iterator over the solar cells.
        """
        return iter(self._solar_cells)


class SolarCell:
    """
    This class calculates the power output of a solar cell based on the location, time, and tilt angle.
    """

    def __init__(self, segment: Segment, tilt: float, time: datetime.datetime, cell_eff: float):
        assert isinstance(segment, Segment), "segment must be an instance of Segment"
        assert isinstance(tilt, (int, float)), "tilt must be a number"
        if time:
            assert isinstance(time, datetime.datetime), "time must be a datetime object"
            if time.tzinfo is None:
                time = time.replace(tzinfo=datetime.timezone.utc)
        else:
            time = datetime.datetime.now(datetime.timezone.utc)
        assert isinstance(cell_eff, (int, float)), "cell_eff must be a number"

        self._eff = cell_eff
        self._segment = segment
        self._tilt = tilt
        self._time = time

        self._calculate_cell_power_out()

    def _calculate_cell_power_out(self) -> float:
        """
        Calculates the power output of the solar cell based on the current conditions.
        """
        self._lat = self._segment.p1.lat
        self._lon = self._segment.p1.lon
        self._elevation = self._segment.p1.elevation / 1000  # km

        azimuth_angle = self._segment.azimuth

        assert 0 <= azimuth_angle <= 360, "Azimuth angle must be between 0 and 360 degrees"
        self._heading_azimuth_angle = (azimuth_angle + (180 if self._tilt < 0 else 0)) % 360
        self._incident_diffuse = self._segment.ghi  # W/m^2

        self._location = LocationInfo(f"Location at ({self._lat}, {self._lon})", "United States", self._time.tzinfo, self._lat, self._lon)
        self._sun_elevation_angle = max(0, elevation(self._location.observer, self._time))
        self._sun_azimuth_angle = azimuth(self._location.observer, self._time)

        self._cell_irradiance = self._incident_diffuse * (
            math.cos(math.radians(self._sun_elevation_angle)) * math.sin(math.radians(self._tilt)) * math.cos(math.radians(self._heading_azimuth_angle - self._sun_azimuth_angle))
            + math.sin(math.radians(self._sun_elevation_angle)) * math.cos(math.radians(self._tilt))
        )

        if isinstance(self._incident_diffuse, complex):
            print("Complex incident diffuse value detected.")
            print(self._incident_diffuse, self._sun_elevation_angle, self._tilt, self._heading_azimuth_angle, self._sun_azimuth_angle, self._time)

        # change to use irradiance data from API
        self._cell_power_out = max(0, self._cell_irradiance * self._eff * CELL_DATA["cell_area"])  # watts

    def update_power(self, new_segment: Segment = None, new_time: datetime.datetime = None) -> float:
        """
        Updates the segment and time for the solar cell data, and recalculates the power output.
        """
        if new_segment:
            assert isinstance(new_segment, Segment), "new_segment must be an instance of Segment"
            self._segment = new_segment
        if new_time:
            assert isinstance(new_time, datetime.datetime), "new_time must be a datetime object"
            assert hasattr(new_time, "tzinfo"), "new_time must have timezone information"
            self._time = new_time
        else:
            self._time = datetime.datetime.now(datetime.timezone.utc)

        self._calculate_cell_power_out()
        return self.cell_power_out

    @property
    def segment(self) -> Segment:
        """
        Returns the segment instance variable.
        """
        return self._segment

    @property
    def time(self) -> datetime.datetime:
        """
        Returns the time instance variable.
        """
        return self._time

    @property
    def location(self) -> LocationInfo:
        """
        Returns the LocationInfo object representing the solar cell's location.
        """
        return self._location

    @property
    def cell_power_out(self) -> float:
        """
        Returns the power output of the solar cell in watts.
        """
        return self._cell_power_out

    def __repr__(self) -> str:
        return (
            f"CellSolarData(segment={self._segment}, lon={self._lon}, elevation={self._elevation}, "
            f"time={self._time}, tilt={self._tilt}, heading_azimuth_angle={self._heading_azimuth_angle}, "
            f"sun_elevation_angle={self._sun_elevation_angle}, sun_azimuth_angle={self._sun_azimuth_angle}, "
            f"incident_diffuse={self._incident_diffuse}, cell_irradiance={self._cell_irradiance}, "
            f"cell_power_out={self._cell_power_out})"
        )
