"""
Shared utilities for all optimizer implementations.

Contains:
  - OptResult dataclass
  - build_bounds()
  - validate_with_full_sim()
  - simulate_single_segment()
"""
from __future__ import annotations

import time
import numpy as np
from dataclasses import dataclass

from ..engine.interval_simulator import SSInterval, MAX_TORQUE, BRAKE
from ..engine.kinematics import Speed
from ..engine.nodes import Segment, VelocityNode
from ..utils import constants
from .coarse_to_fine import simulate_interval_with_v_eff


# ═══════════════════════════════════════════════════════════════
#  Result container
# ═══════════════════════════════════════════════════════════════

@dataclass
class OptResult:
    """Standard result container returned by every optimizer method."""
    method: str
    speeds_kmph: list[float]
    total_time: float        # from full simulation (seconds)
    n_evals: int             # objective / segment-sim evaluations
    wall_time: float         # wall-clock duration of optimization (seconds)
    raw_result: object = None


# ═══════════════════════════════════════════════════════════════
#  Common utilities
# ═══════════════════════════════════════════════════════════════

def build_bounds(
    interval: SSInterval,
    v_min: float = 20.0,
    v_max: float = 100.0,
) -> list[tuple[float, float]]:
    """Per-segment (min, max) speed bounds in km/h, clamped to speed limits."""
    bounds = []
    for seg in interval.segments:
        lo, hi = v_min, v_max
        if seg.speed_limit.mps > 0:
            hi = min(hi, seg.speed_limit.kmph)
            lo = min(lo, hi)
        bounds.append((lo, hi))
    return bounds


def validate_with_full_sim(interval: SSInterval, speeds_kmph: list[float]) -> float:
    """
    Run the full SSInterval simulation (including braking envelope)
    with the given speed profile.  Returns total time in seconds.
    """
    return simulate_interval_with_v_eff(interval, speeds_kmph)


# ═══════════════════════════════════════════════════════════════
#  Segment-level simulator
# ═══════════════════════════════════════════════════════════════

def simulate_single_segment(
    segment: Segment,
    entry_speed_mps: float,
    v_eff_kmph: float,
    *,
    dt_base: float = 1.0,
    dv_max_mps: float = 1.0 / 3.6,
    max_steps: int = 50_000,
) -> tuple[float, float, float]:
    """
    Simulate ONE road segment with full time-stepping physics.

    Replicates the force-balance model of SSInterval.simulate_interval
    for a single segment in isolation — **no braking envelope**.
    All transient effects (acceleration ramp, speed-dependent drag,
    grade force, rolling resistance) are preserved.

    Parameters
    ----------
    segment : Segment
        Road segment (contains distance, gradient, wind, speed_limit).
    entry_speed_mps : float
        Speed at entry (m/s).
    v_eff_kmph : float
        Target effective speed (km/h).
    dt_base : float
        Base timestep in seconds (refined by adaptive timestep).
    dv_max_mps : float
        Max speed change per timestep for adaptive control.
    max_steps : int
        Safety limit on iterations.

    Returns
    -------
    (exit_speed_mps, elapsed_seconds, energy_joules)
    """
    # Clamp v_eff to speed limit
    if segment.speed_limit.mps > 0:
        target_mps = min(v_eff_kmph / 3.6, segment.speed_limit.mps)
    else:
        target_mps = v_eff_kmph / 3.6

    # Compute cruise torque (same method as coarse_to_fine.set_v_eff)
    vnode = VelocityNode(segment, Speed(mps=target_mps))
    t_eff = vnode.torque if vnode.solve_velocity() else 0.0

    # Pre-compute segment geometry constants
    seg_dist = segment.dist
    grad_sin = segment.gradient.sin()
    grad_cos = segment.gradient.cos()
    Fg_const = constants.car_mass * constants.accel_g * grad_sin
    Frr_const = constants.coef_rr * constants.car_mass * constants.accel_g * grad_cos
    drag_coeff = 0.5 * constants.air_density * constants.coef_drag * constants.cross_section

    # State variables
    speed = entry_speed_mps
    dist = 0.0
    elapsed = 0.0
    energy = 0.0

    for _ in range(max_steps):
        if dist >= seg_dist:
            break

        # ── Control law (mirrors SSInterval forward loop) ──
        if speed < target_mps:
            torque = MAX_TORQUE                    # accelerate
        else:
            torque = t_eff                         # cruise

        # ── Force balance (mirrors StateNode exactly) ──
        Fm = torque / constants.wheel_radius * constants.num_motors
        Fd = drag_coeff * speed * speed            # wind = 0 in current DB
        Ft = Fm - Fd - Frr_const - Fg_const
        acc = Ft / constants.car_mass

        # ── Adaptive timestep (mirrors SSInterval.adaptive_timestep) ──
        dt = dt_base
        if acc != 0 and abs(acc * dt) > dv_max_mps:
            dt = abs(dv_max_mps / acc)

        # Don't overshoot segment boundary
        d_step = speed * dt + 0.5 * acc * dt * dt
        remaining = seg_dist - dist
        if d_step > remaining and speed > 0:
            disc = speed * speed + 2.0 * acc * remaining
            if acc != 0 and disc >= 0:
                dt = (-speed + np.sqrt(disc)) / acc
                dt = max(dt, 1e-4)
            else:
                dt = remaining / max(speed, 1e-4)

        # ── Update state ──
        new_speed = speed + acc * dt
        dist += speed * dt + 0.5 * acc * dt * dt
        elapsed += dt

        # Energy: P_bat = P_mech × η  (matches Power_calc: 0.9 efficiency)
        if new_speed > 0:
            P_mech = torque * (new_speed / constants.wheel_radius) * constants.num_motors
            energy += P_mech * 0.9 * dt

        # ── Stall detection (matches SSInterval logic) ──
        if new_speed <= 0 and speed <= 0:
            Fm_max = MAX_TORQUE / constants.wheel_radius * constants.num_motors
            if Fm_max < Fg_const:
                return 0.0, elapsed, energy

        speed = max(0.0, new_speed)

    return speed, elapsed, energy


def _snap_to_grid(value: float, grid: np.ndarray) -> int:
    """Return the index of the nearest grid point (grid must be sorted)."""
    idx = np.searchsorted(grid, value)
    if idx > 0 and (idx >= len(grid) or
                     abs(grid[idx - 1] - value) <= abs(grid[idx] - value)):
        idx -= 1
    return idx
