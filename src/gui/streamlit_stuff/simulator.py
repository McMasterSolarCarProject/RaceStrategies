from dataclasses import dataclass

from src.database.fetch_route_intervals import fetch_route_intervals
from src.engine.interval_simulator import SSInterval, join_intervals
from src.engine.kinematics import Speed
from src.gui.route_map import RouteMap


@dataclass
class SimulationConfig:
    placemark: str
    db_path: str
    time_step: float
    velocity_step: float
    split_at_stops: bool
    hover: bool = True


@dataclass
class SimulationResult:
    intervals: list[SSInterval]
    master_interval: SSInterval
    route_map: RouteMap


def simulate(config: SimulationConfig) -> SimulationResult:
    route_map = RouteMap()
    master_interval = route_map.generate_simulation_map(
        config.placemark,
        time_step=config.time_step,
        velocity_step=config.velocity_step,
        hover=config.hover,
        db_path=config.db_path,
        split_at_stops=config.split_at_stops,
    )
    # generate_simulation_map returns join_intervals(route) — we need the individual intervals too
    # so fetch them back out
    intervals = fetch_route_intervals(config.placemark, split_at_stops=config.split_at_stops, db_path=config.db_path)
    if isinstance(intervals, SSInterval):
        intervals = [intervals]

    return SimulationResult(intervals, master_interval, route_map)
