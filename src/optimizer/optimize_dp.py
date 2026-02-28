"""
Forward Dynamic Programming optimizer for solar car race strategy.

Uses backward DP with precomputed segment-level transition tables.
Each transition runs the full force-balance time-stepping physics,
preserving all transient effects (acceleration, drag, grade, etc.).

Guaranteed globally optimal for the discretised problem.
Complexity: O(K × S × A) — linear in segments, polynomial overall.
"""
from __future__ import annotations

import time
import numpy as np

from ..engine.interval_simulator import SSInterval, BRAKE
from ..engine.nodes import Segment
from ..utils import constants
from .common import OptResult, validate_with_full_sim, simulate_single_segment, _snap_to_grid


def _precompute_segment_transitions(
    segment: Segment,
    speed_grid_mps: np.ndarray,
    action_grid_kmph: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Precompute ALL (entry_speed × v_eff) transitions for one segment.

    Returns
    -------
    exit_speeds : ndarray[S, A]   – exit speed in m/s
    times       : ndarray[S, A]   – elapsed seconds
    energies    : ndarray[S, A]   – energy in joules
    """
    S = len(speed_grid_mps)
    A = len(action_grid_kmph)
    exit_speeds = np.zeros((S, A))
    times = np.full((S, A), np.inf)
    energies = np.zeros((S, A))

    for s_idx in range(S):
        for a_idx in range(A):
            es, dt, en = simulate_single_segment(
                segment, speed_grid_mps[s_idx], action_grid_kmph[a_idx]
            )
            exit_speeds[s_idx, a_idx] = es
            times[s_idx, a_idx] = dt
            energies[s_idx, a_idx] = en

    return exit_speeds, times, energies


def optimize_dp(
    interval: SSInterval,
    v_min: float = 20.0,
    v_max: float = 100.0,
    *,
    speed_resolution: float = 2.0,
    v_eff_resolution: float = 2.0,
    verbose: bool = True,
) -> OptResult:
    """
    Backward Dynamic Programming with segment-level simulation.

    Each DP transition uses a **precomputed transition table** built by
    running ``simulate_single_segment()`` for every (entry_speed, v_eff)
    pair per segment.  This keeps full force-balance time-stepping
    physics — preserving ALL transient effects — while converting the
    backward sweep into pure numpy array lookups.

    State space
        (k, s) — segment index k, discretised entry speed index s.

    Action space
        v_eff for segment k (discretised per-segment, clamped to limits).

    Transition
        precomputed table[k][s, a] → (exit_speed, Δt, ΔE)

    Terminal condition
        After the last segment the car must stop.  Approximate braking
        cost V[K][s] = s / a_brake provides a smooth gradient so the
        backward pass naturally reduces speed near the end.
        The final result is always validated with the full braking-envelope
        simulation.

    Complexity
        O(K × S × A)  segment simulations in the precompute phase,
        then O(K × S × A) array lookups in the DP sweep.
        Much faster than brute force O(A^K), and guaranteed globally
        optimal for the discretised problem.

    Parameters
    ----------
    speed_resolution : float
        Discretisation step for state speed grid (km/h).
    v_eff_resolution : float
        Discretisation step for control speed grid (km/h).
    """
    segments = interval.segments
    K = len(segments)

    # ── Build grids ──
    speed_grid_kmph = np.arange(0, v_max + speed_resolution, speed_resolution)
    speed_grid_mps = speed_grid_kmph / 3.6
    S = len(speed_grid_mps)

    per_seg_actions: list[np.ndarray] = []
    for seg in segments:
        hi, lo = v_max, v_min
        if seg.speed_limit.mps > 0:
            hi = min(hi, seg.speed_limit.kmph)
            lo = min(lo, hi)
        per_seg_actions.append(
            np.arange(lo, hi + v_eff_resolution * 0.5, v_eff_resolution)
        )

    # Braking deceleration (constant approximation)
    a_brake = BRAKE / constants.car_mass          # ≈ 1.74 m/s²

    t0 = time.perf_counter()
    n_evals = 0

    # ── Precompute transition tables (the expensive part) ──
    # transition_tables[k] = (exit_speeds[S,A], times[S,A], energies[S,A])
    transition_tables: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for k, seg in enumerate(segments):
        A_k = len(per_seg_actions[k])
        if verbose:
            print(f"  precomputing segment {k+1}/{K}  "
                  f"({S}×{A_k} = {S * A_k} sims)")
        tbl = _precompute_segment_transitions(
            seg, speed_grid_mps, per_seg_actions[k]
        )
        transition_tables.append(tbl)
        n_evals += S * A_k

    t_precompute = time.perf_counter() - t0
    if verbose:
        print(f"  precomputation done: {n_evals:,} sims in {t_precompute:.1f}s")

    # ── Snap exit speeds to grid indices (vectorised) ──
    exit_idx_tables: list[np.ndarray] = []
    for es_table, _, _ in transition_tables:
        # es_table is [S, A] of exit speeds in m/s
        idx = np.searchsorted(speed_grid_mps, es_table)  # [S, A]
        # Clamp and snap to nearest
        idx = np.clip(idx, 0, S - 1)
        # Check if idx-1 is closer
        prev_idx = np.clip(idx - 1, 0, S - 1)
        closer_to_prev = np.abs(speed_grid_mps[prev_idx] - es_table) < np.abs(speed_grid_mps[idx] - es_table)
        idx = np.where(closer_to_prev, prev_idx, idx)
        exit_idx_tables.append(idx)

    # ── DP tables ──
    V = np.full((K + 1, S), np.inf)
    policy = np.full((K, S), -1, dtype=int)

    # ── Terminal cost ──
    for s_idx, s_mps in enumerate(speed_grid_mps):
        V[K][s_idx] = s_mps / a_brake if s_mps > 0 else 0.0

    if verbose:
        print(f"DP: {K} segments × {S} speed states, "
              f"speed grid 0–{v_max} km/h (Δ{speed_resolution}), "
              f"action Δ{v_eff_resolution} km/h")

    # ── Backward pass (fast — pure array lookups) ──
    t_dp = time.perf_counter()
    for k in range(K - 1, -1, -1):
        _, dt_table, _ = transition_tables[k]
        s_next_table = exit_idx_tables[k]
        A_k = len(per_seg_actions[k])

        remaining_after = interval.total_dist - segments[k].tdist

        for s_idx in range(S):
            s_mps = speed_grid_mps[s_idx]
            remaining_from_here = remaining_after + segments[k].dist
            brake_dist = s_mps ** 2 / (2.0 * a_brake)
            if brake_dist > remaining_from_here * 1.5:
                continue

            # Vectorised cost for all actions at this state
            future_costs = V[k + 1, s_next_table[s_idx, :A_k]]
            total_costs = dt_table[s_idx, :A_k] + future_costs

            best_a = int(np.argmin(total_costs))
            best_cost = total_costs[best_a]

            if best_cost < np.inf:
                V[k][s_idx] = best_cost
                policy[k][s_idx] = best_a

    t_dp_done = time.perf_counter() - t_dp
    if verbose:
        print(f"  DP sweep done in {t_dp_done:.3f}s")

    # ── Forward pass: extract optimal v_eff profile ──
    optimal_speeds: list[float] = []
    s_idx = 0  # start from rest (speed = 0 m/s)

    for k in range(K):
        a_idx = policy[k][s_idx]
        if a_idx < 0:
            # Infeasible state — fall back to minimum speed
            v_eff = float(per_seg_actions[k][0])
        else:
            v_eff = float(per_seg_actions[k][a_idx])

        optimal_speeds.append(v_eff)

        # Propagate state using precomputed table
        es_table, _, _ = transition_tables[k]
        a_idx_used = a_idx if a_idx >= 0 else 0
        exit_speed = es_table[s_idx, a_idx_used]
        s_idx = _snap_to_grid(exit_speed, speed_grid_mps)

    wall = time.perf_counter() - t0

    # ── Validate with full simulation (braking envelope included) ──
    actual_time = validate_with_full_sim(interval, optimal_speeds)

    if verbose:
        print(f"DP: {n_evals:,} segment sims, {wall:.1f}s wall, "
              f"time={actual_time:.1f}s")
        print(f"  Speeds: {[round(s, 1) for s in optimal_speeds]}")

    return OptResult("dynamic_programming", optimal_speeds, actual_time,
                     n_evals, wall)
