import math

from src.config import DEFAULT_PROFILE
from src.engine.kinematics import Speed
from src.engine.motor_calcs import MotorModel
from src.engine.motor_data import TORQUE_CURRENT_RPM_DATA


def test_motor_model_sorts_reference_data_by_torque():
    model = MotorModel()

    assert list(model.torque_ref) == sorted(row[0] for row in TORQUE_CURRENT_RPM_DATA)
    assert model.current_ref[0] == TORQUE_CURRENT_RPM_DATA[0][1]


def test_speed_from_torque_uses_interpolated_reference_rpm():
    model = MotorModel()
    speed = model.speed_from_torque(1.0)
    expected = Speed.create_from_rpm(889, radius=DEFAULT_PROFILE.motor.wheel_radius)

    assert math.isclose(speed.mps, expected.mps)


def test_torque_from_speed_is_inverse_for_reference_point():
    model = MotorModel()
    speed = model.speed_from_torque(20.0)

    assert math.isclose(model.torque_from_speed(speed), 20.0)


def test_set_voltage_scales_rpm_reference_values():
    model = MotorModel()
    initial_rpm = model.rpm_ref.copy()

    model.set_voltage(model.ref_voltage / 2)

    assert all(model.rpm_ref == initial_rpm / 2)
