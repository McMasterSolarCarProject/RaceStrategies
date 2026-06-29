from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.session_store import SessionStore
from src.navigation.advice_builder import AdviceBuilder
from src.navigation.profile_builder import (
    PROFILE_VERSION,
    SYNC_PROFILE_VERSION,
    SYNC_SPEED_INCREMENT_KMH,
    ProfileBundleBuilder,
)
from src.navigation.route_mapper import RouteRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUTE_NAME = "A. Independence to Topeka"


def test_route_mapper_maps_known_coordinate_to_segment():
    repository = RouteRepository(project_root=PROJECT_ROOT)

    match = repository.map_position(ROUTE_NAME, 39.092185, -94.417077)

    assert match.route_name == ROUTE_NAME
    assert match.segment_index == 0
    assert match.cross_track_m < 1
    assert not match.off_route


def test_route_mapper_flags_far_off_coordinate():
    repository = RouteRepository(project_root=PROJECT_ROOT)

    match = repository.map_position(ROUTE_NAME, 38.0, -95.0)

    assert match.off_route
    assert match.cross_track_m > 1_000


def test_advice_builder_returns_static_segment_fields():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    match = repository.map_position(ROUTE_NAME, 39.092185, -94.417077)

    advice = AdviceBuilder(repository).build(match, current_speed_mps=20)

    assert advice.recommended_speed_kmh > 0
    assert advice.speed_limit_kmh is not None
    assert advice.grade_percent is not None
    assert advice.lookahead
    assert advice.action in {"hold", "slow_down", "speed_up", "return_to_route"}


def test_profile_bundle_contains_route_points_and_advice_fields():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)

    profile = ProfileBundleBuilder(repository).build(ROUTE_NAME)
    first_point = profile.points[0]

    assert profile.route_name == ROUTE_NAME
    assert profile.profile_version == PROFILE_VERSION
    assert profile.profile_hash
    assert profile.total_distance_m == route.total_distance_m
    assert len(profile.points) == len(route.points)
    assert first_point.index == 0
    assert first_point.along_route_m == first_point.distance_m
    assert first_point.lat == route.points[0].lat
    assert first_point.lon == route.points[0].lon
    assert first_point.recommended_speed_kmh > 0
    assert first_point.speed_limit_kmh is not None
    assert first_point.grade_percent is not None


def test_api_session_and_telemetry_flow():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)

    routes = client.get("/api/routes")
    assert routes.status_code == 200
    assert ROUTE_NAME in [route["name"] for route in routes.json()["routes"]]

    created = client.post("/api/sessions", json={"route_name": ROUTE_NAME})
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    advice = client.post(
        f"/api/sessions/{session_id}/telemetry",
        json={"lat": 39.092185, "lon": -94.417077, "speed_mps": 10, "source": "manual"},
    )
    assert advice.status_code == 200
    body = advice.json()
    assert body["session_id"] == session_id
    assert body["route_name"] == ROUTE_NAME
    assert body["recommended_speed_kmh"] > 0
    assert "lookahead" in body


