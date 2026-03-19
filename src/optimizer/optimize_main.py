from __future__ import annotations
import copy
import time
import numpy as np
from itertools import product

from ..database.fetch_route_intervals import fetch_route_intervals
from ..engine.interval_simulator import SSInterval, join_intervals
from ..engine.kinematics import Speed, Velocity
from ..engine.nodes import VelocityNode


def set_v_eff(interval: SSInterval, v_eff_kmph: list[float]) -> SSInterval:
    """
    Override v_eff and t_eff on every segment of a single SSInterval **in-place**.
    v_eff_kmph must have one entry per segment in the interval.
    """
    if len(v_eff_kmph) != len(interval.segments):
        raise ValueError(
            f"v_eff list length ({len(v_eff_kmph)}) != segments ({len(interval.segments)})"
        )

    for seg, v_kmph in zip(interval.segments, v_eff_kmph):
        target = min(v_kmph, seg.speed_limit.kmph) if seg.speed_limit.mps > 0 else v_kmph
        seg.v_eff = Velocity(seg.displacement.unit_vector(), Speed(kmph=target))

        vnode = VelocityNode(seg, Speed(kmph=target))
        if vnode.solve_velocity():
            seg.t_eff = vnode.torque
        else:
            seg.t_eff = 0

    return interval


def simulate_interval_with_v_eff(interval: SSInterval, v_eff_kmph: list[float]) -> float:
    """
    Deep-copy an interval, apply v_eff profile, simulate, return total time (seconds).
    """
    trial = copy.deepcopy(interval)
    set_v_eff(trial, v_eff_kmph)
    trial.simulate_interval()
    return trial.time_nodes[-1].time


def brute_force_interval(
    interval: SSInterval,
    bounds: list[tuple[float, float]],
    step: float,
) -> tuple[list[float], float]:
    """
    Brute-force search over all speed combos for a single SSInterval.

    Parameters
    ----------
    interval : SSInterval
        The interval to optimize.
    bounds : list[tuple[float, float]]
        Per-segment (min_kmph, max_kmph) bounds.
    step : float
        Step size in km/h for candidate generation.

    Returns
    -------
    (best_speeds, best_time, all_results)
        The best per-segment speeds, the resulting time, and a list of
        all (combo, time) pairs tested.
    """
    # Build per-segment candidate lists (clamped to speed limits)
    per_segment_candidates = []
    for i, (lo, hi) in enumerate(bounds):
        limit = interval.segments[i].speed_limit.kmph
        if limit > 0:
            hi = min(hi, limit)
            lo = min(lo, hi)
        candidates = list(np.arange(lo, hi + step * 0.5, step))
        if not candidates:
            candidates = [lo]
        per_segment_candidates.append(candidates)

    total_combos = 1
    for c in per_segment_candidates:
        total_combos *= len(c)

    print(f"  Segments: {len(interval.segments)}, Step: {step} km/h, Total combos: {total_combos:,}")

    best_time = float("inf")
    best_speeds = None
    checked = 0
    all_results: list[tuple[list[float], float]] = []

    for combo in product(*per_segment_candidates):
        combo_list = list(combo)
        t = simulate_interval_with_v_eff(interval, combo_list)
        all_results.append((combo_list, t))
        if t < best_time:
            best_time = t
            best_speeds = combo_list
        checked += 1
        if checked % 500 == 0:
            print(f"    Checked {checked:,}/{total_combos:,} | Best time so far: {best_time:.1f}s")

    print(f"    Done. Best time: {best_time:.1f}s | Speeds: {[round(s, 1) for s in best_speeds]}")
    return best_speeds, best_time, all_results


def coarse_to_fine_interval(
    interval: SSInterval,
    v_min_kmph: float = 20,
    v_max_kmph: float = 100,
    passes: list[float] | None = None,
) -> tuple[list[float], float]:
    """
    Coarse-to-fine brute force on a single SSInterval.

    Each pass does a full brute-force sweep at the given step size,
    then narrows bounds around the best result for the next pass.

    Parameters
    ----------
    interval : SSInterval
        The interval to optimize.
    v_min_kmph : float
        Global lower speed bound (km/h).
    v_max_kmph : float
        Global upper speed bound (km/h).
    passes : list[float]
        Step sizes for each refinement pass (coarse -> fine).
        e.g. [10, 5, 2] means 10 km/h step first, then 5, then 2.

    Returns
    -------
    (best_speeds, best_time, all_pass_results)
        all_pass_results is a list (one per pass) of lists of (combo, time) tuples.
    """
    if passes is None:
        passes = [10, 5, 2]

    n_segments = len(interval.segments)
    # Initial bounds: same range for every segment
    bounds = [(v_min_kmph, v_max_kmph)] * n_segments

    best_speeds = None
    best_time = float("inf")
    all_pass_results: list[list[tuple[list[float], float]]] = []

    for pass_idx, step in enumerate(passes):
        print(f"\n{'='*50}")
        print(f"Pass {pass_idx + 1}/{len(passes)} — step {step} km/h")
        print(f"Bounds: {[(round(lo, 1), round(hi, 1)) for lo, hi in bounds]}")

        best_speeds, best_time, results = brute_force_interval(interval, bounds, step)
        all_pass_results.append(results)

        # Narrow bounds: best_speed +/- current step, clamped to global range
        bounds = [
            (max(v_min_kmph, spd - step), min(v_max_kmph, spd + step))
            for spd in best_speeds
        ]

    return best_speeds, best_time, all_pass_results


