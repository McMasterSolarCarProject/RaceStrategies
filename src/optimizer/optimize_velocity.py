from __future__ import annotations
import copy
import time
import numpy as np

from ..database.fetch_route_intervals import fetch_route_intervals
from ..engine.interval_simulator import SSInterval, join_intervals
from ..engine.kinematics import Speed, Velocity
from ..engine.nodes import Segment, VelocityNode


def set_v_eff(intervals: list[SSInterval], v_eff_kmph: float | list[float]) -> list[SSInterval]:
    """
    Override v_eff (and corresponding t_eff) on every segment in a list of intervals.

    Parameters
    ----------
    intervals : list[SSInterval]
        The intervals whose segments will be modified **in-place**.
    v_eff_kmph : float | list[float]
        Either a single target speed (km/h) applied uniformly, or a list
        with one value per segment across all intervals.

    Returns
    -------
    list[SSInterval]
        The same interval objects (modified in-place) for convenience.
    """
    # Flatten all segments so we can index them
    all_segments: list[Segment] = []
    for interval in intervals:
        all_segments.extend(interval.segments)

    if isinstance(v_eff_kmph, (int, float)):
        v_eff_values = [v_eff_kmph] * len(all_segments)
    else:
        if len(v_eff_kmph) != len(all_segments):
            raise ValueError(
                f"v_eff_kmph list length ({len(v_eff_kmph)}) != total segments ({len(all_segments)})"
            )
        v_eff_values = v_eff_kmph

    for seg, v_kmph in zip(all_segments, v_eff_values):
        target = min(v_kmph, seg.speed_limit.kmph) if seg.speed_limit.mps > 0 else v_kmph
        seg.v_eff = Velocity(seg.displacement.unit_vector(), Speed(kmph=target))

        # Calculate the torque needed to maintain v_eff on this segment
        vnode = VelocityNode(seg, Speed(kmph=target))
        if vnode.solve_velocity():
            seg.t_eff = vnode.torque
        else:
            # Motor can't sustain this speed on this segment — use 0
            seg.t_eff = 0

    return intervals


def simulate_with_v_eff(
    intervals: list[SSInterval],
    v_eff_kmph: float | list[float],
    verbose: bool = False,
) -> tuple[SSInterval, float]:
    """
    Deep-copy the intervals, apply a v_eff profile, simulate, and return
    the joined master interval plus total simulated time.

    Returns
    -------
    (master_interval, total_time)
    """
    # Deep copy so the original intervals are untouched
    trial = copy.deepcopy(intervals)
    set_v_eff(trial, v_eff_kmph)

    for i, interval in enumerate(trial):
        interval.simulate_interval()
        if verbose:
            print(f"  Interval {i+1}/{len(trial)}  "
                  f"time={interval.time_nodes[-1].time:.1f}s")

    master = join_intervals(trial)
    total_time = master.time_nodes[-1].time
    return master, total_time


