from __future__ import annotations
from typing import Dict, Iterable
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline, Pipeline
from math import pi
import matplotlib.pyplot as plt

from ..utils.constants import TORQUE_CURRENT_RPM_DATA, wheel_radius, battery_voltage
# from ..src.utils.graph import plot_dual_axis_fit
from ..engine.kinematics import Speed
        

import numpy as np
from sklearn.linear_model import LinearRegression
import copy

class MotorModel:
    def __init__(self):
        self.ref_voltage = battery_voltage
        self.voltage = battery_voltage
        self.data = {}
        self.fits = {}
        self.load_data(TORQUE_CURRENT_RPM_DATA)
        self.fit_at_reference_voltage()
        self.original_fits = copy.deepcopy(self.fits)

    def load_data(self, data):
        A = np.array(data, float)
        self.data["torque"]  = A[:,0].reshape(-1,1)
        self.data["current"] = A[:,1].reshape(-1,1)
        self.data["rpm"]     = A[:,2].reshape(-1,1)

    def rpm_to_kmph(self, rpm_vals):
        """Convert RPM to km/h using wheel radius"""
        # Convert RPM to m/s: rpm * (2*pi*r) / 60
        # Then convert m/s to km/h: * 3.6
        wheel_circumference = 2 * pi * wheel_radius  # meters
        speed_ms = rpm_vals * wheel_circumference / 60
        speed_kmph = speed_ms * 3.6
        return speed_kmph

    def fit_at_reference_voltage(self):
        T = self.data["torque"]
        I = self.data["current"]
        R = self.data["rpm"].ravel()

        # rpm fits at reference V
        self.fits["rpm|torque"]  = LinearRegression().fit(T, R)
        self.fits["rpm|current"] = LinearRegression().fit(I, R)  # <-- add this

        # voltage-independent fits
        self.fits["current|torque"] = LinearRegression().fit(T, I.ravel())
        self.fits["torque|current"] = LinearRegression().fit(I, T.ravel())


    def set_voltage(self, new_voltage: float):
        """Refits the rpm relationships to a new voltage by adjusting
        only the intercept (slope is voltage-independent).
        """
        V_new = float(new_voltage)
        scale = V_new / self.ref_voltage
        self.voltage = V_new

        # update BOTH rpm fits in-place
        self.fits = copy.deepcopy(self.original_fits)
        for fit_key in ["rpm|torque", "rpm|current"]:
            if fit_key in self.fits:
                mdl = self.fits[fit_key]
                coef = mdl.coef_.copy()
                intercept_ref = mdl.intercept_
                new_intercept = intercept_ref * scale
                mdl.intercept_ = new_intercept
                mdl.coef_ = coef
    
    def plot_dual_axis_fit(
        self,
        fit_y1: str,
        fit_y2: str,
        x_col: str,
        y1_label: str,
        y2_label: str,
        title: str = "Dual Axis Fit Plot",
        speed_unit: str = "rpm"
    ):
        """
        Plots two relationships on the same X-axis with two Y-axes using stored fits.

        Parameters:
        - fit_y1: label of first stored fit, e.g. "torque|current"
        - fit_y2: label of second stored fit, e.g. "rpm|current"
        - x_col: column label to use as X data, e.g. "current"
        - y1_label: label for left Y-axis
        - y2_label: label for right Y-axis
        - title: plot title
        """

        # Extract data - ensure proper reshaping
        x_data = self.data[x_col]
        x = x_data.ravel()
        
        # Get predictions
        y1 = self.fits[fit_y1].predict(x_data).ravel()
        y2_raw = self.fits[fit_y2].predict(x_data).ravel()

        # Convert y2 to desired speed unit if it's an RPM fit
        if fit_y2.startswith("rpm|") and speed_unit != "rpm":
            y2 = self.convert_rpm_to_speed_units(y2_raw, speed_unit)
        else:
            y2 = y2_raw

        # Smooth x-range for curves
        x_range = np.linspace(x.min(), x.max(), 300).reshape(-1, 1)
        y1_fit = self.fits[fit_y1].predict(x_range)
        y2_fit_raw = self.fits[fit_y2].predict(x_range)

        # Convert y2 fit to desired speed unit if it's an RPM fit
        if fit_y2.startswith("rpm|") and speed_unit != "rpm":
            y2_fit = self.convert_rpm_to_speed_units(y2_fit_raw, speed_unit)
        else:
            y2_fit = y2_fit_raw

        # Start plotting
        fig, ax1 = plt.subplots(figsize=(10, 5))

        # Left Y-axis (y1)
        scatter1 = ax1.scatter(x, y1, color='blue', label=f'{y1_label} Data', marker='o', alpha=0.7)
        line1 = ax1.plot(x_range, y1_fit, color='blue', label=f"{y1_label} Fit", linewidth=2)
        ax1.set_xlabel(x_col)
        ax1.set_ylabel(y1_label, color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')

        # Right Y-axis (y2)
        ax2 = ax1.twinx()
        scatter2 = ax2.scatter(x, y2, color='red', label=f'{y2_label} Data', marker='s', alpha=0.7)
        line2 = ax2.plot(x_range, y2_fit, color='red', linestyle='--', label=f"{y2_label} Fit", linewidth=2)
        ax2.set_ylabel(y2_label, color='red')
        ax2.tick_params(axis='y', labelcolor='red')

        # Merge legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper center")

        ax1.set_title(title)
        plt.tight_layout()
        plt.show()
    
    def convert_rpm_to_speed_units(self, rpm_vals, unit: str):
        """Convert RPM values to specified speed unit using Speed class"""
        speed_objs = [Speed.create_from_rpm(rpm=r, radius=wheel_radius) for r in rpm_vals]
        
        if unit.lower() == "rpm":
            return rpm_vals
        elif unit.lower() == "kmph":
            return [s.kmph for s in speed_objs]
        elif unit.lower() == "mph":
            return [s.mph for s in speed_objs]
        elif unit.lower() == "mps":
            return [s.mps for s in speed_objs]
        else:
            raise ValueError(f"Unknown speed unit: {unit}. Use 'rpm', 'kmph', 'mph', or 'mps'")

    def torque_from_speed(self, rpm: float) -> float:
        rpm_torque_fit = self.fits["rpm|torque"]  # rpm = a*T + b
        a = float(rpm_torque_fit.coef_)
        b = float(rpm_torque_fit.intercept_)
        return (rpm - b) / a

    def speed_from_torque(self, torque: float) -> float:
        rpm_torque_fit = self.fits["rpm|torque"]  # rpm = a*T + b
        a = float(rpm_torque_fit.coef_)
        b = float(rpm_torque_fit.intercept_)
        return a*torque + b

    def plot_model(self, voltage: float, unit:str):
        self.set_voltage(voltage)

         # Unit labels mapping
        unit_labels = {
            "rpm": "Speed (RPM)",
            "kmph": "Speed (km/h)",
            "mph": "Speed (mph)", 
            "mps": "Speed (m/s)"
        }
        
        y2_label = unit_labels.get(unit, "Speed (RPM)")

        self.plot_dual_axis_fit(
            fit_y1="torque|current",
            fit_y2= "rpm|current",
            x_col="current",
            y1_label="Torque (Nm)",
            y2_label=y2_label,
            title = f"Torque & Speed vs Current at {voltage}V",
            speed_unit=unit
        )


motor = MotorModel()
motor.set_voltage(85)
if __name__ == "__main__":
    motor.plot_model(100.8, unit = "mph")