def print_all_results(all_pass_results: list[list[tuple[list[float], float]]]):
    """Print every combo and its time for each pass, sorted by time."""
    for pass_idx, results in enumerate(all_pass_results):
        print(f"\n{'='*50}")
        print(f"Pass {pass_idx + 1}: {len(results)} combos")
        print(f"{'='*50}")
        sorted_results = sorted(results, key=lambda x: x[1])
        for rank, (speeds, t) in enumerate(sorted_results, 1):
            marker = " <-- BEST" if rank == 1 else ""
            print(f"  #{rank:>4d}  time={t:>8.1f}s  speeds={[round(s, 1) for s in speeds]}{marker}")


def optimize_route(
    placemark_name: str = "A. Independence to Topeka",
    db_path: str = "ASC_2024.sqlite",
    max_nodes: int = None,
    v_min_kmph: float = 20,
    v_max_kmph: float = 100,
    passes: list[float] | None = None,
    verbose: bool = True,
) -> dict:
    """
    Coarse-to-fine brute-force optimizer for a full route.
    Optimizes each SSInterval independently, then joins results.

    Returns
    -------
    dict with "best_profile", "best_times", "total_time", "master"
    """
    if passes is None:
        passes = [10, 5, 2]

    start = time.perf_counter()

    intervals = fetch_route_intervals(
        placemark_name, split_at_stops=True, max_nodes=max_nodes, db_path=db_path
    )
    if isinstance(intervals, SSInterval):
        intervals = [intervals]

    print(f"Route '{placemark_name}': {len(intervals)} intervals")
    print(f"Speed range: {v_min_kmph}–{v_max_kmph} km/h")
    print(f"Passes (step sizes): {passes}")

    all_best_speeds = []
    all_best_times = []

    for i, interval in enumerate(intervals):
        print(f"\n{'#'*60}")
        print(f"Interval {i + 1}/{len(intervals)}  ({len(interval.segments)} segments)")
        print(f"{'#'*60}")

        best_speeds, best_time, pass_results = coarse_to_fine_interval(
            interval,
            v_min_kmph=v_min_kmph,
            v_max_kmph=v_max_kmph,
            passes=passes,
        )
        all_best_speeds.append(best_speeds)
        all_best_times.append(best_time)

        # Print all iterations for this interval
        if verbose:
            print_all_results(pass_results)

        if i == 5:
            break 

    # Rebuild final simulation with optimal speeds
    optimized_intervals = []
    for interval, speeds in zip(intervals, all_best_speeds):
        trial = copy.deepcopy(interval)
        set_v_eff(trial, speeds)
        trial.simulate_interval()
        optimized_intervals.append(trial)

    master = join_intervals(optimized_intervals)
    total_time = master.time_nodes[-1].time

    elapsed = time.perf_counter() - start
    if verbose:
        print(f"\n{'='*60}")
        print(f"Optimization complete in {elapsed:.1f}s")
        print(f"Total route time: {total_time:.1f}s ({total_time / 3600:.2f}h)")
        for i, (speeds, t) in enumerate(zip(all_best_speeds, all_best_times)):
            print(f"  Interval {i+1}: {t:.1f}s | speeds: {[round(s, 1) for s in speeds]}")

    return {
        "best_profile": all_best_speeds,
        "best_times": all_best_times,
        "total_time": total_time,
        "master": master,
    }


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    result = optimize_route(
        placemark_name="A. Independence to Topeka",
        max_nodes=20,
        v_min_kmph=5,
        v_max_kmph=45,
        passes=[10, 5, 2],
        verbose=True,
    )

    if result["master"]:
        result["master"].plot(
            "dist", ["speed.kmph", "segment.v_eff.kmph"],
            f"optimized_{result['total_time']:.0f}s",
            brake=False,
        )
        plt.show()
