from pathlib import Path

from src.config.schema import load_builtin_profile, load_profiles


def write_profile_file(tmp_path: Path) -> Path:
    profile_file = tmp_path / "physics_profiles.toml"
    profile_file.write_text(
        """[profiles.base.physics]
accel_g = 9.81
air_density = 1.2

[profiles.base.vehicle]
car_mass = 750.0
coef_drag = 0.15
coef_rr = 0.0075
cross_section = 2.8

[profiles.base.battery]
battery_c_rated = 180.0
battery_voltage = 101.64
passive_consumption = 7.5
regen_eff = 0.05

[profiles.base.motor]
num_motors = 2
wheel_radius = 0.2

[profiles.child]
extends = "base"

[profiles.child.vehicle]
car_mass = 700.0
coef_drag = 0.12
""",
        encoding="utf-8",
    )
    return profile_file


def test_load_profiles_resolves_inheritance(tmp_path):
    profile_file = write_profile_file(tmp_path)

    profiles = load_profiles(profile_file)

    assert profiles["base"].vehicle.car_mass == 750.0
    assert profiles["child"].vehicle.car_mass == 700.0
    assert profiles["child"].vehicle.coef_drag == 0.12
    assert profiles["child"].physics.air_density == 1.2


def test_profile_variation_overrides_a_single_value(tmp_path):
    profile_file = write_profile_file(tmp_path)
    profile = load_profiles(profile_file)["base"]

    variants = profile.variation("vehicle.car_mass", [725.0, 775.0])

    assert [variant.vehicle.car_mass for variant in variants] == [725.0, 775.0]
    assert [variant.vehicle.coef_drag for variant in variants] == [0.15, 0.15]


def test_builtin_profile_file_loads():
    profile = load_builtin_profile()

    assert profile.name == "default"
    assert profile.vehicle.car_mass == 750.0
