import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline, Pipeline
from math import pi
import matplotlib.pyplot as plt

from ..utils.constants import TORQUE_CURRENT_RPM_DATA, wheel_radius
from ..utils.graph import plot_dual_axis_fit
from .kinematics import Speed


class Model:
    def __init__(self):
        self._data = {}
        self._fits = {}
        self._voltage = 101.64
        self._ra = 0.4

    def insert_data(self, data_array: list, *labels: str):
        """
        Takes a list of data and corresponding labels, where each label corresponds to a column in the dataset.
        If the number of labels match the number of columns in the data, it saves the data to a _data dict.
        The _data dict's keys are the labels, which directly correspond to the columns in the data.
        """
        data_array = np.array(data_array)
        if data_array.ndim == 1:
            data_array = data_array.reshape(-1, 1)  # if a 1D array is passed, convert it to a 2D column vector
        if data_array.shape[1] != len(labels):
            raise ValueError(f"Length of data_array must match number of labels. Array length: {data_array.shape[1]}. Labels length: {len(labels)}.")
        for i in range(len(labels)):
            self._data[labels[i]] = data_array[:, i]

    def create_fit(self, x: np.ndarray, y: np.ndarray, label: str, degree: int = 1):
        """
        Creates a linear or polynomial fit for the given x and y data, and stores it in the _fits
        dict with the given label.
        """
        self._fits[label] = make_pipeline(PolynomialFeatures(degree), LinearRegression())
        self._fits[label].fit(x.reshape(-1, 1), y)

    def demo_model(self):
        self.create_fit(self.data["torque"], self.data["current"], "torque_to_current")
        self.create_fit(self.data["torque"], self.data["kmph"], "torque_to_velocity")
        self.create_fit(self.data["current"], self.data["torque"], "current_to_torque")
        self.create_fit(self.data["current"], self.data["kmph"], "current_to_velocity")
        self.create_fit(self.data["kmph"], self.data["torque"], "velocity_to_torque")

        new_velocity = self.fits["current_to_velocity"].predict(self.data["current"].reshape(-1, 1))

        plot_dual_axis_fit(
            self.data["current"],  # x-axis, actual current
            self.data["torque"],  # left y-axis, actual torque
            new_velocity,  # right y2-axis, predicted velocity         ! Note: Why not use actual velocity for this?
            self.fits["current_to_torque"],  # fitted models to plot regression lines
            self.fits["current_to_velocity"],  # fitted models to plot regression lines
            "current",
            "torque",
            "kmph",
            "current vs torque and rpm",
        )

    def solve_motor_constant(self):
        """
        Solves for the motor constant ke using the given formula. It is calculated for each data point, and
        the average is returned. Current and rpm data arrays are required to be present in the _data dict.
        """
        ke_array = (self._voltage - self.data["current"] * self._ra) / self.data["rpm"]
        self._ke = np.mean(ke_array)
        return self._ke

    @property
    def data(self) -> dict[str, np.ndarray]:
        return self._data

    @property
    def fits(self) -> dict[str, Pipeline]:
        return self._fits

    @property
    def voltage(self) -> float:
        return self._voltage

    @property
    def ke(self) -> float:
        return self._ke

    @property
    def ra(self) -> float:
        return self._ra


class Motor:
    def __init__(self, torque: float = None, velocity: Speed = None, current: float = None):
        provided = [i is not None for i in (torque, velocity, current)]
        if sum(provided) != 1:
            raise ValueError("Exactly one of torque, velocity, or current must be provided.")

        data_array = np.array(TORQUE_CURRENT_RPM_DATA)
        kmph_data = data_array[:, 2] * 2 * pi * wheel_radius * 60 / 1000  # convert rpm to kmph
        data_array = np.column_stack((data_array, kmph_data))

        self._model = Model()
        self._model.insert_data(data_array, "torque", "current", "rpm", "kmph")
        self._model.solve_motor_constant()
        self._model.demo_model()  # this is what creates the graph

        if torque is not None:
            self.update_torque(torque)
        elif velocity is not None:
            self.update_velocity(velocity)
        elif current is not None:
            self.update_current(current)

        self._ra = (self._model.voltage - (self._torque * self._velocity.rps())) / self._current
        self._ke = self._model.voltage - self._current * self._ra / (self._velocity.rps())

    def update_torque(self, new_torque: float):
        self._torque = new_torque
        self._current = self._model.fits["torque_to_current"].predict([[self._torque]])[0]
        self._velocity = Speed(kmph=self._model.fits["torque_to_velocity"].predict([[self._torque]]))

    def update_velocity(self, new_velocity: Speed):
        self._velocity = new_velocity
        self._torque = self._model.fits["velocity_to_torque"].predict([[self._velocity.kmph]])[0]
        self._current = self._model.fits["torque_to_current"].predict([[self._torque]])[0]
        
    def update_current(self, new_current: float):
        self._current = new_current
        self._torque = self._model.fits["current_to_torque"].predict([[self._current]])[0]
        self._velocity = Speed(kmph=self._model.fits["current_to_velocity"].predict([[self._current]]))

    def efficiency_rating(self):
        return self.velocity.mps * self.torque / (self._model.voltage * self.current)

    @property
    def torque(self) -> float:
        return self._torque

    @property
    def velocity(self) -> Speed:
        return self._velocity

    @property
    def current(self) -> float:
        return self._current

    @property
    def voltage(self) -> float:
        return self._model.voltage

# put this into test
if __name__ == "__main__":
    m = Motor(velocity=Speed(mph=35))
    print(m.velocity.mps, m.current, m.torque, m.efficiency_rating())