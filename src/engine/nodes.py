from __future__ import annotations
from .kinematics import Velocity, Displacement, Speed, Coordinate, ZERO_VEC, NULL_COORDINATE
from ..config import CarProfile, DEFAULT_PROFILE
from .motor_calcs import motor

# Speed takes mps as the default parameter, so all calculations are in mps
class Segment(Displacement):  # Meters
    def __init__(self, p1: Coordinate, p2: Coordinate, id: int = 0, speed_limit: Speed = Speed(0), ghi: float = 0, wind: Velocity = ZERO_VEC, tdist: float = 0):
        self.id = id
        super().__init__(p1, p2)
        self.displacement = Displacement(p1, p2)
        self.ghi = ghi
        self.wind = wind
        self.speed_limit = speed_limit
        self.tdist = tdist

    def __str__(self):
        return f"Segment {self.id} | Total Distance: {self.tdist} | Speed limit: {self.speed_limit.kmph} km/h"

NULL_SEGMENT = Segment(NULL_COORDINATE, NULL_COORDINATE)

class StateNode:
    CRUISE_FORCE_TOLERANCE_N = 1e-6

    NUMERICAL_METRICS = {
        "torque": "Torque (Nm)",
        "Fb": "Braking Force (N)",
        "speed_mps": "Velocity (m/s)",
        "speed_kmph": "Velocity (km/h)",
        "speed_mph": "Velocity (mph)",
        "Fm": "Motor Force (N)",
        "acc": "Acceleration (m/s²)",
    }

    def __init__(self, segment: Segment = NULL_SEGMENT, profile: CarProfile = DEFAULT_PROFILE):
        self.segment = segment
        self.torque = 0
        self.Fb = 0
        self.speed_mps = 0.0
        self.profile = profile
        
        self.Fm = 0 # motor force
        self.Fd = 0 # drag force
        self.Frr = 0 # rolling resistance force
        self.Fg = 0 # gravitational force (x component)
        self.Ft = 0 # total force
        self.acc = 0 # acceleration

        self.P_out = 0 # Power output from the motor
        self.P_in = 0 # Power input to the motor (before efficiency losses)
        self.P_sol = 0 # Power generated from solar panels
        self.P_elec = 0 # Power draw from firmware
        # !! replace with electrical firmware constant

        # Various Scoring Metrics
        self.energy_per_meter = 0

    def Fm_calc(self):
        # Assume torque is calculated from the motor model
        self.Fm = self.torque / self.profile.motor.wheel_radius * self.profile.motor.num_motors

    def Fd_calc(self, initial_speed_mps: float):
        velocity = self.segment.displacement.unit_vector() * initial_speed_mps

        # The overflow should never be happening
        try:
            (velocity - self.segment.wind).mag ** 2
        except OverflowError:
            print("ERROR: The value of velocity in fd_calc is too high! Try a smaller timestep")
            print(f"velocity: {velocity.mag} mps clamped to velocity: 200 mps")
            velocity = self.segment.displacement.unit_vector() * 200
        finally:
            self.Fd = 0.5 * self.profile.physics.air_density * self.profile.vehicle.coef_drag * self.profile.vehicle.cross_section * ((velocity - self.segment.wind).mag ** 2)

    def Frr_calc(self):
        self.Frr = self.profile.vehicle.coef_rr * self.profile.vehicle.car_mass * self.profile.physics.accel_g * self.segment.gradient.cos()

    def Fg_calc(self):
        self.Fg = self.profile.vehicle.car_mass * self.profile.physics.accel_g * self.segment.gradient.sin()

    def Ft_calc(self):
        self.Ft = self.Fm - self.Fd - self.Frr - self.Fg - self.Fb
        self.acc = self.Ft / self.profile.vehicle.car_mass

    def Power_calc(self):
        self.P_out = self.torque * (self.speed_mps / self.profile.motor.wheel_radius) * self.profile.motor.num_motors
        # self.P_in = self.P_out*motor.efficiency_from_torque_speed(self.torque, motor_speed)
        self.P_in = self.P_out / 0.9 # assume 90% efficiency

    def solar_energy_cal(self):
        self.P_sol = 0

    def solve_cruise_state(self, speed_mps: float | None = None):
        if speed_mps is not None:
            self.speed_mps = float(speed_mps)

        self.Fd_calc(self.speed_mps)
        self.Fg_calc()
        self.Frr_calc()
        self.solar_energy_cal()
        self.Fm = self.Fg + self.Frr + self.Fd
        self.torque = self.Fm * self.profile.motor.wheel_radius / self.profile.motor.num_motors
        motor_speed = motor.speed_from_torque(self.torque)
        if motor_speed.mps < self.speed_mps:
            return False
        self.Ft_calc()
        if abs(self.Ft) > self.CRUISE_FORCE_TOLERANCE_N:
            print(f"Warning: Cruise state has non-zero total force: {self.Ft} N. This may indicate an issue with the calculations.")
            return False
        self.Ft = 0
        self.Power_calc()
        return True

    @classmethod
    def get_numerical_metrics(cls) -> list[str]:
        """
        Contains a list of all the numerical attributes that can be plotted on a graph.
        This is to allow the gui app to dynamically display these metrics.
        If new attributes are added to StateNode, then NUMERICAL_METRICS must be updated.
        """
        return list(cls.NUMERICAL_METRICS.keys())


