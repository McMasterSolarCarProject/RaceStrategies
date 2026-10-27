from copy import copy
import math
from .nodes import DynamicNode
from ..config import Engine


class DynamicProfile:
    def __init__(self, engine: Engine, profile: list[DynamicNode]):
        self.engine = engine
        self.nodes: list[DynamicNode] = profile
        self.start_velocity = self.nodes[0].velocity
        self.end_velocity = self.nodes[-1].velocity
        self.start_distance = self.nodes[0].dist
        self.end_distance = self.nodes[-1].dist
        self.dir = 1 if self.nodes[-1].velocity >= self.nodes[0].velocity else -1

    def indexing(self, velocity_interval: float, distance_interval: float):
        self.velocity_interval = velocity_interval
        self.distance_interval = distance_interval
        self.velocity_index = [0]
        self.distance_index = [0]
        next_velocity = self.start_velocity + self.dir * velocity_interval
        next_distance = self.start_distance + distance_interval
        for i in range(1, len(self.nodes)):
            while self.dir * next_velocity <= self.dir * self.nodes[i].velocity:
                next_velocity += self.dir * velocity_interval
                self.velocity_index.append(i)
            while next_distance <= self.nodes[i].dist:
                next_distance += distance_interval
                self.distance_index.append(i)

        last_index = len(self.nodes) - 1
        if self.velocity_index[-1] != last_index:
            self.velocity_index.append(last_index)
        if self.distance_index[-1] != last_index:
            self.distance_index.append(last_index)

    def node_at(self, velocity: float | None = None, distance: float | None = None, precise: bool = False) -> DynamicNode:
        if velocity is not None:
            value = velocity
            value_attribute = "velocity"
            node_index = self.velocity_index[self.index_at(velocity=velocity)]
            interpolation = {"velocity": velocity}
        elif distance is not None:
            value = distance
            value_attribute = "dist"
            node_index = self.distance_index[self.index_at(distance=distance)]
            interpolation = {"distance": distance}

        direction = self.dir if velocity is not None else 1
        index = self.index_at(velocity=velocity) if velocity is not None else self.index_at(distance=distance)
        index_values = self.velocity_index if velocity is not None else self.distance_index
        if precise:
            node_index = self._binary_upper_node(value, value_attribute, direction, index_values, index)

        if node_index == 0:
            return copy(self.nodes[0])

        lower_node = self.nodes[node_index - 1]
        upper_node = self.nodes[node_index]
        if math.isclose(getattr(lower_node, value_attribute), value):
            return copy(lower_node)
        if math.isclose(getattr(upper_node, value_attribute), value):
            return copy(upper_node)
        return lower_node.interpolate(upper_node, **interpolation)

    def _binary_upper_node(self, value: float, value_attribute: str, direction: int, index_values: list[int], bucket: int,) -> int:
        lower = max(0, index_values[bucket] - 1)
        upper = index_values[bucket + 1] + 1 if bucket + 1 < len(index_values) else len(self.nodes)
    
        target = direction * value

        while lower < upper:
            middle = (lower + upper) // 2
            if direction * getattr(self.nodes[middle], value_attribute) < target:
                lower = middle + 1
            else:
                upper = middle
        return lower

    def index_at(self, velocity: float | None = None, distance: float | None = None) -> int:
        """Return the lookup-index for a velocity or distance."""
        if velocity is not None:
            value = velocity
            direction = self.dir
            start = self.start_velocity
            end = self.end_velocity
            interval = self.velocity_interval
            index = self.velocity_index
        elif distance is not None:
            value = distance
            direction = 1
            start = self.start_distance
            end = self.end_distance
            interval = self.distance_interval
            index = self.distance_index

        offset = direction * (value - start)
        end_offset = direction * (end - start)
        if offset < 0 or offset > end_offset:
            raise ValueError("Requested value is outside the profile.")
        return min(math.floor(offset / interval), len(index) - 1)

