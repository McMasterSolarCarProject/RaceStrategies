import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import QhullError


class Motor:
    """Interpolate CSV columns rpm, torque (N m), and efficiency (fraction).

    Supports positive RPM/torque inside the measured convex hull, without
    extrapolation. Use measurements from consistent operating conditions;
    data coverage does not establish rated or thermal limits.
    """

    def __init__(self, csv_path: str | Path):
        columns = ("rpm", "torque", "efficiency")
        with open(csv_path, newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not set(columns).issubset(reader.fieldnames or []):
                raise ValueError("CSV must contain rpm, torque, and efficiency columns.")
            try:
                data = np.array([[float(row[column]) for column in columns] for row in reader])
            except (TypeError, ValueError) as error:
                raise ValueError("RPM, torque, and efficiency must contain numeric values.") from error

        if len(data) < 3:
            raise ValueError("At least three non-collinear operating points are required.")
        if not np.isfinite(data).all() or (data <= 0).any() or (data[:, 2] > 1).any():
            raise ValueError("Values must be finite, RPM and torque positive, and efficiency in (0, 1].")
        self._points = data[:, :2]
        if len(np.unique(self._points, axis=0)) != len(data):
            raise ValueError("Duplicate RPM/torque points must be combined before loading.")
        try:
            self._interpolator = LinearNDInterpolator(self._points, data[:, 2], rescale=True)
        except QhullError as error:
            raise ValueError("Measurements must span a two-dimensional RPM/torque region.") from error

    def get_efficiency(self, rpm: float, torque: float) -> float:
        """Return efficiency as a fraction; reject unsupported operating points."""
        if not np.isfinite([rpm, torque]).all() or rpm <= 0 or torque <= 0:
            raise ValueError("RPM and torque must be finite and positive.")
        efficiency = self._interpolator(rpm, torque).item()
        if not np.isfinite(efficiency) or not 0 < efficiency <= 1:
            raise ValueError("Operating point is outside the measured motor map.")
        return efficiency

    def get_electrical_power(self, rpm: float, torque: float) -> float:
        """Return input power in watts using P_in = torque * omega / efficiency."""
        efficiency = self.get_efficiency(rpm, torque)
        return float(torque * (rpm * 2 * np.pi / 60) / efficiency)

    def generate_heatmap(self):
        """Return a Matplotlib (figure, axes), leaving unsupported regions blank."""
        minimum = self._points.min(axis=0)
        maximum = self._points.max(axis=0)
        rpm, torque = np.meshgrid(
            np.linspace(minimum[0], maximum[0], 150),
            np.linspace(minimum[1], maximum[1], 150),
        )
        # shortcut: the convex hull bridges unmeasured gaps; use an explicit envelope if the dataset has holes.
        efficiency = np.ma.masked_invalid(self._interpolator(rpm, torque))
        figure, axes = plt.subplots(layout="constrained")
        heatmap = axes.pcolormesh(rpm, torque, efficiency * 100, shading="auto", vmin=0, vmax=100)
        axes.set(xlabel="Speed (RPM)", ylabel="Torque (N m)", title="Motor efficiency")
        figure.colorbar(heatmap, ax=axes, label="Efficiency (%)")
        return figure, axes


if __name__ == "__main__":
    motor = Motor(Path(__file__).resolve().parents[1] / "data" / "golden_motor_hpm3000_48v.csv")
    print(f"Efficiency at 4000 RPM, 8 N m: {motor.get_efficiency(4000, 8):.1%}")
    print(f"Electrical power at 3500 RPM, 11.5 N m: {motor.get_electrical_power(3500, 11.5):.1f} W")
    motor.generate_heatmap()
    plt.show()
