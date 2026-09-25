from pathlib import Path
from dataclasses import dataclass, replace
import tomllib

profile_path = Path(__file__).with_name("profile_configs.toml")
default_path = Path(__file__).with_name("default_configs.toml")

@dataclass(frozen=True)
class Constants:
    g: float
    air_density: float


@dataclass(frozen=True)
class Vehicle:
    name: str
    car_mass: float
    coef_drag: float
    coef_rr: float
    cross_section: float

    c_rated: float
    battery_voltage: float
    passive_consumption: float
    regen_eff: float

    cell_area: float

    num_motors: int
    wheel_radius: float


@dataclass(frozen=True)
class Engine:
    name: str
    time_step: float


def load_default_configs()-> tuple[Constants, Vehicle, Engine]:
    with open(default_path, "rb") as f:
        raw_data = tomllib.load(f)

    constants = Constants(**raw_data["Constants"])
    vehicle_default = Vehicle(**raw_data["Vehicle"]["default"])
    engine_default = Engine(**raw_data["Engine"]["default"])

    return constants, vehicle_default, engine_default

constants, vehicle_default, engine_default = load_default_configs()


def load_vehicle_config(vehicle_name: str, parent_vehicle: Vehicle = vehicle_default):
    with profile_path.open("rb") as f:
        raw_data = tomllib.load(f)
    profile_values = raw_data["Vehicle"][vehicle_name]
    return replace(parent_vehicle, **profile_values)

def load_engine_config(engine_name: str, parent_engine: Engine = engine_default):
    with profile_path.open("rb") as f:
        raw_data = tomllib.load(f)
    profile_values = raw_data["Engine"][engine_name]
    return replace(parent_engine, **profile_values)


def config_variations(attributes: list[str], values: list[list], base_config) -> list:
    variations = []

    for row in zip(*values):
        changes = dict(zip(attributes, row))
        variations.append(replace(base_config, **changes))
    return variations

if __name__ == "__main__":
    with profile_path.open("rb") as f:
        raw_data = tomllib.load(f)
    print(raw_data["Vehicle"]["mass_sweep_725"])