def test_sync_without_client_profile_returns_placeholder_profile_with_future_speed_marker():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    base_profile = ProfileBundleBuilder(repository).build(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)
    session_id = client.post("/api/sessions", json={"route_name": ROUTE_NAME}).json()["session_id"]
    current_point = route.points[0]

    response = client.post(
        f"/api/sessions/{session_id}/sync",
        json={
            "telemetry": {
                "lat": current_point.lat,
                "lon": current_point.lon,
                "speed_mps": 10,
                "source": "demo",
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["sync_count"] == 1
    assert body["profile_current"] is False
    assert body["latest_profile_version"] == SYNC_PROFILE_VERSION
    assert body["profile"]["route_name"] == ROUTE_NAME
    assert body["profile"]["profile_version"] == SYNC_PROFILE_VERSION
    assert body["profile"]["profile_hash"] != base_profile.profile_hash
    assert len(body["profile"]["points"]) == len(route.points)

    points = body["profile"]["points"]
    assert points[0]["recommended_speed_kmh"] == pytest.approx(
        base_profile.points[0].recommended_speed_kmh + SYNC_SPEED_INCREMENT_KMH
    )
    assert points[1]["recommended_speed_kmh"] == pytest.approx(
        base_profile.points[1].recommended_speed_kmh + SYNC_SPEED_INCREMENT_KMH
    )

    if base_profile.points[0].target_speed_kmh is None:
        assert points[0]["target_speed_kmh"] is None
    else:
        assert points[0]["target_speed_kmh"] == pytest.approx(
            base_profile.points[0].target_speed_kmh + SYNC_SPEED_INCREMENT_KMH
        )

    if base_profile.points[1].target_speed_kmh is None:
        assert points[1]["target_speed_kmh"] is None
    else:
        assert points[1]["target_speed_kmh"] == pytest.approx(
            base_profile.points[1].target_speed_kmh + SYNC_SPEED_INCREMENT_KMH
        )


def test_rolling_sync_second_sync_increments_future_points_cumulatively():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    base_profile = ProfileBundleBuilder(repository).build(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)
    session_id = client.post("/api/sessions", json={"route_name": ROUTE_NAME}).json()["session_id"]

    first = client.post(
        f"/api/sessions/{session_id}/sync",
        json={
            "telemetry": {
                "lat": route.points[0].lat,
                "lon": route.points[0].lon,
                "speed_mps": 10,
                "source": "demo",
            }
        },
    ).json()
    first_profile = first["profile"]
    assert first["profile_current"] is False

    second = client.post(
        f"/api/sessions/{session_id}/sync",
        json={
            "telemetry": {
                "lat": route.points[1].lat,
                "lon": route.points[1].lon,
                "speed_mps": 10,
                "source": "demo",
            },
            "client_profile": {
                "route_name": ROUTE_NAME,
                "profile_version": SYNC_PROFILE_VERSION,
                "profile_hash": first_profile["profile_hash"],
            },
        },
    ).json()

    assert second["profile_current"] is False
    assert second["sync_count"] == 2
    assert second["profile"]["profile_hash"] != first_profile["profile_hash"]
    second_points = second["profile"]["points"]
    assert second_points[0]["recommended_speed_kmh"] == base_profile.points[0].recommended_speed_kmh
    assert second_points[1]["recommended_speed_kmh"] == pytest.approx(
        base_profile.points[1].recommended_speed_kmh + 2 * SYNC_SPEED_INCREMENT_KMH
    )
    assert second_points[2]["recommended_speed_kmh"] == pytest.approx(
        base_profile.points[2].recommended_speed_kmh + 2 * SYNC_SPEED_INCREMENT_KMH
    )


def test_four_demo_syncs_at_same_point_increment_speed_cumulatively():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    base_profile = ProfileBundleBuilder(repository).build(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)
    session_id = client.post("/api/sessions", json={"route_name": ROUTE_NAME}).json()["session_id"]
    current_point = route.points[0]
    expected_speeds = [
        base_profile.points[0].recommended_speed_kmh + increment * SYNC_SPEED_INCREMENT_KMH
        for increment in range(1, 5)
    ]

    for click, expected_speed in enumerate(expected_speeds, start=1):
        response = client.post(
            f"/api/sessions/{session_id}/sync",
            json={
                "telemetry": {
                    "lat": current_point.lat,
                    "lon": current_point.lon,
                    "speed_mps": 10,
                    "source": "demo",
                }
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sync_count"] == click
        assert body["profile"]["points"][0]["recommended_speed_kmh"] == pytest.approx(expected_speed)


def test_gps_sync_does_not_increment_sync_count():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)
    session_id = client.post("/api/sessions", json={"route_name": ROUTE_NAME}).json()["session_id"]
    current_point = route.points[0]

    for _ in range(3):
        response = client.post(
            f"/api/sessions/{session_id}/sync",
            json={
                "telemetry": {
                    "lat": current_point.lat,
                    "lon": current_point.lon,
                    "speed_mps": 10,
                    "source": "gps",
                }
            },
        )
        assert response.status_code == 200
        assert response.json()["sync_count"] == 0

    demo = client.post(
        f"/api/sessions/{session_id}/sync",
        json={
            "telemetry": {
                "lat": current_point.lat,
                "lon": current_point.lon,
                "speed_mps": 10,
                "source": "demo",
            }
        },
    )
    assert demo.status_code == 200
    assert demo.json()["sync_count"] == 1


def test_route_profile_endpoint_returns_full_profile():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)

    response = client.get(f"/api/routes/{ROUTE_NAME}/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["route_name"] == ROUTE_NAME
    assert body["profile_version"] == PROFILE_VERSION
    assert len(body["points"]) == len(route.points)


def test_sync_always_returns_updated_profile_even_when_client_reports_current_hash():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)
    session_id = client.post("/api/sessions", json={"route_name": ROUTE_NAME}).json()["session_id"]

    first = client.post(
        f"/api/sessions/{session_id}/sync",
        json={
            "telemetry": {
                "lat": route.points[0].lat,
                "lon": route.points[0].lon,
                "speed_mps": 10,
                "source": "demo",
            }
        },
    ).json()
    first_profile = first["profile"]

    repeat = client.post(
        f"/api/sessions/{session_id}/sync",
        json={
            "telemetry": {
                "lat": route.points[0].lat,
                "lon": route.points[0].lon,
                "speed_mps": 10,
                "source": "demo",
            },
            "client_profile": {
                "route_name": ROUTE_NAME,
                "profile_version": SYNC_PROFILE_VERSION,
                "profile_hash": first_profile["profile_hash"],
            },
        },
    ).json()

    assert repeat["profile_current"] is False
    assert repeat["profile"] is not None
    assert repeat["profile"]["profile_hash"] != first_profile["profile_hash"]
    repeat_points = repeat["profile"]["points"]
    assert repeat_points[0]["recommended_speed_kmh"] == pytest.approx(
        first["profile"]["points"][0]["recommended_speed_kmh"] + SYNC_SPEED_INCREMENT_KMH
    )
    assert repeat_points[1]["recommended_speed_kmh"] == pytest.approx(
        first["profile"]["points"][1]["recommended_speed_kmh"] + SYNC_SPEED_INCREMENT_KMH
    )


def test_sync_accepts_telemetry_and_returns_advice():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)
    session_id = client.post("/api/sessions", json={"route_name": ROUTE_NAME}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/sync",
        json={
            "telemetry": {
                "lat": route.points[1].lat,
                "lon": route.points[1].lon,
                "speed_mps": 8,
                "source": "demo",
            },
            "client_profile": {"profile_version": SYNC_PROFILE_VERSION},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["profile_current"] is False
    assert body["profile"] is not None
    assert body["advice"]["session_id"] == session_id
    assert body["advice"]["route_name"] == ROUTE_NAME
    assert body["advice"]["recommended_speed_kmh"] > 0
    assert body["advice"]["lookahead"]


def test_api_replay_progresses_along_route():
    repository = RouteRepository(project_root=PROJECT_ROOT)
    route = repository.load_route(ROUTE_NAME)
    app = create_app(repository=repository, store=SessionStore())
    client = TestClient(app)
    session_id = client.post("/api/sessions", json={"route_name": ROUTE_NAME}).json()["session_id"]

    along_values = []
    for point in route.points[:4]:
        response = client.post(
            f"/api/sessions/{session_id}/telemetry",
            json={"lat": point.lat, "lon": point.lon, "speed_mps": 8, "source": "demo"},
        )
        assert response.status_code == 200
        along_values.append(response.json()["along_route_m"])

    assert along_values == sorted(along_values)
