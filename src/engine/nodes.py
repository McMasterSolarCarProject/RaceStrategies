from __future__ import annotations
from .kinematics import Vec, Velocity, Displacement, Speed, Coordinate, ZERO_VEC, UNIT_VEC, ZERO_VELOCITY
from ..utils.constants import *
from .models import Motor
from .motor_calcs import motor

# Speed takes mps as the default parameter, so all calculations are in mps
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
        return f"Total Distance: {self.tdist} | V eff: {self.v_eff.kmph} | T eff: {self.t_eff}"

class StateNode:
    def __init__(self, segment: Segment, torque: float = 0, Fb: float = 0, speed: Speed = Speed(0)):
        self.segment = segment
        self.torque = torque
        self.Fb = Fb
        self.speed = speed
        self.Fm = 0

    def Fm_calc(self):
        # if velocity.mag <= 0.2:
        #     self.Fm = 50
        # else:
        #     self.Fm = self.power / velocity.mag
        self.Fm = self.torque / wheel_radius

    def Fd_calc(self, initial_speed: Speed):
        velocity = Velocity(self.segment.displacement.unit_vector(), initial_speed)
        self.Fd = 0.5 * air_density * coef_drag * cross_section * ((velocity - self.segment.wind).mag ** 2)

    def Frr_calc(self):
        self.Frr = coef_rr * car_mass * accel_g * self.segment.gradient.cos()

    def Fg_calc(self):
        self.Fg = car_mass * accel_g * self.segment.gradient.sin()

    def Ft_calc(self):
        self.Ft = self.Fm - self.Fd - self.Frr - self.Fg - self.Fb

    def solar_energy_cal(self):
        self.solar = 0


class TimeNode(StateNode):
    def __init__(self, segment: Segment, motor: Motor, time: float = 0, dist: float = 0, speed: Speed = Speed(0), acc: float = 0, torque: float = 0, Fb: float = 0, soc: float = 0):
        super().__init__(segment, torque, Fb, speed)
        self.time = time
        self.dist = dist
        self.acc = acc
        self.soc = soc
        self.motor = motor

    def solve_TimeNode(self, initial_TimeNode: TimeNode, time_step):
        self.Fm_calc()
        self.Fd_calc(initial_TimeNode.speed)
        self.Frr_calc()
        self.Fg_calc()
        self.Ft_calc()
        self.solar_energy_cal()
        self.acc = self.Ft / car_mass
        self.speed = Speed(initial_TimeNode.speed.mps + self.acc * time_step)
        self.dist = initial_TimeNode.dist + initial_TimeNode.speed.mps * time_step + 0.5 * self.acc * time_step ** 2

        # Electrical Calcs
        # self.soc = self.soc - self.current_calc(self.torque) * time_step / battery_c_rated + self.solar

    def __str__(self):
        return f"D: {self.dist} T:{self.time},P: {self.power}, A: {self.acc}, Ft: {self.Ft}, V: {self.speed.kmph}\n Forces {self.Fd, self.Frr, self.Fg}"


class VelocityNode(StateNode):
    #constant vel --> motor force -->  power, torque --> energy per metre (epm)
    def __init__(self, segment: Segment, speed: Speed = Speed(0)):
        super().__init__(segment, 0, 0, speed)

    def solve_velocity(self):
        self.Fd_calc(self.speed)
        self.Fg_calc()
        self.Frr_calc()
        self.solar_energy_cal()
        self.Fm = self.Fg + self.Frr + self.Fd
        self.P_mech = self.Fm * self.speed.mps
        self.torque = self.Fm * wheel_radius
        motor_speed = motor.speed_from_torque(self.torque)
        if motor_speed < self.speed.rpm():
            print("dunno")
            return False
            raise ValueError(f"Power from Torque of {self.torque} is too low for {self.velocity.mps:.2f} m/s")
        self.P_bat = self.motor.voltage * self.motor.current
        # if self.P_bat == 0:
        #     raise ValueError(f"Power is zero for velocity {self.velocity.mps:.2f} m/s.")
        self.epm = self.P_bat / (self.speed.mps) #- self.solar / self.velocity.mps
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

    print("typeshi;"*67)