from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import (
    AdviceResponse,
    ClientProfileState,
    CreateSessionRequest,
    HealthResponse,
    LookaheadResponse,
    ProfileBundle,
    RouteSummary,
    RoutesResponse,
    SessionResponse,
    SyncRequest,
    SyncResponse,
    TelemetryRequest,
)
from src.api.session_store import NavigationSession, SessionStore, session_store
from src.navigation.advice_builder import AdviceBuilder, DrivingAdvice
from src.navigation.profile_builder import SYNC_PROFILE_VERSION, ProfileBundleBuilder
from src.navigation.route_mapper import RouteNotFoundError, RouteRepository, get_default_repository


def create_app(
    repository: RouteRepository | None = None,
    store: SessionStore | None = None,
) -> FastAPI:
    route_repository = repository or get_default_repository()
    sessions = store or session_store
    advice_builder = AdviceBuilder(route_repository)
    profile_builder = ProfileBundleBuilder(route_repository)

    app = FastAPI(title="Race Strategies Navigation MVP", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", routes_available=len(route_repository.list_routes()))

    @app.get("/api/routes", response_model=RoutesResponse)
    def routes() -> RoutesResponse:
        return RoutesResponse(routes=[RouteSummary(name=name) for name in route_repository.list_routes()])

    @app.get("/api/routes/{route_name}/profile", response_model=ProfileBundle)
    def route_profile(route_name: str) -> ProfileBundle:
        try:
            return profile_builder.build(route_name)
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/sessions", response_model=SessionResponse)
    def create_session(request: CreateSessionRequest) -> SessionResponse:
        route_name = request.route_name
        try:
            if route_name is None:
                route_name = route_repository.default_route_name()
            route_repository.load_route(route_name)
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        session = sessions.create(route_name)
        return _session_response(session)

    @app.get("/api/sessions/{session_id}", response_model=SessionResponse)
    def get_session(session_id: str) -> SessionResponse:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return _session_response(session)

    @app.post("/api/sessions/{session_id}/telemetry", response_model=AdviceResponse)
    def post_telemetry(session_id: str, telemetry: TelemetryRequest) -> AdviceResponse:
        session = sessions.update_telemetry(session_id, telemetry)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        try:
            match = route_repository.map_position(session.route_name, telemetry.lat, telemetry.lon)
            advice = advice_builder.build(match, telemetry.speed_mps)
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return _advice_response(session.session_id, advice)

    @app.post("/api/sessions/{session_id}/sync", response_model=SyncResponse)
    def sync_session(session_id: str, request: SyncRequest) -> SyncResponse:
        """/sync contract adapter for the navigation MVP.

        This currently returns telemetry advice plus a backend-generated placeholder
        profile when the client needs one. The future route-update/reoptimizer
        should be called from this flow once that optimizer exists.
        """
        session = sessions.update_telemetry(session_id, request.telemetry)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        try:
            match = route_repository.map_position(session.route_name, request.telemetry.lat, request.telemetry.lon)
            advice = advice_builder.build(match, request.telemetry.speed_mps)
            profile_current, profile = _build_rolling_sync_placeholder(
                session,
                session.route_name,
                match.along_route_m,
                request.telemetry,
                request.client_profile,
                profile_builder,
            )
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return SyncResponse(
            accepted=True,
            server_time=datetime.now(timezone.utc),
            profile_current=profile_current,
            latest_profile_version=SYNC_PROFILE_VERSION,
            sync_count=session.sync_count,
            profile=profile,
            advice=_advice_response(session.session_id, advice),
        )

    return app


def _session_response(session: NavigationSession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        route_name=session.route_name,
        created_at=session.created_at,
        last_telemetry_at=session.last_telemetry_at,
    )


def _build_rolling_sync_placeholder(
    session,
    route_name: str,
    current_along_route_m: float,
    telemetry: TelemetryRequest,
    client_profile: ClientProfileState | None,
    profile_builder: ProfileBundleBuilder,
) -> tuple[bool, ProfileBundle | None]:
    """Return a rolling /sync verification profile until route reoptimization exists.

    Sync-path verification placeholder only — not a real optimizer. Demo /sync
    requests increment the session sync_count and return an active profile where
    the current point and all later points gain sync_count * 0.01 km/h over the
    static base profile (along_route_m >= current telemetry position).
    Live GPS syncs reuse the current sync_count without incrementing it.
    profile_current stays false while the placeholder is active so the native phone
    app always accepts the updated active profile during MVP testing.
    """
    del client_profile  # reserved for future optimizer idempotency checks
    if telemetry.source == "demo":
        session.sync_count += 1
    profile = profile_builder.build_sync_placeholder(
        route_name,
        current_along_route_m,
        session.sync_count,
    )
    return False, profile


def _advice_response(session_id: str, advice: DrivingAdvice) -> AdviceResponse:
    return AdviceResponse(
        session_id=session_id,
        route_name=advice.route_name,
        segment_index=advice.segment_index,
        along_route_m=advice.along_route_m,
        cross_track_m=advice.cross_track_m,
        off_route=advice.off_route,
        distance_to_end_m=advice.distance_to_end_m,
        recommended_speed_kmh=advice.recommended_speed_kmh,
        speed_limit_kmh=advice.speed_limit_kmh,
        grade_percent=advice.grade_percent,
        elevation_m=advice.elevation_m,
        target_speed_kmh=advice.target_speed_kmh,
        torque_nm=advice.torque_nm,
        power_w=advice.power_w,
        action=advice.action,
        warnings=advice.warnings,
        lookahead=[
            LookaheadResponse(
                segment_index=item.segment_index,
                distance_from_position_m=item.distance_from_position_m,
                speed_limit_kmh=item.speed_limit_kmh,
                grade_percent=item.grade_percent,
                stop_type=item.stop_type,
            )
            for item in advice.lookahead
        ],
    )


app = create_app()
