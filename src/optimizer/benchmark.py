"""
Benchmark harness and full-route optimizer.

Compares all optimizer implementations head-to-head on the same
interval, and provides a route-level optimizer that applies any
method across all stop-to-stop intervals.
"""
from __future__ import annotations

import copy
import time

from ..engine.interval_simulator import SSInterval, join_intervals
from .common import OptResult, validate_with_full_sim
from .coarse_to_fine import set_v_eff
from .optimize_de import optimize_de
from .optimize_slsqp import optimize_slsqp
from .optimize_ga import optimize_ga
from .optimize_dp import optimize_dp


# ═══════════════════════════════════════════════════════════════
#  Benchmark
# ═══════════════════════════════════════════════════════════════

def benchmark_interval(
    interval: SSInterval,
    v_min: float = 20.0,
    v_max: float = 100.0,
    methods: list[str] | None = None,
    verbose: bool = True,
) -> dict[str, OptResult]:
    """
    Run selected optimizers on a single interval and compare results.

    Parameters
    ----------
    methods : list[str] | None
        Which methods to run.  Defaults to ``["de", "slsqp", "ga", "dp"]``.
        Options: ``"coarse_to_fine"``, ``"de"``, ``"slsqp"``, ``"ga"``, ``"dp"``.
        Note: ``"coarse_to_fine"`` is O(A^K) — skip for >5 segments.

    Returns a dict mapping method name → OptResult.
    """
    if methods is None:
        # Skip brute force by default — it's exponential
        n_segs = len(interval.segments)
        methods = ["de", "slsqp", "ga", "dp"]
        if n_segs <= 5:
            methods.insert(0, "coarse_to_fine")
        elif verbose:
            print(f"Skipping coarse_to_fine (exponential with {n_segs} segments)")

    results: dict[str, OptResult] = {}

    if "coarse_to_fine" in methods:
        from .coarse_to_fine import coarse_to_fine_interval
        if verbose:
            print(f"\n{'='*60}")
            print("BENCHMARK: Coarse-to-Fine Brute Force")
            print(f"{'='*60}")
        t0 = time.perf_counter()
        bf_speeds, bf_time, bf_passes = coarse_to_fine_interval(
            interval, v_min, v_max, passes=[10, 5, 2]
        )
        bf_wall = time.perf_counter() - t0
        bf_evals = sum(len(p) for p in bf_passes)
        actual_bf = validate_with_full_sim(interval, bf_speeds)
        results["coarse_to_fine"] = OptResult(
            "coarse_to_fine", bf_speeds, actual_bf, bf_evals, bf_wall
        )

    if "de" in methods:
        if verbose:
            print(f"\n{'='*60}")
            print("BENCHMARK: Differential Evolution")
            print(f"{'='*60}")
        results["de"] = optimize_de(interval, v_min, v_max, verbose=verbose)

    if "slsqp" in methods:
        if verbose:
            print(f"\n{'='*60}")
            print("BENCHMARK: SLSQP Multi-Start")
            print(f"{'='*60}")
        results["slsqp"] = optimize_slsqp(interval, v_min, v_max, verbose=verbose)

    if "ga" in methods:
        if verbose:
            print(f"\n{'='*60}")
            print("BENCHMARK: Genetic Algorithm + Local Search")
            print(f"{'='*60}")
        results["ga"] = optimize_ga(interval, v_min, v_max, verbose=verbose)

    if "dp" in methods:
        if verbose:
            print(f"\n{'='*60}")
            print("BENCHMARK: Dynamic Programming")
            print(f"{'='*60}")
        results["dp"] = optimize_dp(interval, v_min, v_max, verbose=verbose)

    # ── Summary table ──
    if verbose:
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")
        header = f"{'Method':<25} {'Time (s)':>10} {'Evals':>10} {'Wall (s)':>10}"
        print(header)
        print("-" * len(header))
        for r in sorted(results.values(), key=lambda r: r.total_time):
            print(f"{r.method:<25} {r.total_time:>10.1f} "
                  f"{r.n_evals:>10,} {r.wall_time:>10.1f}")

    return results


# ═══════════════════════════════════════════════════════════════
#  Full route optimiser
# ═══════════════════════════════════════════════════════════════

def optimize_route(
    placemark_name: str = "A. Independence to Topeka",
    db_path: str = "ASC_2024.sqlite",
    max_nodes: int | None = None,
    v_min: float = 20.0,
    v_max: float = 100.0,
    method: str = "de",
    verbose: bool = True,
) -> dict:
    """
    Optimise a full route (all stop-to-stop intervals) using *method*.

    Parameters
    ----------
    method : str
        ``"de"`` | ``"slsqp"`` | ``"ga"`` | ``"dp"`` | ``"coarse_to_fine"``

    Returns
    -------
    dict  with keys ``best_profile``, ``best_times``, ``total_time``, ``master``.
    """
    from ..database.fetch_route_intervals import fetch_route_intervals

    METHODS = {
        "de": optimize_de,
        "slsqp": optimize_slsqp,
        "ga": optimize_ga,
        "dp": optimize_dp,
    }

    start = time.perf_counter()
    intervals = fetch_route_intervals(
        placemark_name, split_at_stops=True,
        max_nodes=max_nodes, db_path=db_path,
    )
    if isinstance(intervals, SSInterval):
        intervals = [intervals]

    if verbose:
        print(f"Route '{placemark_name}': {len(intervals)} intervals")
        print(f"Method: {method},  Speed range: {v_min}–{v_max} km/h")

    all_speeds: list[list[float]] = []
    all_times: list[float] = []

    for i, interval in enumerate(intervals):
        if verbose:
            print(f"\n{'#'*60}")
            print(f"Interval {i + 1}/{len(intervals)}  "
                  f"({len(interval.segments)} segments)")
            print(f"{'#'*60}")

        if method in METHODS:
            result = METHODS[method](interval, v_min, v_max, verbose=verbose)
            all_speeds.append(result.speeds_kmph)
            all_times.append(result.total_time)
        elif method == "coarse_to_fine":
            from .coarse_to_fine import coarse_to_fine_interval
            speeds, t, _ = coarse_to_fine_interval(interval, v_min, v_max)
            all_speeds.append(speeds)
            all_times.append(t)
        else:
            raise ValueError(f"Unknown method '{method}'. "
                             f"Choose from: {list(METHODS) + ['coarse_to_fine']}")

    # Rebuild optimised simulation
    optimised: list[SSInterval] = []
    for interval, speeds in zip(intervals, all_speeds):
        trial = copy.deepcopy(interval)
        set_v_eff(trial, speeds)
        trial.simulate_interval()
        optimised.append(trial)

    master = join_intervals(optimised)
    total = master.time_nodes[-1].time
    elapsed = time.perf_counter() - start

    if verbose:
        print(f"\n{'='*60}")
        print(f"Route optimisation complete in {elapsed:.1f}s")
        print(f"Total time: {total:.1f}s ({total / 3600:.2f}h)")
        for i, (spd, t) in enumerate(zip(all_speeds, all_times)):
            print(f"  Interval {i+1}: {t:.1f}s | "
                  f"speeds={[round(s, 1) for s in spd]}")

    return {
        "best_profile": all_speeds,
        "best_times": all_times,
        "total_time": total,
        "master": master,
    }
