import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import QhullError


class Motor:
    """Estimate motor efficiency and power from CSV data for one motor/controller setup."""

    def __init__(self, csv_path: str | Path) -> None:
        """Load RPM, torque (N m), efficiency (fraction), and optional duty (fraction)."""
        columns = ["rpm", "torque", "efficiency"]
        with open(csv_path, newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not set(columns).issubset(reader.fieldnames or []):
                raise ValueError("CSV must contain rpm, torque, and efficiency columns.")
            self._has_duty = "duty" in reader.fieldnames
            if self._has_duty:
                columns.append("duty")
            try:
                data = np.array([[float(row[column]) for column in columns] for row in reader])
            except (TypeError, ValueError) as error:
                raise ValueError("Motor measurements must contain numeric values.") from error

        if len(data) < 3:
            raise ValueError("At least three non-collinear operating points are required.")
        if not np.isfinite(data).all() or (data <= 0).any() or (data[:, 2:] > 1).any():
            raise ValueError("Values must be finite, RPM and torque positive, and efficiency/duty in (0, 1].")
        self._points = data[:, :2]  # Shape (rows, 2): [[rpm, torque], ...]; data also has efficiency and optional duty columns.
        if len(np.unique(self._points, axis=0)) != len(data):
            raise ValueError("Duplicate RPM/torque points must be combined before loading.")
        try:
            # Pair each RPM/torque row with its efficiency and optional duty values.
            self._interpolator = LinearNDInterpolator(self._points, data[:, 2:], rescale=True)
        except QhullError as error:
            raise ValueError("Measurements must span a two-dimensional RPM/torque region.") from error

    def _interpolate(self, rpm: float, torque: float) -> np.ndarray:
        """Estimate values between the supplied points and reject unsupported inputs."""
        if not np.isfinite([rpm, torque]).all() or rpm <= 0 or torque <= 0:
            raise ValueError("RPM and torque must be finite and positive.")
        values = self._interpolator(rpm, torque)  # Call the SciPy object to estimate efficiency and optional duty from nearby data.
        if not np.isfinite(values).all():
            raise ValueError("Operating point is outside the measured motor map.")
        return values

    def get_efficiency(self, rpm: float, torque: float) -> float:
        """Return efficiency as a fraction at a supported operating point."""
        return float(self._interpolate(rpm, torque)[0])

    def get_electrical_power(self, rpm: float, torque: float) -> float:
        """Return input power in watts using P_in = torque * omega / efficiency."""
        efficiency = self.get_efficiency(rpm, torque)
        return float(torque * (rpm * 2 * np.pi / 60) / efficiency)

    def get_battery_current(self, rpm: float, torque: float, voltage: float) -> float:
        """Return DC input current in amperes using the voltage of the measured configuration."""
        if not np.isfinite(voltage) or voltage <= 0:
            raise ValueError("Battery voltage must be finite and positive.")
        return self.get_electrical_power(rpm, torque) / voltage

    def get_duty(self, rpm: float, torque: float) -> float:
        """Return interpolated duty as a fraction when the CSV includes duty measurements."""
        if not self._has_duty:
            raise ValueError("CSV does not include duty measurements.")
        return float(self._interpolate(rpm, torque)[1])

    def generate_heatmap(self) -> tuple[Figure, Axes]:
        """Return a Matplotlib (figure, axes), leaving unsupported regions blank."""
        minimum = self._points.min(axis=0)
        maximum = self._points.max(axis=0)
        rpm, torque = np.meshgrid(
            np.linspace(minimum[0], maximum[0], 150),
            np.linspace(minimum[1], maximum[1], 150),
        )
        # shortcut: estimates can cross gaps in the data; add gap checks before relying on values in those gaps.
        efficiency = np.ma.masked_invalid(self._interpolator(rpm, torque)[..., 0])
        figure, axes = plt.subplots(layout="constrained")
        heatmap = axes.pcolormesh(rpm, torque, efficiency * 100, shading="auto", cmap="jet", vmin=0, vmax=100)
        axes.set(xlabel="Speed (RPM)", ylabel="Torque (N m)", title="Motor efficiency", xlim=(0, maximum[0]), ylim=(0, maximum[1]))
        figure.colorbar(heatmap, ax=axes, label="Efficiency (%)")
        return figure, axes


if __name__ == "__main__":
    motor = Motor(Path(__file__).resolve().parents[1] / "data/datasets" / "hyundai_sonata_8_5kw_270v.csv")
    print(f"Efficiency at 800 RPM, 12 N m: {motor.get_efficiency(800, 12):.1%}")
    print(f"Electrical power at 800 RPM, 12 N m: {motor.get_electrical_power(800, 12):.1f} W")
    motor.generate_heatmap()
    plt.show()
