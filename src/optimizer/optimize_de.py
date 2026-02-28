"""
Differential Evolution optimizer for solar car race strategy.

Uses scipy.optimize.differential_evolution as a global, population-based,
gradient-free optimizer.  Treats the full interval simulation as a
black-box f(v_eff_vector) → time.
"""
from __future__ import annotations

import time
import numpy as np

from ..engine.interval_simulator import SSInterval
from .common import OptResult, build_bounds, validate_with_full_sim
from .coarse_to_fine import simulate_interval_with_v_eff


def optimize_de(
    interval: SSInterval,
    v_min: float = 20.0,
    v_max: float = 100.0,
    *,
    maxiter: int = 100,
    seed: int = 42,
    tol: float = 0.01,
    popsize: int = 15,
    verbose: bool = True,
) -> OptResult:
    """
    Differential Evolution — global, population-based, gradient-free.

    Treats the full interval simulation as a black-box f(v_eff_vector) → time.
    Typically converges in 500–2 000 evaluations regardless of dimensionality.
    """
    from scipy.optimize import differential_evolution

    bounds = build_bounds(interval, v_min, v_max)
    n_evals = 0

    def objective(x):
        nonlocal n_evals
        n_evals += 1
        return simulate_interval_with_v_eff(interval, list(x))

    t0 = time.perf_counter()
    result = differential_evolution(
        objective,
        bounds=bounds,
        maxiter=maxiter,
        seed=seed,
        tol=tol,
        popsize=popsize,
        disp=verbose,
    )
    wall = time.perf_counter() - t0

    speeds = list(result.x)
    actual_time = validate_with_full_sim(interval, speeds)

    if verbose:
        print(f"DE: {n_evals:,} evals, {wall:.1f}s wall, time={actual_time:.1f}s")
        print(f"  Speeds: {[round(s, 1) for s in speeds]}")

    return OptResult("differential_evolution", speeds, actual_time, n_evals, wall, result)
