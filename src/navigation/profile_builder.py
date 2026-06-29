from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from src.api.schemas import ProfileBundle, ProfilePoint

from .route_mapper import Route, RouteRepository
from .speed_utils import recommended_speed


PROFILE_VERSION = 1
SYNC_PROFILE_VERSION = 2
SYNC_SPEED_INCREMENT_KMH = 0.01
SYNC_ALONG_ROUTE_EPSILON_M = 1e-3
PROFILE_GENERATED_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)


class ProfileBundleBuilder:
    """Builds a static route-derived profile bundle for the MVP contract.

    This adapter serializes the loaded route points into the phone sync shape.
    It does not compute an optimized profile or reoptimize around telemetry;
    that behavior is future route-update work.
    """

    def __init__(self, repository: RouteRepository, profile_version: int = PROFILE_VERSION) -> None:
        self.repository = repository
        self.profile_version = profile_version

    def build(self, route_name: str) -> ProfileBundle:
        route = self.repository.load_route(route_name)
        points = [_profile_point(route, index) for index, _ in enumerate(route.points)]
        return ProfileBundle(
            route_name=route.name,
            profile_version=self.profile_version,
            profile_hash=_profile_hash(route.name, self.profile_version, 0, points),
            generated_at=PROFILE_GENERATED_AT,
            total_distance_m=route.total_distance_m,
            points=points,
        )

    def build_sync_placeholder(
        self,
        route_name: str,
        current_along_route_m: float,
        sync_count: int,
    ) -> ProfileBundle:
        """Build the /sync verification profile until real optimization exists.

        Sync-path verification placeholder only — not a real optimizer. Each sync
        adds sync_count * SYNC_SPEED_INCREMENT_KMH to the current profile point
        and all later points (along_route_m >= current telemetry position).
        Recommended speed is always
        incremented for visibility; target speed is incremented only when the route
        already has a target. Speed limit is unchanged. profile_hash changes every
        sync so the phone can detect and cache the rolling active profile.
        """
        base_profile = self.build(route_name)
        speed_increment_kmh = sync_count * SYNC_SPEED_INCREMENT_KMH
        points = [
            _sync_placeholder_point(point, current_along_route_m, speed_increment_kmh)
            for point in base_profile.points
        ]
        return ProfileBundle(
            route_name=base_profile.route_name,
            profile_version=SYNC_PROFILE_VERSION,
            profile_hash=_profile_hash(base_profile.route_name, SYNC_PROFILE_VERSION, sync_count, points),
            generated_at=PROFILE_GENERATED_AT,
            total_distance_m=base_profile.total_distance_m,
            points=points,
        )


def _profile_point(route: Route, index: int) -> ProfilePoint:
    point = route.points[index]
    segment = route.segments[index] if index < len(route.segments) else None
    speed_limit_kmh = segment.speed_limit_kmh if segment is not None else point.speed_limit_kmh
    target_speed_kmh = segment.target_speed_kmh if segment is not None else point.target_speed_kmh

    return ProfilePoint(
        index=index,
        distance_m=point.distance_m,
        along_route_m=point.distance_m,
        lat=point.lat,
        lon=point.lon,
        elevation_m=point.elevation_m,
        recommended_speed_kmh=recommended_speed(speed_limit_kmh, target_speed_kmh),
        speed_limit_kmh=speed_limit_kmh,
        target_speed_kmh=target_speed_kmh,
        torque_nm=point.torque_nm,
        power_w=point.power_w,
        grade_percent=segment.grade_percent if segment is not None else 0.0,
        stop_type=point.stop_type,
    )


def _sync_placeholder_point(
    point: ProfilePoint,
    current_along_route_m: float,
    speed_increment_kmh: float,
) -> ProfilePoint:
    if point.along_route_m + SYNC_ALONG_ROUTE_EPSILON_M < current_along_route_m or speed_increment_kmh <= 0:
        return point

    return point.model_copy(
        update={
            "recommended_speed_kmh": point.recommended_speed_kmh + speed_increment_kmh,
            "target_speed_kmh": (
                point.target_speed_kmh + speed_increment_kmh
                if point.target_speed_kmh is not None
                else None
            ),
        }
    )


def _profile_hash(
    route_name: str,
    profile_version: int,
    sync_count: int,
    points: list[ProfilePoint],
) -> str:
    payload = {
        "route_name": route_name,
        "profile_version": profile_version,
        "sync_count": sync_count,
        "points": [point.model_dump(mode="json") for point in points],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
