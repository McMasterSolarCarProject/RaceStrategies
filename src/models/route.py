from dataclasses import dataclass
from .geometry import Displacement, Coordinate, NULL_COORDINATE, Speed, Velocity, ZERO_VELOCITY
from ..config import constants

class Segment(Displacement):
    def __init__(self, p1: Coordinate, p2: Coordinate, id: int = 0, speed_limit: Speed = Speed(constants.max_speed_limit), ghi: float = 0, wind: Velocity = ZERO_VELOCITY):
        self.id = id
        super().__init__(p1, p2)
        self.displacement = Displacement(p1, p2)
        self.ghi = ghi
        self.wind = wind
        self.wind_speed = wind.project_onto(self.unit_vector()).mag
        self.speed_limit = speed_limit.mps

    def __str__(self):
        return f"Segment {self.id} | Speed limit: {self.speed_limit} m/s"

NULL_SEGMENT = Segment(NULL_COORDINATE, NULL_COORDINATE)

@dataclass(frozen=True)
class Route:
    name: str
    segments: list[Segment]
    # intervals: list[int]
