from src.config import load_builtin_profile
from src.engine.kinematics import Speed


def test_profile_overrides_apply_to_speed():
    profile = load_builtin_profile().with_overrides(
        {
            "vehicle.car_mass": 701.0,
            "motor.wheel_radius": 0.25,
            "solar.cell_area": 0.02,
        }
    )

    assert profile.vehicle.car_mass == 701.0
    assert profile.motor.wheel_radius == 0.25
    assert profile.solar.cell_area == 0.02
    assert Speed(mps=10).rpm(radius=profile.motor.wheel_radius) == Speed(mps=10).rpm(radius=0.25)
