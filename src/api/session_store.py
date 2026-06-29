from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .schemas import TelemetryRequest


@dataclass
class NavigationSession:
    session_id: str
    route_name: str
    created_at: datetime
    last_telemetry_at: datetime | None = None
    last_telemetry: TelemetryRequest | None = None
    sync_count: int = 0


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, NavigationSession] = {}

    def create(self, route_name: str) -> NavigationSession:
        session = NavigationSession(
            session_id=str(uuid4()),
            route_name=route_name,
            created_at=datetime.now(timezone.utc),
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> NavigationSession | None:
        return self._sessions.get(session_id)

    def update_telemetry(self, session_id: str, telemetry: TelemetryRequest) -> NavigationSession | None:
        session = self.get(session_id)
        if session is None:
            return None
        session.last_telemetry = telemetry
        session.last_telemetry_at = telemetry.timestamp or datetime.now(timezone.utc)
        return session


session_store = SessionStore()
