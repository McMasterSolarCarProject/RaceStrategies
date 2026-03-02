'''Plan for optimizer check:
optimizer is like a function of speed profile that outputs
the associated score
the final speed profile for an optimizer must be a local
minimum of this function


need:
- interval loader function
- run the optimizer
- neighbourhood evaluator
    +/- small delta in each dimension
    pairwise effects
    random bounded changes
- aggregate results over intervals

results to give:
- did it pass
- base time
- best neighbour time
- improvement of neighbour
- tolerance
- dimensions that affect results the most
- number of checks
- time elapsed

add to optimizer CLI

add to init
'''

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from ..database.fetch_route_intervals import fetch_route_intervals
from ..engine.interval_simulator import SSInterval
from .common import build_bounds
from .coarse_to_fine import coarse_to_fine_interval, simulate_interval_with_v_eff


@dataclass
class NeighbourhoodResult:
    passed: bool
    base_time: float
    best_neighbour_time: float
    improvement: float
    tolerance: float
    top_dims: list[tuple[int, float]]
    checks: int
    wall_time: float
    best_source: str


def load_intervals(
    route: str,
    db_path: str,
    max_nodes: int,
    max_intervals: int,
) -> list[SSInterval]:
    intervals = fetch_route_intervals(
        route,
        split_at_stops=True,
        max_nodes=max_nodes,
        db_path=db_path,
    )
    if isinstance(intervals, SSInterval):
        intervals = [intervals]
    if max_intervals > 0:
        intervals = intervals[:max_intervals]
    return intervals


def _clamp_profile(profile: np.ndarray, bounds: list[tuple[float, float]]) -> list[float]:
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    return np.clip(profile, lo, hi).tolist()


def _score(interval: SSInterval, speeds_kmph: list[float]) -> float:
    return simulate_interval_with_v_eff(interval, speeds_kmph)


def evaluate_neighbourhood(
    interval: SSInterval,
    base_profile: list[float],
    bounds: list[tuple[float, float]],
    *,
    delta: float,
    delta_bound: float,
    pairwise: int,
    random_samples: int,
    random_scale: float,
    tolerance: float,
    top_dims: int,
    seed: int,
) -> NeighbourhoodResult:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)

    base = np.array(base_profile, dtype=float)
    n_dims = len(base)
    base_time = _score(interval, base.tolist())
    best_time = base_time
    best_source = "base"
    checks = 0
    dim_effect = np.zeros(n_dims, dtype=float)
    offset_levels = np.arange(delta, delta_bound + delta * 0.5, delta)
    offsets = np.concatenate((-offset_levels[::-1], offset_levels))

    def try_candidate(candidate: np.ndarray, source: str) -> None:
        nonlocal best_time, best_source, checks
        trial = _clamp_profile(candidate, bounds)
        trial_time = _score(interval, trial)
        checks += 1
        if trial_time < best_time:
            best_time = trial_time
            best_source = source
        return trial_time

    for i in range(n_dims):
        for offset in offsets:
            cand = base.copy()
            cand[i] += offset
            t = try_candidate(cand, f"coord[{i + 1}] {offset:+.2f}")
            dim_effect[i] = max(dim_effect[i], abs(t - base_time))

    all_pairs = list(combinations(range(n_dims), 2))
    if pairwise > 0 and all_pairs:
        if pairwise < len(all_pairs):
            selected_idx = rng.choice(len(all_pairs), size=pairwise, replace=False)
            selected_pairs = [all_pairs[int(i)] for i in selected_idx]
        else:
            selected_pairs = all_pairs
        for i, j in selected_pairs:
            for di in offsets:
                for dj in offsets:
                    cand = base.copy()
                    cand[i] += di
                    cand[j] += dj
                    try_candidate(cand, f"pair[{i + 1},{j + 1}] ({di:+.2f},{dj:+.2f})")

    for _ in range(max(0, random_samples)):
        step = rng.uniform(-delta_bound, delta_bound, size=n_dims) * random_scale
        cand = base + step
        try_candidate(cand, "random")

    elapsed = time.perf_counter() - t0
    improvement = base_time - best_time
    passed = improvement <= tolerance
    order = np.argsort(dim_effect)[::-1]
    top = [(int(i + 1), float(dim_effect[i])) for i in order[: max(1, top_dims)]]

    return NeighbourhoodResult(
        passed=passed,
        base_time=float(base_time),
        best_neighbour_time=float(best_time),
        improvement=float(improvement),
        tolerance=float(tolerance),
        top_dims=top,
        checks=checks,
        wall_time=elapsed,
        best_source=best_source,
    )


