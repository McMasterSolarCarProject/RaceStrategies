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
import copy
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


# ═══════════════════════════════════════════════════════════════
#  Multi-lap strategy (start → middle×n → end)
# ═══════════════════════════════════════════════════════════════

@dataclass
class LapStrategyResult:
    """Result from simulate_lap_strategy."""
    combined_interval: SSInterval
    num_middle_laps: int
    time_start: float
    time_middle: float
    time_end: float
    total_time: float
    energy_start: float
    energy_middle_total: float
    energy_end: float


def simulate_lap_strategy(
    start_interval: SSInterval,
    middle_interval: SSInterval,
    end_interval: SSInterval,
    time_budget_seconds: float,
    verbose: bool = True,
) -> LapStrategyResult:
    """
    Simulate a 3-lap race strategy: START → MIDDLE×n → END.

    The start and end laps are simulated once each. The middle lap is
    simulated once, then repeated as many times as the time budget allows.

    Parameters
    ----------
    start_interval : SSInterval
        First lap (e.g., fresh battery tactics).
    middle_interval : SSInterval
        Repeatable middle lap (fills most of race time).
    end_interval : SSInterval
        Final lap (e.g., manage remaining energy).
    time_budget_seconds : float
        Total available time (seconds).
    verbose : bool
        Print diagnostic info.

    Returns
    -------
    LapStrategyResult
        Contains combined_interval (simulated full race), lap times,
        energy per lap, and number of complete middle laps.
    """
    if verbose:
        print(f"[Lap Strategy] Simulating with {time_budget_seconds:.1f}s budget...")

    # Simulate each lap phase
    start_interval.simulate_interval()
    time_start = start_interval.time_nodes[-1].time
    energy_start = 0  # Energy tracking not implemented on TimeNode

    middle_interval.simulate_interval()
    time_middle = middle_interval.time_nodes[-1].time
    energy_middle = 0  # Energy tracking not implemented on TimeNode

    end_interval.simulate_interval()
    time_end = end_interval.time_nodes[-1].time
    energy_end = 0  # Energy tracking not implemented on TimeNode

    # Calculate how many complete middle laps fit
    time_remaining = time_budget_seconds - time_start - time_end
    num_middle_laps = max(0, int(time_remaining / time_middle))
    total_time = time_start + (num_middle_laps * time_middle) + time_end

    if verbose:
        print(f"  Start: {time_start:.1f}s ({energy_start:.0f}J)")
        print(f"  Middle: {time_middle:.1f}s ({energy_middle:.0f}J) × {num_middle_laps}")
        print(f"  End: {time_end:.1f}s ({energy_end:.0f}J)")
        print(f"  Total: {total_time:.1f}s / {time_budget_seconds:.1f}s")

    # Combine into single interval
    combined = copy.deepcopy(start_interval)

    for _ in range(num_middle_laps):
        middle_copy = copy.deepcopy(middle_interval)
        combined += middle_copy

    end_copy = copy.deepcopy(end_interval)
    combined += end_copy

    return LapStrategyResult(
        combined_interval=combined,
        num_middle_laps=num_middle_laps,
        time_start=time_start,
        time_middle=time_middle,
        time_end=time_end,
        total_time=total_time,
        energy_start=energy_start,
        energy_middle_total=energy_middle * num_middle_laps,
        energy_end=energy_end,
    )