class DynamicNode(StateNode):
    NUMERICAL_METRICS = {
        **StateNode.NUMERICAL_METRICS,
        "time": "Time (s)",
        "dist": "Distance (m)",
        "soc": "State of Charge (%)",
        "target_speed_mps": "Target Speed (m/s)",
        "target_speed_kmph": "Target Speed (km/h)",
        "target_speed_mph": "Target Speed (mph)",
        "target_torque": "Target Torque (Nm)",
        "segment.speed_limit.mps": "Speed Limit (m/s)",
        "segment.speed_limit.kmph": "Speed Limit (km/h)",
        "segment.speed_limit.mph": "Speed Limit (mph)",
        "segment.tdist": "Segment Total Distance (m)",
        "segment.dist": "Segment Distance (m)",
        "segment.elevation": "Segment Elevation Change (m)",
        "segment.azimuth": "Segment Azimuth (deg)",
        "segment.ghi": "Segment GHI",
        "segment.gradient.sin": "Road Grade",
        "segment.gradient.cos": "Road Grade Cosine",
        "segment.wind.mag": "Wind Speed",
    }

    def __init__(self, segment: Segment = NULL_SEGMENT, torque: float = 0, Fb: float = 0, speed_mps: float = 0.0, profile: CarProfile = DEFAULT_PROFILE):
        super().__init__(segment, profile=profile)
        self.torque = torque
        self.Fb = Fb
        self.speed_mps = float(speed_mps)
        self.target_speed_mps = 0.0
        self.target_torque = 0.0
        self.time = 0
        self.dist = 0
        self.soc = 0

    def solve_DynamicNode(self, initial_DynamicNode: DynamicNode, time_step):
        self.Fm_calc()
        self.Fd_calc(initial_DynamicNode.speed_mps)
        self.Frr_calc()
        self.Fg_calc()
        self.Ft_calc()
        self.solar_energy_cal()
        self.speed_mps = initial_DynamicNode.speed_mps + self.acc * time_step
        self.dist = initial_DynamicNode.dist + initial_DynamicNode.speed_mps * time_step + 0.5 * self.acc * time_step ** 2
        self.Power_calc()
        self.soc = initial_DynamicNode.soc + ((self.P_sol - self.P_in - self.P_elec) * time_step) / self.profile.battery.battery_c_rated * 100 # use battery energy capcity instead
        # Electrical Calcs
        # self.soc = self.soc - self.current_calc(self.torque) * time_step / battery_c_rated + self.solar

    def __str__(self):
        return f"D: {self.dist} T:{self.time},P: {self.power}, A: {self.acc}, Ft: {self.Ft}, V: {self.speed_mps * 3.6}\n Forces {self.Fd, self.Frr, self.Fg, self.Fm, self.Fb, self.torque}"

    @property
    def speed(self) -> Speed:
        return Speed(mps=self.speed_mps)
    
    def __getattr__(self, name):
        """Return 0 for missing attributes instead of raising AttributeError."""
        # Don't intercept special methods - let them raise AttributeError normally
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        default = None
        print(f"Attribute '{name}' not found. Returning {default}.")
        return default


INITIAL_DYNAMIC_NODE = DynamicNode()
INITIAL_DYNAMIC_NODE.soc = 100

# make test cases for this stuff
if __name__ == "__main__":
    def test_segment():
        pass

    def test_StateNode():
        pass

    def test_DynamicNode():
        pass

    def test_VelocityNode():
        pass

