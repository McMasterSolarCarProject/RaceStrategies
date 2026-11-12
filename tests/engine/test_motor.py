import math
from pathlib import Path
import runpy

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

from src.engine.motor import Motor

matplotlib.use("Agg")


@pytest.fixture
def motor(tmp_path):
    csv_path = tmp_path / "motor.csv"
    csv_path.write_text("rpm,torque,efficiency\n1000,1,0.8\n3000,1,0.9\n1000,3,0.9\n", encoding="utf-8")
    return Motor(csv_path)


def test_motor_interpolation_and_electrical_power(motor):
    assert math.isclose(motor.get_efficiency(1000, 1), 0.8)
    assert math.isclose(motor.get_efficiency(1500, 1.5), 0.85)
    assert math.isclose(motor.get_efficiency(2000, 2), 0.9)
    assert math.isclose(motor.get_electrical_power(1500, 1.5), 1.5 * 50 * math.pi / 0.85)


@pytest.mark.parametrize("rpm,torque", [(2500, 2), (500, 1), (1000, 4), (0, 1), (1000, 0), (-1, 1), (float("nan"), 1), (1000, float("inf"))])
def test_motor_rejects_unsupported_operating_points(motor, rpm, torque):
    with pytest.raises(ValueError):
        motor.get_efficiency(rpm, torque)
    with pytest.raises(ValueError):
        motor.get_electrical_power(rpm, torque)


@pytest.mark.parametrize("contents", [
    "",
    "rpm,torque\n1000,1\n",
    "rpm,torque,efficiency\n",
    "rpm,torque,efficiency\n1000,1,0.8\n",
    "rpm,torque,efficiency\n1000,1,0.8\n2000,2,0.8\n3000,3,0.8\n",
    "rpm,torque,efficiency\n1000,1,0.8\n3000,1,0.9\n1000,3,0.9\n1000,1,0.7\n",
    *[f"rpm,torque,efficiency\n1000,1,{value}\n3000,1,0.9\n1000,3,0.9\n" for value in ["0", "-0.1", "1.1", "80", "nan", "inf", "", "invalid"]],
    "rpm,torque,efficiency\n0,1,0.8\n3000,1,0.9\n1000,3,0.9\n",
    "rpm,torque,efficiency\n1000,-1,0.8\n3000,1,0.9\n1000,3,0.9\n",
])
def test_motor_rejects_invalid_csv(tmp_path, contents):
    csv_path = tmp_path / "motor.csv"
    csv_path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        Motor(csv_path)


def test_motor_heatmap_masks_unsupported_regions(motor):
    figure, axes = motor.generate_heatmap()
    try:
        figure.canvas.draw()
        assert axes.get_xlabel() == "Speed (RPM)"
        assert axes.get_ylabel() == "Torque (N m)"
        assert len(figure.axes) == 2
        assert np.ma.getmaskarray(axes.collections[0].get_array()).any()
    finally:
        plt.close(figure)


def test_motor_demo_uses_sample_data_and_displays_heatmap(monkeypatch, capsys):
    shown = []
    monkeypatch.setattr(plt, "show", lambda: shown.append(True))
    try:
        result = runpy.run_path(str(Path(__file__).resolve().parents[2] / "src/engine/motor.py"), run_name="__main__")
        assert shown == [True]
        assert "Electrical power" in capsys.readouterr().out
        assert math.isclose(result["motor"].get_efficiency(4119, 7.3), 0.92)
    finally:
        plt.close("all")
