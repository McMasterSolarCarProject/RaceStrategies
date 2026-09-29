import pytest

from src.config import constants
from src.models import Vec, Segment, Route, NULL_COORDINATE, coordinate_from_displacement

@pytest.fixture
def sample_segment():
    segment = Segment(NULL_COORDINATE, coordinate_from_displacement(NULL_COORDINATE, Vec(100, 0), 0))
    assert segment.dist == 100
    assert segment.speed_limit == constants.max_speed_limit
    assert segment.gradient.mag == 100
    assert segment.gradient.sin() == 0
    assert segment.gradient.cos() == 1
    assert segment.ghi == 0
    assert segment.wind_speed == 0
    return segment

@pytest.fixture
def sample_route(sample_segment):
    return Route(name="Test Route", segments=[sample_segment])
