from dataclasses import dataclass
from .geometry import Displacement, Coordinate, NULL_COORDINATE, Speed, Velocity, ZERO_VELOCITY


class Segment(Displacement):
    def __init__(self, p1: Coordinate, p2: Coordinate, id: int = 0, speed_limit: Speed = Speed(0), ghi: float = 0, wind: Velocity = ZERO_VELOCITY):
        self.id = id
        super().__init__(p1, p2)
        self.displacement = Displacement(p1, p2)
        self.ghi = ghi
        self.wind = wind
        self.speed_limit = speed_limit

    def __str__(self):
        return f"Segment {self.id} | Speed limit: {self.speed_limit.kmph} km/h"

NULL_SEGMENT = Segment(NULL_COORDINATE, NULL_COORDINATE)

@dataclass(frozen=True)
class Route:
    name: str
    segments: list[Segment]
    intervals: list[int]
