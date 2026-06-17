from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Iterable
import tomllib


BUILTIN_PROFILES_PATH = Path(__file__).with_name("physics_profiles.toml")


@dataclass(frozen=True)
class PhysicsConstants:
    accel_g: float = 9.81  # m/s^2
    air_density: float = 1.225  # kg/m^3


@dataclass(frozen=True)
class VehicleConfig:
    car_mass: float = 750.0  # kg
    coef_drag: float = 0.15
    coef_rr: float = 0.0075
    cross_section: float = 2.8  # m^2


@dataclass(frozen=True)
class BatteryConfig:
    battery_c_rated: float = 180.0
    battery_voltage: float = 101.64
    passive_consumption: float = 7.5  # Watts
    regen_eff: float = 0.05  # %


@dataclass(frozen=True)
class SolarConfig:
    cell_area: float = 0.0153  # m^2


@dataclass(frozen=True)
class MotorConfig:
    num_motors: int = 2
    wheel_radius: float = 0.2  # m


@dataclass(frozen=True)
class CarProfile:
    name: str = "default"
    physics: PhysicsConstants = field(default_factory=PhysicsConstants)
    vehicle: VehicleConfig = field(default_factory=VehicleConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    solar: SolarConfig = field(default_factory=SolarConfig)
    motor: MotorConfig = field(default_factory=MotorConfig)

    def override(self, dotted_path: str, value: Any) -> CarProfile:
        return self.with_overrides({dotted_path: value})

    def with_overrides(self, overrides: dict[str, Any]) -> CarProfile:
        updated = self
        for dotted_path, value in overrides.items():
            updated = _set_dotted_value(updated, dotted_path, value)
        return updated

    def variation(self, dotted_path: str, values: Iterable[Any]) -> list[CarProfile]:
        return [self.override(dotted_path, value) for value in values]


@dataclass(frozen=True)
class ProfileDefinition:
    name: str
    extends: str | None = None
    physics: dict[str, Any] = field(default_factory=dict)
    vehicle: dict[str, Any] = field(default_factory=dict)
    battery: dict[str, Any] = field(default_factory=dict)
    solar: dict[str, Any] = field(default_factory=dict)
    motor: dict[str, Any] = field(default_factory=dict)


DEFAULT_PROFILE_NAME = "default"


def load_profiles(path: str | Path) -> dict[str, CarProfile]:
    with Path(path).open("rb") as file:
        raw_data = tomllib.load(file)

    definitions = _parse_profile_definitions(raw_data)
    resolved: dict[str, CarProfile] = {}
    for name in definitions:
        resolved[name] = _resolve_profile(name, definitions, resolved, stack=[])
    return resolved


def load_profile(path: str | Path, name: str = DEFAULT_PROFILE_NAME) -> CarProfile:
    profiles = load_profiles(path)
    try:
        return profiles[name]
    except KeyError as error:
        available = ", ".join(sorted(profiles)) or "<none>"
        raise KeyError(f"Unknown profile '{name}'. Available profiles: {available}") from error


def load_builtin_profile(name: str = DEFAULT_PROFILE_NAME) -> CarProfile:
    return load_profile(BUILTIN_PROFILES_PATH, name=name)


def load_builtin_profiles() -> dict[str, CarProfile]:
    return load_profiles(BUILTIN_PROFILES_PATH)


def _parse_profile_definitions(raw_data: dict[str, Any]) -> dict[str, ProfileDefinition]:
    profiles_table = raw_data.get("profiles", raw_data)
    if not isinstance(profiles_table, dict):
        raise TypeError("Expected a TOML table named 'profiles'.")

    definitions: dict[str, ProfileDefinition] = {}
    for name, profile_data in profiles_table.items():
        if not isinstance(profile_data, dict):
            continue

        definitions[name] = ProfileDefinition(
            name=name,
            extends=profile_data.get("extends"),
            physics=dict(profile_data.get("physics", {})),
            vehicle=dict(profile_data.get("vehicle", {})),
            battery=dict(profile_data.get("battery", {})),
            solar=dict(profile_data.get("solar", {})),
            motor=dict(profile_data.get("motor", {})),
        )

    return definitions


def _resolve_profile(
    name: str,
    definitions: dict[str, ProfileDefinition],
    resolved: dict[str, CarProfile],
    stack: list[str],
) -> CarProfile:
    if name in resolved:
        return resolved[name]

    if name in stack:
        cycle = " -> ".join(stack + [name])
        raise ValueError(f"Profile inheritance cycle detected: {cycle}")

    try:
        definition = definitions[name]
    except KeyError as error:
        raise KeyError(f"Profile '{name}' is not defined.") from error

    stack.append(name)
    if definition.extends is None:
        base_profile = CarProfile(name=name)
    else:
        base_profile = _resolve_profile(definition.extends, definitions, resolved, stack)

    profile = replace(
        base_profile,
        name=name,
        physics=_merge_section(base_profile.physics, definition.physics),
        vehicle=_merge_section(base_profile.vehicle, definition.vehicle),
        battery=_merge_section(base_profile.battery, definition.battery),
        solar=_merge_section(base_profile.solar, definition.solar),
        motor=_merge_section(base_profile.motor, definition.motor),
    )
    stack.pop()
    resolved[name] = profile
    return profile


def _merge_section(base: Any, overrides: dict[str, Any]) -> Any:
    if not overrides:
        return base

    invalid_keys = [key for key in overrides if not hasattr(base, key)]
    if invalid_keys:
        invalid = ", ".join(sorted(invalid_keys))
        raise KeyError(f"Unknown config field(s) '{invalid}' for {type(base).__name__}.")

    return replace(base, **overrides)


def _set_dotted_value(profile: CarProfile, dotted_path: str, value: Any) -> CarProfile:
    section_name, field_name = _split_dotted_path(dotted_path)
    section = getattr(profile, section_name)
    if not hasattr(section, field_name):
        raise KeyError(f"Unknown config field '{field_name}' for {type(section).__name__}.")

    updated_section = replace(section, **{field_name: value})
    return replace(profile, **{section_name: updated_section})


def _split_dotted_path(dotted_path: str) -> tuple[str, str]:
    parts = dotted_path.split(".")
    if len(parts) != 2:
        raise ValueError(f"Config override paths must look like 'section.field'; got '{dotted_path}'.")

    section_name, field_name = parts
    valid_sections = {field.name for field in fields(CarProfile) if field.name != "name"}
    if section_name not in valid_sections:
        raise KeyError(f"Unknown config section '{section_name}'.")

    return section_name, field_name
