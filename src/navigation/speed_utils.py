from __future__ import annotations

DEFAULT_RECOMMENDED_SPEED_KMH = 45.0


def recommended_speed(speed_limit_kmh: float | None, target_speed_kmh: float | None) -> float:
    candidates = [value for value in [speed_limit_kmh, target_speed_kmh] if value is not None and value > 0]
    if not candidates:
        return DEFAULT_RECOMMENDED_SPEED_KMH
    return min(candidates)
