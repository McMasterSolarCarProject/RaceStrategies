from ..config import Vehicle, constants, vehicle_default
from ..models import Segment, NULL_SEGMENT

class StateNode:

    def __init__(self, segment: Segment, vehicle: Vehicle =  vehicle_default):
        self.segment = segment
        self.vehicle = vehicle

        self.torque = 0

    def Fm_calc(self):
        self.Fm = self.torque / self.vehicle.wheel_radius * self.vehicle.num_motors

    def Fd_calc(self):
        pass

    def solve_cruise_state(self):
        pass

class DynamicNode(StateNode):

    def __init__(self, segment: Segment, vehicle: Vehicle = vehicle_default):
        super().__init__(segment, vehicle)


    def solve_DynamicNode(self):
        pass

INITIAL_DYNAMIC_NODE = DynamicNode(NULL_SEGMENT, vehicle_default)