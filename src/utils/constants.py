from pathlib import Path
import os

from ..config import CarProfile, DEFAULT_PROFILE_NAME, load_builtin_profile, load_profile


GRAPH_OUTPUT_DIR = "graphs/"
DATA_DIR = "data/"


def _apply_profile(profile: CarProfile) -> None:
    global ACTIVE_PROFILE
    global num_motors, CELL_AREA, air_density, coef_drag, coef_rr, car_mass, accel_g, wheel_radius
    global cross_section, passive_consumption, regen_eff, battery_c_rated, battery_voltage

    ACTIVE_PROFILE = profile
    num_motors = profile.motor.num_motors
    CELL_AREA = profile.solar.cell_area
    air_density = profile.physics.air_density
    coef_drag = profile.vehicle.coef_drag
    coef_rr = profile.vehicle.coef_rr
    car_mass = profile.vehicle.car_mass
    accel_g = profile.physics.accel_g
    wheel_radius = profile.motor.wheel_radius
    cross_section = profile.vehicle.cross_section
    passive_consumption = profile.battery.passive_consumption
    regen_eff = profile.battery.regen_eff
    battery_c_rated = profile.battery.battery_c_rated
    battery_voltage = profile.battery.battery_voltage


def get_active_profile() -> CarProfile:
    return ACTIVE_PROFILE


def set_active_profile(profile: CarProfile) -> CarProfile:
    _apply_profile(profile)
    return profile


def use_builtin_profile(name: str = DEFAULT_PROFILE_NAME) -> CarProfile:
    return set_active_profile(load_builtin_profile(name))


def load_profile_from_file(path: str | Path, name: str = DEFAULT_PROFILE_NAME) -> CarProfile:
    return set_active_profile(load_profile(path, name=name))


ACTIVE_PROFILE = load_builtin_profile()
_apply_profile(ACTIVE_PROFILE)

eff_factor = 0.5  # a lower value will produce higher speeds


def save_plot(plot, filename):
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(GRAPH_OUTPUT_DIR, filename)
    plot.savefig(filepath)
    print(f"Graph saved to {filepath}")

TILTS = {
    "hood_front": {
        "left_stairs": [33.38, 27.64, 27.64, 27.63, 27.63, 27.63, 27.44, 27.44, 27.44],
        "left_center_3x4": [
            33.38,
            33.38,
            33.38,
            27.64,
            27.64,
            27.64,
            27.63,
            27.63,
            27.63,
            27.44,
            27.44,
            27.44,
        ],
        "right_center_3x4": [
            33.38,
            33.38,
            33.38,
            27.64,
            27.64,
            27.64,
            27.63,
            27.63,
            27.63,
            27.44,
            27.44,
            27.44,
        ],
        "right_stairs": [33.38, 27.64, 27.64, 27.63, 27.63, 27.63, 27.44, 27.44, 27.44],
    },
    "top_front": {
        "leftmost_top_3x2": [28.52, 28.52, 28.52, 22.16, 22.16, 22.16],
        "leftmost_center_3x2": [22.16, 22.16, 22.16, 22.16, 22.16, 22.16],
        "leftmost_bottom_3x2": [13.14, 13.14, 13.14, 13.14, 13.14, 13.14],
        "leftcenter_top_3x2": [28.52, 28.52, 28.52, 22.16, 22.16, 22.16],
        "leftcenter_center_3x2": [22.16, 22.16, 22.16, 22.16, 22.16, 22.16],
        "leftcenter_bottom_3x2": [13.14, 13.14, 13.14, 13.14, 13.14, 13.14],
        "rightcenter_top_3x2": [28.52, 28.52, 28.52, 22.16, 22.16, 22.16],
        "rightcenter_center_3x2": [22.16, 22.16, 22.16, 22.16, 22.16, 22.16],
        "rightcenter_bottom_3x2": [13.14, 13.14, 13.14, 13.14, 13.14, 13.14],
        "rightmost_top_4x3": [
            28.52,
            28.52,
            28.52,
            28.52,
            22.16,
            22.16,
            22.16,
            22.16,
            22.16,
            22.16,
            22.16,
            22.16,
        ],
        "rightmost_bottom_4x3": [
            22.16,
            22.16,
            22.16,
            22.16,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
        ],
    },
    "top_back": {
        "leftmost_3x4": [
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            1.11,
            1.11,
            1.11,
            -3.64,
            -3.64,
            -3.64,
        ],
        "leftcenter_3x4": [
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            1.11,
            1.11,
            1.11,
            -3.64,
            -3.64,
            -3.64,
        ],
        "rightcenter_3x4": [
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            1.11,
            1.11,
            1.11,
            -3.64,
            -3.64,
            -3.64,
        ],
        "rightmost_4x4": [
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            13.14,
            1.11,
            1.11,
            1.11,
            1.11,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
    },
    "back": {
        "leftmost_top_3x4": [
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
        "leftcenter_top_3x4": [
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
        "rightcenter_top_3x4": [
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
        "rightmost_top_4x4": [
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
        "leftmost_bottom_3x4": [
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
        "leftcenter_bottom_3x4": [
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
        "rightcenter_bottom_3x4": [
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
            -3.64,
        ],
        "rightmost_bottom-4x4": [-4, -4, -4, -4, -5, -5, -5, -5, -6, -6, -6, -6],
    },
}

# for independence to topeka, 2022
SPEED_LIMITS = {  # distance and speed in mph
    0: 20,  # distance: speed limit
    1: 30,
    1.6: 35,
    7.1: 30,
    7.6: 25,
    7.9: 30,
    8.7: 40,
    16.7: 35,
    18.5: 45,
    20.1: 40,
    24.2: 35,
    24.5: 45,
    34.5: 50,
    38.5: 30,
    38.7: 50,
    43.3: 40,
    44.3: 30,
    44.6: 35,
    45.6: 40,
    46: 45,
    55.7: 55,
    60.4: 45,
    61.6: 55,
    69.6: 45,
    70.2: 60,
    76.6: 55,
    86.5: 45,
    87: 55,
    93.9: 45,
    94.9: 40,
    96: 30,
    97: 40,
    98: 30,
    98.25: 25,
}

TORQUE_CURRENT_RPM_DATA = [
    (1, 1.61, 889),
    (2, 2.54, 892),
    (4, 4.36, 884),
    (6, 6.14, 877),
    (8, 7.88, 870),
    (10, 9.7, 863),
    (12, 11.42, 856),
    (14, 13.15, 850),
    (16, 14.84, 843),
    (18, 16.54, 837),
    (20, 18.25, 831),
    (22, 19.92, 825),
    (24, 21.6, 820),
    (26, 23.461, 811.54),
    (28, 25.197, 805.12),
    (30, 26.933, 798.7),
    (32, 28.669, 792.28),
    (34, 30.405, 785.86),
    (36, 32.141, 779.44),
    (38, 33.877, 773.02),
    (40, 35.613, 766.6),
    (42, 37.349, 760.18),
    (44, 39.085, 753.76),
    (46, 40.821, 747.34),
    (48, 42.557, 740.92),
    (50, 44.293, 734.5),
    (52, 46.029, 728.08),
    (54, 47.765, 721.66),
    (56, 49.501, 715.24),
    (58, 51.237, 708.82),
    (60, 52.973, 702.4),
    (62, 54.709, 695.98),
    (64, 56.445, 689.56),
    (65.567, 57.805156, 684.52993),
]