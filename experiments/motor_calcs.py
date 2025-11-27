from __future__ import annotations
from typing import Dict, Iterable
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline, Pipeline
from math import pi
import matplotlib.pyplot as plt

from src.utils.constants import TORQUE_CURRENT_RPM_DATA, wheel_radius, battery_voltage
# from ..src.utils.graph import plot_dual_axis_fit
from src.engine.kinematics import Speed
        

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

    def load_data(self, data):
        A = np.array(data, float)
        self.data["torque"]  = A[:,0].reshape(-1,1)
        self.data["current"] = A[:,1].reshape(-1,1)
        self.data["rpm"]     = A[:,2].reshape(-1,1)

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
        """
        'Refits' the rpm|torque relationship to a new voltage by adjusting
        only the intercept (slope is voltage-independent).
        """
        V_new = float(new_voltage)
        scale = V_new / self.ref_voltage
        self.voltage = V_new

        # update the rpm|torque fit in-place
        mdl = self.fits["rpm|torque"]

        coef = mdl.coef_.copy()
        intercept_ref = mdl.intercept_

        new_intercept = intercept_ref * scale

        # overwrite coefficients
        mdl.intercept_ = new_intercept
        mdl.coef_ = coef

    # --------- Prediction helpers ----------
    def rpm_at_torque(self, torque_vals):
        mdl = self.fits["rpm|torque"]
        T = np.array(torque_vals, float).reshape(-1,1)
        return mdl.predict(T).ravel()

    def current_at_torque(self, torque_vals):
        return self.fits["current|torque"].predict(np.array(torque_vals,float).reshape(-1,1)).ravel()

    def torque_at_current(self, current_vals):
        return self.fits["torque|current"].predict(np.array(current_vals,float).reshape(-1,1)).ravel()
    
    def speed_objs_at_torque(self, torque_vals):
        kmph = self.speed_at_torque(torque_vals)
        return [Speed(kmph=v) for v in np.atleast_1d(kmph)]

    def speed_objs_at_current(self, current_vals):
        kmph = self.speed_at_current(current_vals)
        return [Speed(kmph=v) for v in np.atleast_1d(kmph)]
    
    def plot_dual_axis_fit(
        self,
        fit_y1: str,
        fit_y2: str,
        x_col: str,
        y1_label: str,
        y2_label: str,
        title: str = "Dual Axis Fit Plot"
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

        # Extract data
        x = self.data[x_col].ravel()
        y1 = self.fits[fit_y1].predict(self.data[x_col]).ravel()
        y2 = self.fits[fit_y2].predict(self.data[x_col]).ravel()

        # Smooth x-range for curves
        x_range = np.linspace(x.min(), x.max(), 300).reshape(-1, 1)
        y1_fit = self.fits[fit_y1].predict(x_range)
        y2_fit = self.fits[fit_y2].predict(x_range)

        # Start plotting
        fig, ax1 = plt.subplots(figsize=(10, 5))

        # Left Y-axis (y1)
        ax1.scatter(x, y1, label=y1_label, marker='o')
        ax1.plot(x_range, y1_fit, label=f"{y1_label} Fit")
        ax1.set_xlabel(x_col)
        ax1.set_ylabel(y1_label)
        ax1.tick_params(axis='y')

        # Right Y-axis (y2)
        ax2 = ax1.twinx()
        ax2.scatter(x, y2, label=y2_label, marker='o', alpha=0.6)
        ax2.plot(x_range, y2_fit, linestyle='--', label=f"{y2_label} Fit")
        ax2.set_ylabel(y2_label)
        ax2.tick_params(axis='y')

        # Merge legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper center")

        ax1.set_title(title)
        plt.tight_layout()
        plt.show()


motor = MotorModel()
motor.fit_at_reference_voltage()
motor.plot_dual_axis_fit(
    fit_y1="torque|current",
    fit_y2="kmph|current",
    x_col="current",
    y1_label="Torque (Nm)",
    y2_label="kmph",
    title="Torque & kmph vs Current"
)
