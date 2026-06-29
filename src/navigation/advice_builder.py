from __future__ import annotations

from dataclasses import dataclass

from .route_mapper import RouteMatch, RouteRepository
from .speed_utils import recommended_speed


@dataclass(frozen=True)
class LookaheadItem:
    segment_index: int
    distance_from_position_m: float
    speed_limit_kmh: float | None
    grade_percent: float
    stop_type: str | None


@dataclass(frozen=True)
class DrivingAdvice:
    route_name: str
    segment_index: int
    along_route_m: float
    cross_track_m: float
    off_route: bool
    distance_to_end_m: float
    recommended_speed_kmh: float
    speed_limit_kmh: float | None
    grade_percent: float
    elevation_m: float
    target_speed_kmh: float | None
    torque_nm: float | None
    power_w: float | None
    action: str
    warnings: list[str]
    lookahead: list[LookaheadItem]


class AdviceBuilder:
    """Interim adapter from route-position matches to static driving advice.

    This is not route-update or speed-plan optimization. It exposes the current
    API contract by packaging route data, simple speed bounds, and nearby route
    features until the real optimizer/reoptimizer is added.
    """

    def __init__(self, repository: RouteRepository, lookahead_distance_m: float = 1_000.0) -> None:
        self.repository = repository
        self.lookahead_distance_m = lookahead_distance_m

    def build(self, match: RouteMatch, current_speed_mps: float | None = None) -> DrivingAdvice:
        segment = match.segment
        speed_limit_kmh = segment.speed_limit_kmh
        target_speed_kmh = segment.target_speed_kmh
        recommended_speed_kmh = recommended_speed(speed_limit_kmh, target_speed_kmh)
        current_speed_kmh = current_speed_mps * 3.6 if current_speed_mps is not None else None

        warnings: list[str] = []
        if match.off_route:
            warnings.append(f"Off route by {match.cross_track_m:.0f} m")

        lookahead = self._lookahead(match)
        stop_ahead = next((item for item in lookahead if item.stop_type), None)
        if stop_ahead is not None:
            warnings.append(f"Stop/checkpoint ahead in {stop_ahead.distance_from_position_m:.0f} m")

        lower_limit_ahead = next(
            (
                item
                for item in lookahead
                if item.speed_limit_kmh is not None
                and speed_limit_kmh is not None
                and item.speed_limit_kmh < speed_limit_kmh - 1
            ),
            None,
        )
        if lower_limit_ahead is not None:
            warnings.append(
                f"Speed limit drops to {lower_limit_ahead.speed_limit_kmh:.0f} km/h in "
                f"{lower_limit_ahead.distance_from_position_m:.0f} m"
            )

        action = self._action(current_speed_kmh, recommended_speed_kmh, match.off_route)
        return DrivingAdvice(
            route_name=match.route_name,
            segment_index=match.segment_index,
            along_route_m=match.along_route_m,
            cross_track_m=match.cross_track_m,
            off_route=match.off_route,
            distance_to_end_m=match.distance_to_end_m,
            recommended_speed_kmh=recommended_speed_kmh,
            speed_limit_kmh=speed_limit_kmh,
            grade_percent=segment.grade_percent,
            elevation_m=segment.start.elevation_m,
            target_speed_kmh=target_speed_kmh,
            torque_nm=segment.start.torque_nm,
            power_w=segment.start.power_w,
            action=action,
            warnings=warnings,
            lookahead=lookahead,
        )

    def _action(self, current_speed_kmh: float | None, recommended_speed_kmh: float, off_route: bool) -> str:
        if off_route:
            return "return_to_route"
        if current_speed_kmh is None:
            return "hold"
        if current_speed_kmh > recommended_speed_kmh + 3:
            return "slow_down"
        if current_speed_kmh < recommended_speed_kmh - 5:
            return "speed_up"
        return "hold"

    def _lookahead(self, match: RouteMatch) -> list[LookaheadItem]:
        route = self.repository.load_route(match.route_name)
        items: list[LookaheadItem] = []
        for segment in route.segments[match.segment_index :]:
            distance_from_position_m = max(segment.start.distance_m - match.along_route_m, 0.0)
            if distance_from_position_m > self.lookahead_distance_m:
                break
            items.append(
                LookaheadItem(
                    segment_index=segment.index,
                    distance_from_position_m=distance_from_position_m,
                    speed_limit_kmh=segment.speed_limit_kmh,
                    grade_percent=segment.grade_percent,
                    stop_type=segment.start.stop_type,
                )
            )
        return items[:10]
