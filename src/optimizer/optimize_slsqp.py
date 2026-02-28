"""
SLSQP multi-start optimizer for solar car race strategy.

Uses scipy.optimize.minimize(method='SLSQP') — a gradient-based
constrained optimiser with numerical finite-difference gradients.
Multiple random restarts mitigate local optima.
"""
from __future__ import annotations

import time
import numpy as np

from ..engine.interval_simulator import SSInterval
from .common import OptResult, build_bounds, validate_with_full_sim
from .coarse_to_fine import simulate_interval_with_v_eff


def optimize_slsqp(
    interval: SSInterval,
    v_min: float = 20.0,
    v_max: float = 100.0,
    *,
    n_restarts: int = 5,
    seed: int = 42,
    verbose: bool = True,
) -> OptResult:
    """
    SLSQP — gradient-based constrained optimiser with multi-start.

    Uses numerical finite-difference gradients on the simulation.
    Fast convergence (~50–200 evals per start) but may find local optima;
    multiple random restarts mitigate this.
    """
    from scipy.optimize import minimize

    bounds = build_bounds(interval, v_min, v_max)
    n_evals = 0
    rng = np.random.default_rng(seed)

    def objective(x):
        nonlocal n_evals
        n_evals += 1
        return simulate_interval_with_v_eff(interval, list(x))

    t0 = time.perf_counter()
    best_result = None
    best_time = float("inf")

    for restart in range(n_restarts):
        x0 = np.array([rng.uniform(lo, hi) for lo, hi in bounds])
        result = minimize(
            objective, x0,
            method="SLSQP",
            bounds=bounds,
            options={"maxiter": 200, "ftol": 1e-4},
        )
        t = validate_with_full_sim(interval, list(result.x))
        if verbose:
            print(f"  SLSQP restart {restart + 1}/{n_restarts}: "
                  f"time={t:.1f}s  speeds={[round(s, 1) for s in result.x]}")
        if t < best_time:
            best_time = t
            best_result = result

    wall = time.perf_counter() - t0
    speeds = list(best_result.x)
    actual_time = validate_with_full_sim(interval, speeds)

    if verbose:
        print(f"SLSQP: {n_evals:,} evals, {wall:.1f}s wall, time={actual_time:.1f}s")

    return OptResult("slsqp_multistart", speeds, actual_time, n_evals, wall, best_result)
