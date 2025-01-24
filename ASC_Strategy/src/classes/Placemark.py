from __future__ import annotations
from classes import Coordinate


class Placemark:
    def __init__(self, name: str, coords: list[Coordinate]):
        self.name = name
        self.coords = coords

    def __str__(self):
        return f"{self.name}: {self.coords}"

    def __repr__(self):
        return f"{self.name}: {self.coords}"