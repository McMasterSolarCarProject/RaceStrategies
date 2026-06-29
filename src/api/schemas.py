from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    routes_available: int


class RouteSummary(BaseModel):
    name: str


class RoutesResponse(BaseModel):
    routes: list[RouteSummary]


class CreateSessionRequest(BaseModel):
    route_name: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    route_name: str
    created_at: datetime
    last_telemetry_at: datetime | None = None


class TelemetryRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    speed_mps: float | None = Field(default=None, ge=0)
    heading_deg: float | None = Field(default=None, ge=0, le=360)
    timestamp: datetime | None = None
    source: Literal["gps", "manual", "demo"] = "gps"


class ClientProfileState(BaseModel):
    route_name: str | None = None
    profile_version: int | None = Field(default=None, ge=0)
    profile_hash: str | None = None


class ProfilePoint(BaseModel):
    index: int
    distance_m: float
    along_route_m: float
    lat: float
    lon: float
    elevation_m: float
    recommended_speed_kmh: float
    speed_limit_kmh: float | None = None
    target_speed_kmh: float | None = None
    torque_nm: float | None = None
    power_w: float | None = None
    grade_percent: float
    stop_type: str | None = None


class ProfileBundle(BaseModel):
    route_name: str
    profile_version: int
    profile_hash: str
    generated_at: datetime
    total_distance_m: float
    points: list[ProfilePoint]


class SyncRequest(BaseModel):
    telemetry: TelemetryRequest
    client_profile: ClientProfileState | None = None


class LookaheadResponse(BaseModel):
    segment_index: int
    distance_from_position_m: float
    speed_limit_kmh: float | None = None
    grade_percent: float
    stop_type: str | None = None


class AdviceResponse(BaseModel):
    session_id: str
    route_name: str
    segment_index: int
    along_route_m: float
    cross_track_m: float
    off_route: bool
    distance_to_end_m: float
    recommended_speed_kmh: float
    speed_limit_kmh: float | None = None
    grade_percent: float
    elevation_m: float
    target_speed_kmh: float | None = None
    torque_nm: float | None = None
    power_w: float | None = None
    action: str
    warnings: list[str]
    lookahead: list[LookaheadResponse]


class SyncResponse(BaseModel):
    accepted: bool
    server_time: datetime
    profile_current: bool
    latest_profile_version: int
    sync_count: int = 0
    profile: ProfileBundle | None = None
    advice: AdviceResponse | None = None
