import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pytest
import math
from src.engine.kinematics import Vec, Coordinate, Velocity, Displacement, Speed, ZERO_VELOCITY, UNIT_VEC

# -------------------- Vec TSests --------------------

def test_vec_addition():
    v1 = Vec(1, 2, 3)
    v2 = Vec(4, 5, 6)
    v3 = v1 + v2
    assert (v3.x, v3.y, v3.z) == (5, 7, 9)

def test_vec_subtraction():
    v1 = Vec(5, 4, 3)
    v2 = Vec(1, 2, 3)
    v3 = v1 - v2
    assert (v3.x, v3.y, v3.z) == (4, 2, 0)

def test_vec_scalar_multiplication():
    v = Vec(2, 3)
    v2 = v * 3
    assert (v2.x, v2.y) == (6, 9)

def test_vec_scalar_division():
    v = Vec(4, 2)
    v2 = v / 2
    assert (v2.x, v2.y) == (2, 1)

def test_vec_magnitude():
    v = Vec(3, 4)
    assert math.isclose(v.mag, 5)

def test_vec_unit_vector_normalized():
    v = Vec(3, 4)
    u = v.unit_vector()
    assert math.isclose(u.mag, 1.0, rel_tol=1e-9)

def test_vec_unit_vector_zero():
    v = Vec(0, 0)
    u = v.unit_vector()
    assert (u.x, u.y) == (0, 1)  # handled zero division

def test_vec_trig_functions():
    v = Vec(3, 4)
    assert math.isclose(v.sin(), 4/5)
    assert math.isclose(v.cos(), 3/5)

# -------------------- Coordinate Tests --------------------

def test_coordinate_str_and_repr():
    c = Coordinate(45.0, -75.0, 100.0)
    assert "Lat" in str(c)
    assert "Lon" in repr(c)
    assert c.lat == 45.0
    assert c.lon == -75.0
    assert c.elevation == 100.0

# -------------------- Displacement Tests --------------------

def test_displacement_basic():
    p1 = Coordinate(39.092185, -94.417077, 98.46)
    p2 = Coordinate(39.092184, -94.417187, 98.49)
    d = Displacement(p1, p2)
    # Check fields exist
    assert hasattr(d, "azimuth")
    assert hasattr(d, "dist")
    assert hasattr(d, "elevation")
    assert isinstance(d.gradient, Vec)
    # Sanity check: distance should be small but positive
    assert d.dist > 0
    # Unit vector magnitude should be 1
    assert math.isclose(d.unit_vector().mag, 1.0, rel_tol=1e-9)

# -------------------- Speed Tests --------------------

def test_speed_from_mps():
    s = Speed(mps=10)
    assert math.isclose(s.kmph, 36)
    assert math.isclose(s.mph, 22.3694, rel_tol=1e-4)

def test_speed_from_kmph():
    s = Speed(kmph=36)
    assert math.isclose(s.mps, 10)
    assert math.isclose(s.mph, 22.3694, rel_tol=1e-4)

def test_speed_from_mph():
    s = Speed(mph=22.3694)
    assert math.isclose(s.mps, 10, rel_tol=1e-4)
    assert math.isclose(s.kmph, 36, rel_tol=1e-4)

def test_speed_default_zero():
    s = Speed()
    assert s.mps == s.kmph == s.mph == 0

def test_speed_rpm_classmethod():
    s = Speed.create_from_rpm(rpm=60, radius=0.2)
    expected_mps = 2 * math.pi * 0.2 * 60 / 60  # 2πr per second
    assert math.isclose(s.mps, expected_mps)

def test_speed_rpm_conversion_methods():
    s = Speed(mps=10)
    rpm_val = s.rpm(radius=0.2)
    rps_val = s.rps(radius=0.2)
    # inverse check
    assert math.isclose(rps_val * 2 * math.pi * 0.2, s.mps, rel_tol=1e-9)
    assert math.isclose(rpm_val / 60 * 2 * math.pi * 0.2, s.mps, rel_tol=1e-9)

# -------------------- Velocity Tests --------------------

def test_velocity_combination():
    v = Velocity(UNIT_VEC, Speed(mps=10))
    assert math.isclose(v.mag, 10)
    assert math.isclose(v.kmph, 36)
    assert math.isclose(v.mph, 22.3694, rel_tol=1e-4)

def test_zero_velocity_constant():
    assert isinstance(ZERO_VELOCITY, Velocity)
    assert ZERO_VELOCITY.mps == 0
    assert ZERO_VELOCITY.mag == 0
