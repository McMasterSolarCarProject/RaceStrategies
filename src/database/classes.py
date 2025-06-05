from __future__ import annotations
from ..engine.kinematics import Coordinate

# class Coordinate:
#     def __init__(self, lon: float, lat: float, elevation: float):
#         self.lon = lon
#         self.lat = lat
#         self.elevation = elevation
#
#     def __str__(self):
#         return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"
#
#     def __repr__(self):
#         return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"

class Placemark:
    def __init__(self, name: str, coords: list[Coordinate]):
        self.name = name
        self.coords = coords

    def __str__(self):
        return f"{self.name}: {self.coords}"

    def __repr__(self):
        return f"{self.name}: {self.coords}"