def optimize_route(
    placemark_name: str = "A. Independence to Topeka",
    db_path: str = "ASC_2024.sqlite",
    v_min_kmph: float = 20,
    v_max_kmph: float = 100,
    v_step_kmph: float = 5,
    max_nodes: int = None,
    verbose: bool = True,
) -> dict:
    """
    Optimise per-segment v_eff values across the route.

    Strategy
    --------
    1. Build a list of candidate speeds for each segment (v_min → min(v_max, speed_limit), stepped by v_step).
    2. Start with every segment at its speed limit (or v_max if lower) as the initial profile.
    3. Sweep each segment one at a time through its candidates while holding the others fixed,
       picking the speed that gives the lowest total route time (coordinate-descent style).
    4. Repeat for a number of passes until the profile converges.

    Parameters
    ----------
    placemark_name : str
        Route placemark to fetch from the database.
    db_path : str
        Path to the SQLite database.
    v_min_kmph / v_max_kmph / v_step_kmph : float
        Range and step size for each segment's v_eff candidates (km/h).
    verbose : bool
        Print progress information.

    Returns
    -------
    dict with keys:
        "best_profile" – list of per-segment v_eff values (km/h)
        "best_time"    – simulated route time (s)
        "best_master"  – the joined SSInterval for the best run
    """
    start = time.perf_counter()

    # ── Fetch intervals ──────────────────────────────────────────────
    intervals = fetch_route_intervals(
        placemark_name, split_at_stops=False, max_nodes=max_nodes, db_path=db_path
    )
    if isinstance(intervals, SSInterval):
        intervals = [intervals]

    # Flatten segment info to build per-segment candidate lists
    seg_speed_limits: list[float] = []
    for iv in intervals:
        for seg in iv.segments:
            seg_speed_limits.append(seg.speed_limit.kmph)

    n_segments = len(seg_speed_limits)

    # Per-segment candidate speeds (clamped to speed limit)
    def candidates_for(seg_idx: int) -> list[float]:
        limit = seg_speed_limits[seg_idx]
        upper = min(v_max_kmph, limit) if limit > 0 else v_max_kmph
        lower = min(v_min_kmph, upper)
        return list(np.arange(lower, upper + v_step_kmph, v_step_kmph))

    if verbose:
        print(f"Route '{placemark_name}': {len(intervals)} intervals, {n_segments} segments")
        print(f"Speed range per segment: {v_min_kmph}–{v_max_kmph} km/h, step {v_step_kmph} km/h")

    # ── Initial profile: use speed limit (or v_max) ──────────────────
    profile = [
        min(v_max_kmph, sl) if sl > 0 else v_max_kmph
        for sl in seg_speed_limits
    ]

    # Simulate initial profile
    best_master, best_time = simulate_with_v_eff(intervals, profile, verbose=False)
    if verbose:
        print(f"Initial profile time: {best_time:.1f}s ({best_time/3600:.2f}h)")

    # ── Coordinate-descent passes ────────────────────────────────────
    MAX_PASSES = 3
    for pass_num in range(1, MAX_PASSES + 1):
        improved = False
        if verbose:
            print(f"\n{'='*50}")
            print(f"Pass {pass_num}/{MAX_PASSES}")

        for seg_idx in range(n_segments):
            candidates = candidates_for(seg_idx)
            current_speed = profile[seg_idx]
            best_candidate = current_speed

            for v_candidate in candidates:
                if v_candidate == current_speed:
                    continue
                trial_profile = profile[:]
                trial_profile[seg_idx] = v_candidate
                _, trial_time = simulate_with_v_eff(intervals, trial_profile, verbose=False)

                if trial_time < best_time:
                    best_time = trial_time
                    best_candidate = v_candidate
                    improved = True

            if best_candidate != current_speed:
                profile[seg_idx] = best_candidate
                # Re-simulate with updated profile to get the master interval
                best_master, best_time = simulate_with_v_eff(intervals, profile, verbose=False)
                if verbose:
                    print(f"  Seg {seg_idx}: {current_speed:.1f} → {best_candidate:.1f} km/h  "
                          f"(time: {best_time:.1f}s)")

        if not improved:
            if verbose:
                print("  No improvement this pass — converged.")
            break

    elapsed = time.perf_counter() - start
    if verbose:
        print(f"\n{'='*50}")
        print(f"Optimised time: {best_time:.1f}s ({best_time/3600:.2f}h)")
        print(f"Optimization took {elapsed:.1f}s")

    return {
        "best_profile": profile,
        "best_time": best_time,
        "best_master": best_master,
    }


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    result = optimize_route(
        placemark_name="A. Independence to Topeka",
        v_min_kmph=20,
        v_max_kmph=40,
        v_step_kmph=5,
        max_nodes=50,
        verbose=True,
    )

    # Plot the per-segment v_eff profile
    profile = result["best_profile"]
    fig, ax = plt.subplots()
    ax.plot(range(len(profile)), profile, marker=".", markersize=2, linestyle="-", linewidth=0.5)
    ax.set_xlabel("Segment Index")
    ax.set_ylabel("v_eff (km/h)")
    ax.set_title("Optimised Per-Segment Target Speed")
    ax.grid(True)

    # Also plot the best run's velocity profile
    if result["best_master"]:
        result["best_master"].plot(
            "dist", ["speed.kmph", "segment.v_eff.kmph"], f"best_time_{result['best_time']:.0f}s", brake=False
        )

    plt.show()
