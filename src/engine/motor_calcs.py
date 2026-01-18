from __future__ import annotations
from typing import Dict, Iterable
import numpy as np
import matplotlib.pyplot as plt

from ..utils.constants import TORQUE_CURRENT_RPM_DATA, wheel_radius, battery_voltage
from ..engine.kinematics import Speed

class MotorModel:
    def __init__(self):
        self.ref_voltage = battery_voltage
        self._data = np.array(TORQUE_CURRENT_RPM_DATA)
        self._data = self._data[self._data[:, 0].argsort()]  # sort by rpm
        self.torque_ref = self._data[:, 0]
        self.current_ref = self._data[:, 1]
        self.rpm_ref = self._data[:, 2]
        self._initial_rpm_ref = self._data[:, 2].copy()  # Store initial RPM values
    
    def set_voltage(self, new_voltage: float):
        # Scale RPM values based on voltage change, torque and current stay the same
        self.rpm_ref = self._initial_rpm_ref * (new_voltage / self.ref_voltage)
        self.ref_voltage = new_voltage

    def _interp(self, x, x_ref, y_ref):
        return np.interp(x, x_ref, y_ref)
    
    def speed_from_torque(self, torque: float) -> Speed:
        rpm = self._interp(torque, self.torque_ref, self.rpm_ref)
        return Speed.create_from_rpm(rpm)
    
    def torque_from_speed(self, speed: Speed) -> float:
        rpm = speed.rpm()
        torque = self._interp(rpm, self.rpm_ref, self.torque_ref)
        return torque
    
    # def current_from_torque(self, torque: float) -> float:
    #     ref_current = self._interp(torque, self.torque_ref, self.current_ref)
    #     return ref_current * (self.voltage / self.ref_voltage)
    
    def efficiency_from_torque_speed(self, torque: float, speed: Speed) -> float:
        rpm = speed.rpm()
        power_out = (torque * rpm * 2 * np.pi) / 60  # Mechanical power in Watts
        current = self.current_from_torque(torque)
        power_in = self.voltage * current  # Electrical power in Watts
        if power_in == 0:
            return 0.0
        efficiency = power_out / power_in
        return efficiency
    
    def plot_model(self, unit: str):
        # self.set_voltage(voltage)
        
        # Generate range of currents
        i_min, i_max = self.current_ref.min(), self.current_ref.max()
        currents = np.linspace(i_min, i_max, 100)
        
        torques = []
        rpms = []
        
        for i in currents:
            # Interpolate torque from current
            t = self._interp(i, self.current_ref, self.torque_ref)
            torques.append(t)
            rpms.append(self.speed_from_torque(t).rpm())
            
        torques = np.array(torques)
        rpms = np.array(rpms)
        
        # Convert RPM to desired unit
        y2_vals = [Speed.create_from_rpm(rpm=r, radius=wheel_radius) for r in rpms]
        if unit.lower() == 'mps':
            y2 = [s.mps for s in y2_vals]
            y2_label = "Speed (m/s)"
        elif unit.lower() == 'kmph':
            y2 = [s.kmph for s in y2_vals]
            y2_label = "Speed (km/h)"
        elif unit.lower() == 'mph':
            y2 = [s.mph for s in y2_vals]
            y2_label = "Speed (mph)"
        else:
            y2 = rpms
            y2_label = "Speed (RPM)"

        fig, ax1 = plt.subplots(figsize=(10, 6))

        color = 'tab:blue'
        ax1.set_xlabel('Current (A)')
        ax1.set_ylabel('Torque (Nm)', color=color)
        ax1.plot(currents, torques, color=color, label='Torque')
        ax1.tick_params(axis='y', labelcolor=color)

        ax2 = ax1.twinx()  
        color = 'tab:red'
        ax2.set_ylabel(y2_label, color=color)  
        ax2.plot(currents, y2, color=color, linestyle='--', label='Speed')
        ax2.tick_params(axis='y', labelcolor=color)

        plt.title(f"Motor Characteristics at {self.ref_voltage}V")
        fig.tight_layout()  
        plt.show()
    


motor = MotorModel()
new_voltage = 85
motor.set_voltage(new_voltage)
if __name__ == "__main__":
    motor.plot_model(unit = "mph")