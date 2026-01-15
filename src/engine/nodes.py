from __future__ import annotations
from .kinematics import Vec, Velocity, Displacement, Speed, Coordinate, ZERO_VEC, UNIT_VEC, ZERO_VELOCITY
from ..utils.constants import *
from .models import Motor

class Segment(Displacement):  # Meters
    def __init__(self, p1: Coordinate, p2: Coordinate, id: int = 0, speed_limit: Speed = Speed(0),  ghi: float = 0, wind: Velocity = ZERO_VEC, v_eff: Speed = Speed(0), t_eff: float = 0):
        self.id = id
        super().__init__(p1, p2)
        self.displacement = Displacement(p1, p2)
        self.v_eff = Velocity(self.displacement.unit_vector(), v_eff)
        self.t_eff = t_eff
        self.ghi = ghi
        self.wind = wind
        self.speed_limit = speed_limit
        self.tdist = self.dist

    def __str__(self):
        return f"Total Distance: {self.tdist} | V eff: {self.v_eff.kmph} | P eff: {self.t_eff}"

class StateNode:
    NUMERICAL_METRICS = {
        "torque": "Torque (Nm)",
        "Fb": "Braking Force (N)",
        "velocity.mps": "Velocity (m/s)",
        "velocity.kmph": "Velocity (km/h)",
        "velocity.mph": "Velocity (mph)",
        "Fm": "Motor Force (N)",
    }

    def __init__(self, segment: Segment, torque: float = 0, Fb: float = 0, velocity: Velocity = ZERO_VELOCITY):
        self.segment = segment
        self.torque = torque
        self.Fb = Fb
        self.velocity = velocity
        self.Fm = 0

    def Fm_calc(self, velocity: Velocity):
        # if velocity.mag <= 0.2:
        #     self.Fm = 50
        # else:
        #     self.Fm = self.power / velocity.mag
        self.Fm = self.torque * wheel_radius

    def Fd_calc(self, velocity: Velocity, wind: Velocity = ZERO_VELOCITY):
        try:
            (velocity - wind).mag ** 2
        except OverflowError:
            print("ERROR: The value of velocity in fd_calc is too high! Try a smaller timestep")
            print(f"velocity: {velocity.mps} mps clamped to velocity: 200 mps")
            velocity = Velocity(unit_vec=velocity.unit_vector(), speed=Speed(mps=200))
        finally:
            self.Fd = 0.5 * air_density * coef_drag * cross_section * ((velocity - wind).mag ** 2)

    def Frr_calc(self, seg: Segment):
        self.Frr = coef_rr * car_mass * accel_g * seg.gradient.cos()

    def Fg_calc(self, seg: Segment):
        self.Fg = car_mass * accel_g * seg.gradient.sin()

    def Ft_calc(self):
        self.Ft = self.Fm - self.Fd - self.Frr - self.Fg - self.Fb

    def solar_energy_cal(self):
        self.solar = 0

    @classmethod
    def get_numerical_metrics(cls) -> list[str]:
        """
        Contains a list of all the numerical attributes that can be plotted on a graph.
        This is to allow the gui app to dynamically display these metrics.
        If new attributes are added to StateNode, then NUMERICAL_METRICS must be updated.
        """
        return list(cls.NUMERICAL_METRICS.keys())


class TimeNode(StateNode):
    NUMERICAL_METRICS = {
        **StateNode.NUMERICAL_METRICS,
        "time": "Time (s)",
        "dist": "Distance (m)",
        "acc": "Acceleration (m/s²)",
        "soc": "State of Charge (%)",
    }

    def __init__(self, segment: Segment, motor: Motor, time: float = 0, dist: float = 0, velocity: Velocity = ZERO_VELOCITY, acc: float = 0, torque: float = 0, Fb: float = 0, soc: float = 0):
        super().__init__(segment, torque, Fb)
        self.time = time
        self.dist = dist
        self.velocity = velocity
        self.acc = acc
        self.soc = soc
        self.motor = motor

    
    def current_calc(self, torque):
        self.motor.update_torque(torque)
        return self.motor.current

    def solve_TimeNode(self, initial_TimeNode: TimeNode, segment: Segment, time_step):
        self.Fm_calc(initial_TimeNode.velocity)
        self.Fd_calc(initial_TimeNode.velocity)  # add wind here
        self.Frr_calc(segment)
        self.Fg_calc(segment)
        self.Ft_calc()
        self.solar_energy_cal()
        self.acc = self.Ft / car_mass
        # self.velocity = Velocity(segment.unit_vector(), Speed(initial_TimeNode.velocity.mps + self.acc * time_step))
        # Capping at 200 mps due to a overflow error where self.Ft grows very high when the time_step value is too large
        self.velocity = Velocity(segment.unit_vector(), Speed(max(0, min(200, initial_TimeNode.velocity.mps + self.acc * time_step))))
        self.dist = initial_TimeNode.dist + initial_TimeNode.velocity.mag * time_step + 0.5 * self.acc * time_step ** 2

        # Electrical Calcs
        self.soc = self.soc - self.current_calc(self.torque) * time_step / battery_c_rated + self.solar

    def __str__(self):
        return f"D: {self.dist} T:{self.time},P: {self.power}, A: {self.acc}, Ft: {self.Ft}, V: {self.velocity.kmph}\n Forces {self.Fd, self.Frr, self.Fg}"


class VelocityNode(StateNode):
    #constant vel --> motor force -->  power, torque --> energy per metre (epm)
    def __init__(self, segment: Segment, motor: Motor, velocity: Velocity = ZERO_VELOCITY):
        super().__init__(segment, 0, 0, velocity)
        self.motor = motor

    def solve_velocity(self,segment):
        self.Fd_calc(self.velocity)
        self.Fg_calc(segment)
        self.Frr_calc(segment)
        self.solar_energy_cal()
        self.Fm = self.Fg + self.Frr + self.Fd
        self.P_mech = self.Fm * self.velocity.mps
        self.torque = self.Fm * wheel_radius
        self.motor.update_velocity(self.velocity)
        if self.motor.velocity.mps < self.velocity.mps:
            print("dunno")
            return False
            raise ValueError(f"Power from Torque of {self.torque} is too low for {self.velocity.mps:.2f} m/s")
        self.P_bat = self.motor.voltage * self.motor.current
        # if self.P_bat == 0:
        #     raise ValueError(f"Power is zero for velocity {self.velocity.mps:.2f} m/s.")
        self.epm = self.P_bat / (self.velocity.mps) #- self.solar / self.velocity.mps
        return True


# make test cases for this stuff
if __name__ == "__main__":
    def test_segment():
        pass

    def test_StateNode():
        pass

    def test_TimeNode():
        pass

    def test_VelocityNode():
        pass

    print("typeshi")