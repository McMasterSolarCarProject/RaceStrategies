import pytest

from src.models import Segment, Route, NULL_SEGMENT
from src.config import constants




def test_route(sample_route):
    sample_segment = sample_route.segments[0]
    assert sample_segment.dist == 100
    assert sample_segment.speed_limit == constants.max_speed_limit
    assert sample_segment.gradient.mag == 100
    assert sample_segment.ghi == 0
    assert sample_segment.wind_speed == 0

def test_segment():
    segment = NULL_SEGMENT
    assert segment.dist == 0
    assert segment.speed_limit == constants.max_speed_limit
    assert segment.gradient.mag == 0
    with pytest.raises(ZeroDivisionError):
        segment.gradient.sin()
    with pytest.raises(ZeroDivisionError):
        segment.gradient.cos()
    assert segment.ghi == 0
    assert segment.wind_speed == 0
