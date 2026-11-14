from pathlib import Path
import runpy

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

from src.engine.motor import Motor

matplotlib.use("Agg")
DATA_DIR = Path(__file__).resolve().parents[2] / "src/data/datasets"


@pytest.fixture
def motor(tmp_path: Path) -> Motor:
    csv_path = tmp_path / "motor.csv"
    csv_path.write_text("rpm,torque,efficiency,duty\n1000,1,0.8,0.4\n3000,1,0.9,0.8\n1000,3,0.9,0.6\n", encoding="utf-8")
    return Motor(csv_path)


class TestMotor:
    """Check interpolation, electrical demand, invalid inputs, and real datasets."""

    def test_interpolation_and_power(self, motor: Motor) -> None:
        assert motor.get_efficiency(1000, 1) == pytest.approx(0.8)
        assert motor.get_efficiency(1500, 1.5) == pytest.approx(0.85)
        assert motor.get_efficiency(2000, 2) == pytest.approx(0.9)
        assert motor.get_electrical_power(1500, 1.5) == pytest.approx(1.5 * 50 * np.pi / 0.85)
        assert motor.get_battery_current(1500, 1.5, 96) == pytest.approx(1.5 * 50 * np.pi / 0.85 / 96)
        assert motor.get_duty(1500, 1.5) == pytest.approx(0.55)

    @pytest.mark.parametrize("rpm,torque", [(2500, 2), (500, 1), (1000, 4), (0, 1), (1000, 0), (-1, 1), (1000, -1), (np.nan, 1), (1000, np.inf)])
    def test_unsupported_points(self, motor: Motor, rpm: float, torque: float) -> None:
        for method in (motor.get_efficiency, motor.get_electrical_power, motor.get_duty):
            with pytest.raises(ValueError):
                method(rpm, torque)
        with pytest.raises(ValueError):
            motor.get_battery_current(rpm, torque, 96)

    @pytest.mark.parametrize("voltage", [0, -96, np.nan, np.inf])
    def test_invalid_voltage(self, motor: Motor, voltage: float) -> None:
        with pytest.raises(ValueError, match="voltage"):
            motor.get_battery_current(1500, 1.5, voltage)

    @pytest.mark.parametrize("rows", [
        "", "1000,1,0.8\n", "1000,1,0.8\n2000,2,0.8\n3000,3,0.8\n",
        "1000,1,0.8\n3000,1,0.9\n1000,3,0.9\n1000,1,0.7\n",
        *[f"1000,1,{value}\n3000,1,0.9\n1000,3,0.9\n" for value in ["0", "-0.1", "1.1", "80", "nan", "inf", "", "invalid"]],
        "0,1,0.8\n3000,1,0.9\n1000,3,0.9\n", "1000,-1,0.8\n3000,1,0.9\n1000,3,0.9\n",
    ])
    def test_invalid_measurements(self, tmp_path: Path, rows: str) -> None:
        csv_path = tmp_path / "motor.csv"
        csv_path.write_text("rpm,torque,efficiency\n" + rows, encoding="utf-8")
        with pytest.raises(ValueError):
            Motor(csv_path)

    def test_missing_columns(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "motor.csv"
        csv_path.write_text("rpm,torque\n1000,1\n", encoding="utf-8")
        with pytest.raises(ValueError, match="columns"):
            Motor(csv_path)

    @pytest.mark.parametrize("duty", ["", "invalid", "nan", "inf", "0", "-0.1", "1.1", "50"])
    def test_invalid_duty(self, tmp_path: Path, duty: str) -> None:
        csv_path = tmp_path / "motor.csv"
        csv_path.write_text(f"rpm,torque,efficiency,duty\n1000,1,0.8,{duty}\n3000,1,0.9,0.8\n1000,3,0.9,0.6\n", encoding="utf-8")
        with pytest.raises(ValueError):
            Motor(csv_path)

    def test_current_motor(self) -> None:
        motor = Motor(DATA_DIR / "mitsuba_m2096d3_c1_96v.csv")
        assert motor.get_efficiency(801, 10.7) == pytest.approx(0.933)
        assert motor.get_efficiency(797, 11.9) == pytest.approx(0.938)
        assert motor.get_battery_current(801, 10.7, 96) == pytest.approx(10, rel=0.005)
        with pytest.raises(ValueError, match="duty"):
            motor.get_duty(801, 10.7)
        with pytest.raises(ValueError):
            motor.get_efficiency(500, 10)

    @pytest.mark.parametrize("filename", sorted(path.name for path in DATA_DIR.glob("*.csv")))
    def test_each_dataset_reproduces_measurements(self, filename: str) -> None:
        path = DATA_DIR / filename
        motor = Motor(path)
        data = np.genfromtxt(path, delimiter=",", names=True)
        for row in data:
            assert motor.get_efficiency(row["rpm"], row["torque"]) == pytest.approx(row["efficiency"])

    @pytest.mark.parametrize("wiring", ["series", "parallel"])
    def test_dyno_power(self, wiring: str) -> None:
        path = DATA_DIR / f"mitsuba_m2096d3_dyno_{wiring}.csv"
        motor = Motor(path)
        data = np.genfromtxt(path, delimiter=",", names=True)
        for row in data:
            # Source torque, RPM, and power are rounded independently.
            assert motor.get_electrical_power(row["rpm"], row["torque"]) == pytest.approx(row["input_power"], rel=0.01)

    def test_heatmap(self, motor: Motor) -> None:
        figure, axes = motor.generate_heatmap()
        try:
            figure.canvas.draw()
            assert axes.get_xlabel() == "Speed (RPM)"
            assert axes.get_ylabel() == "Torque (N m)"
            assert axes.get_xlim() == pytest.approx((0, 3000))
            assert axes.get_ylim() == pytest.approx((0, 3))
            assert len(figure.axes) == 2
            assert np.ma.getmaskarray(axes.collections[0].get_array()).any()
            assert axes.collections[0].cmap.name == "jet"
        finally:
            plt.close(figure)

    def test_demo(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        shown = []
        monkeypatch.setattr(plt, "show", lambda: shown.append(True))
        try:
            result = runpy.run_path(str(DATA_DIR.parents[1] / "engine/motor.py"), run_name="__main__")
            assert shown == [True]
            assert "Electrical power" in capsys.readouterr().out
            assert 0 < result["motor"].get_efficiency(800, 12) <= 1
        finally:
            plt.close("all")