def run_interval_validation(interval: SSInterval, args: argparse.Namespace) -> NeighbourhoodResult:
    t0 = time.perf_counter()
    speeds, _, _ = coarse_to_fine_interval(
        interval,
        v_min_kmph=args.v_min,
        v_max_kmph=args.v_max,
        passes=args.passes,
    )
    optimizer_wall = time.perf_counter() - t0

    bounds = build_bounds(interval, args.v_min, args.v_max)
    result = evaluate_neighbourhood(
        interval,
        speeds,
        bounds,
        delta=args.delta,
        delta_bound=args.delta_bound,
        pairwise=args.pairwise,
        random_samples=args.random_samples,
        random_scale=args.random_scale,
        tolerance=args.tolerance,
        top_dims=args.top_dims,
        seed=args.seed + 17,
    )
    result.wall_time += optimizer_wall
    return result


def print_interval_report(i: int, r: NeighbourhoodResult) -> None:
    top = ", ".join(f"{idx}:{eff:.2f}s" for idx, eff in r.top_dims)
    status = "PASS" if r.passed else "FAIL"
    print(
        f"[{i:02d}] {status} | base={r.base_time:.2f}s | bestN={r.best_neighbour_time:.2f}s "
        f"| gain={r.improvement:.3f}s | tol={r.tolerance:.3f}s | checks={r.checks} "
        f"| elapsed={r.wall_time:.2f}s | via={r.best_source}"
    )
    print(f"     top_dims: {top}")


def print_route_summary(results: list[NeighbourhoodResult]) -> None:
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_gain = sum(r.improvement for r in results) / max(1, total)
    max_gain = max((r.improvement for r in results), default=0.0)
    total_checks = sum(r.checks for r in results)
    total_elapsed = sum(r.wall_time for r in results)
    print("\nRoute summary")
    print(f"  intervals: {total} | passed: {passed}/{total}")
    print(f"  avg_neighbour_gain: {avg_gain:.3f}s | worst_gain: {max_gain:.3f}s")
    print(f"  total_checks: {total_checks} | total_elapsed: {total_elapsed:.2f}s")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m src.optimizer.test_optimizer",
        description="Coarse-to-fine local-minimum validation over route intervals.",
    )
    p.add_argument("--route", default="A. Independence to Topeka")
    p.add_argument("--db", default="ASC_2024.sqlite")
    p.add_argument("--max-nodes", type=int, default=25)
    p.add_argument("--max-intervals", type=int, default=3)

    p.add_argument("--v-min", type=float, default=5.0)
    p.add_argument("--v-max", type=float, default=45.0)
    p.add_argument(
        "--passes",
        type=lambda s: [float(x.strip()) for x in s.split(",") if x.strip()],
        default=[10.0, 5.0, 2.0],
        help="Comma-separated coarse-to-fine step sizes, e.g. 10,5,2",
    )
    p.add_argument("--seed", type=int, default=42)

    p.add_argument(
        "--delta",
        "--delta-kmph",
        dest="delta",
        type=float,
        default=1.0,
        help="Perturbation step in km/h, e.g. 0.1.",
    )
    p.add_argument(
        "--delta-bound",
        "--delta-bound-kmph",
        dest="delta_bound",
        type=float,
        default=None,
        help="Maximum perturbation magnitude in km/h, e.g. 1.0 gives ±0.1, ±0.2, ... when step is 0.1.",
    )
    p.add_argument("--pairwise", type=int, default=12)
    p.add_argument("--random-samples", type=int, default=24)
    p.add_argument("--random-scale", type=float, default=1.0)
    p.add_argument("--tolerance", type=float, default=0.20)
    p.add_argument("--top-dims", type=int, default=5)
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.delta <= 0:
        raise SystemExit("--delta must be > 0")
    if args.delta_bound is None:
        args.delta_bound = args.delta
    if args.delta_bound <= 0:
        raise SystemExit("--delta-bound must be > 0")
    if args.delta_bound < args.delta:
        raise SystemExit("--delta-bound must be >= --delta")

    intervals = load_intervals(args.route, args.db, args.max_nodes, args.max_intervals)
    if not intervals:
        raise SystemExit("No intervals loaded; check --route, --db, or --max-nodes.")

    print(f"Loaded {len(intervals)} interval(s) from route: {args.route}")
    results: list[NeighbourhoodResult] = []
    for i, interval in enumerate(intervals, start=1):
        print(f"\nInterval {i}: {len(interval.segments)} segment(s)")
        res = run_interval_validation(interval, args)
        print_interval_report(i, res)
        results.append(res)

    print_route_summary(results)
    if any(not r.passed for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()