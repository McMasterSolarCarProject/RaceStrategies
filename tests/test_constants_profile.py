from src.config import load_builtin_profile
from src.engine.kinematics import Speed
from src.utils import constants


def test_set_active_profile_updates_constants_and_dynamic_defaults():
    original_profile = constants.get_active_profile()
    try:
        profile = load_builtin_profile().with_overrides(
            {
                "vehicle.car_mass": 701.0,
                "motor.wheel_radius": 0.25,
                "solar.cell_area": 0.02,
            }
        )
        constants.set_active_profile(profile)

        assert constants.car_mass == 701.0
        assert constants.wheel_radius == 0.25
        assert constants.CELL_AREA == 0.02
        assert Speed(mps=10).rpm() == Speed(mps=10).rpm(radius=0.25)
    finally:
        constants.set_active_profile(original_profile)
