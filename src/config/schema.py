from dataclasses import dataclass, field


@dataclass
class PhysicsConstants:
    accel_g: float = 9.81  # m/s^2
    air_density: float = 1.204  # kg/m^3

@dataclass
class VehicleConfig:
    car_mass: float = 575.0 #kg
    coef_drag: float = 0.19
    coef_rr: float = 0.0023
    cross_section = 2.21  # m^2

@dataclass
class BatteryConfig:
    battery_c_rated: float = 180.0
    battery_voltage: float = 101.64
    passive_consumption: float = 7.5  # Watts
    regen_eff: float = 0.05  # %

@dataclass
class MotorConfig:
    num_motors: int = 2
    wheel_radius: float = 0.2  # m



