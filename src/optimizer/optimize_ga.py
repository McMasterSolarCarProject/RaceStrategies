"""
Genetic Algorithm + Local Search optimizer for solar car race strategy.

Inspired by Betancur et al. (2017) who found GA+LS to be the best
evolutionary approach for solar car race optimisation.

Key components:
  - BLX-α blend crossover (α=0.5)
  - Tournament selection (k=3)
  - Gaussian mutation
  - Elitism (top 2)
  - SLSQP local search polish on the GA winner
"""
from __future__ import annotations

import time
import numpy as np

from ..engine.interval_simulator import SSInterval
from ..engine.kinematics import Speed, Velocity
from .common import OptResult, build_bounds, validate_with_full_sim, LapStrategyResult
from .coarse_to_fine import simulate_interval_with_v_eff


def optimize_ga(
    interval: SSInterval,
    v_min: float = 20.0,
    v_max: float = 100.0,
    *,
    pop_size: int = 50,
    generations: int = 80,
    crossover_rate: float = 0.85,
    mutation_rate: float = 0.15,
    mutation_sigma: float = 5.0,
    tournament_k: int = 3,
    elitism: int = 2,
    local_search: bool = True,
    seed: int = 42,
    verbose: bool = True,
) -> OptResult:
    """
    Genetic Algorithm with optional Local Search refinement.

    Inspired by Betancur et al. (2017) who found GA+LS to be the
    best evolutionary approach for solar car race optimisation.

    Chromosome
        Real-valued vector of per-segment speeds (km/h).

    Selection
        Tournament selection with tournament size *tournament_k*.

    Crossover
        BLX-α blend crossover (α=0.5): offspring genes are sampled
        uniformly from [min(p1,p2) - α·d, max(p1,p2) + α·d] where
        d = |p1 - p2|.  This explores beyond the parents' range.

    Mutation
        Gaussian perturbation with σ = *mutation_sigma* km/h,
        clamped to per-segment bounds.

    Elitism
        Top *elitism* individuals survive unchanged to the next gen.

    Local Search
        After the GA finishes, the best individual is polished with
        scipy SLSQP (gradient-based, ~50-200 extra evaluations).
        This is the key insight from Betancur — the GA finds the
        right basin, the local search finds the precise optimum.

    Parameters
    ----------
    pop_size : int
        Population size per generation.
    generations : int
        Number of generations.
    crossover_rate : float
        Probability of crossover per pair.
    mutation_rate : float
        Probability of mutation per gene.
    mutation_sigma : float
        Standard deviation of Gaussian mutation (km/h).
    tournament_k : int
        Tournament selection size.
    elitism : int
        Number of best individuals preserved unchanged.
    local_search : bool
        Whether to polish the GA result with SLSQP.
    """
    from scipy.optimize import minimize

    bounds = build_bounds(interval, v_min, v_max)
    n_dims = len(bounds)
    lo_arr = np.array([b[0] for b in bounds])
    hi_arr = np.array([b[1] for b in bounds])
    rng = np.random.default_rng(seed)
    n_evals = 0

    def fitness(x: np.ndarray) -> float:
        nonlocal n_evals
        n_evals += 1
        return simulate_interval_with_v_eff(interval, list(x))

    # ── Initialise population ──
    population = rng.uniform(lo_arr, hi_arr, size=(pop_size, n_dims))
    fit = np.array([fitness(ind) for ind in population])

    t0 = time.perf_counter()
    best_idx = int(np.argmin(fit))
    best_ever = population[best_idx].copy()
    best_fit = fit[best_idx]

    if verbose:
        print(f"GA: {n_dims}D, pop={pop_size}, gen={generations}, "
              f"cx={crossover_rate}, mut={mutation_rate}, sigma={mutation_sigma}")
        print(f"  Gen 0: best={best_fit:.1f}s  mean={np.mean(fit):.1f}s")

    for gen in range(1, generations + 1):
        new_pop = []

        # ── Elitism: carry best individuals unchanged ──
        elite_indices = np.argsort(fit)[:elitism]
        for ei in elite_indices:
            new_pop.append(population[ei].copy())

        # ── Fill rest of population ──
        while len(new_pop) < pop_size:
            # Tournament selection — two parents
            p1 = _tournament_select(population, fit, tournament_k, rng)
            p2 = _tournament_select(population, fit, tournament_k, rng)

            # BLX-α crossover
            if rng.random() < crossover_rate:
                child = _blx_crossover(p1, p2, lo_arr, hi_arr, rng, alpha=0.5)
            else:
                child = p1.copy() if rng.random() < 0.5 else p2.copy()

            # Gaussian mutation
            for i in range(n_dims):
                if rng.random() < mutation_rate:
                    child[i] += rng.normal(0, mutation_sigma)
                    child[i] = np.clip(child[i], lo_arr[i], hi_arr[i])

            new_pop.append(child)

        population = np.array(new_pop[:pop_size])
        fit = np.array([fitness(ind) for ind in population])

        gen_best_idx = int(np.argmin(fit))
        if fit[gen_best_idx] < best_fit:
            best_fit = fit[gen_best_idx]
            best_ever = population[gen_best_idx].copy()

        if verbose and (gen % max(1, generations // 10) == 0 or gen == 1):
            print(f"  Gen {gen:>3d}: best={best_fit:.1f}s  "
                  f"gen_best={fit[gen_best_idx]:.1f}s  "
                  f"mean={np.mean(fit):.1f}s")

    # ── Local Search: polish with SLSQP ──
    ls_label = ""
    if local_search:
        if verbose:
            print("  Local search (SLSQP) from GA best …")
        ls_result = minimize(
            fitness, best_ever,
            method="SLSQP",
            bounds=bounds,
            options={"maxiter": 200, "ftol": 1e-4},
        )
        if ls_result.fun < best_fit:
            improvement = best_fit - ls_result.fun
            best_ever = ls_result.x.copy()
            best_fit = ls_result.fun
            ls_label = f"  (LS improved by {improvement:.2f}s)"

    wall = time.perf_counter() - t0
    speeds = list(best_ever)
    actual_time = validate_with_full_sim(interval, speeds)

    if verbose:
        print(f"GA+LS: {n_evals:,} evals, {wall:.1f}s wall, "
              f"time={actual_time:.1f}s{ls_label}")
        print(f"  Speeds: {[round(s, 1) for s in speeds]}")

    method_name = "ga+ls" if local_search else "ga"
    return OptResult(method_name, speeds, actual_time, n_evals, wall)


def _tournament_select(
    population: np.ndarray,
    fitness: np.ndarray,
    k: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Select one individual via tournament selection (minimisation)."""
    indices = rng.choice(len(population), size=k, replace=False)
    winner = indices[np.argmin(fitness[indices])]
    return population[winner].copy()


def _blx_crossover(
    p1: np.ndarray,
    p2: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    rng: np.random.Generator,
    alpha: float = 0.5,
) -> np.ndarray:
    """
    BLX-α blend crossover for real-valued chromosomes.

    Offspring genes are sampled from [min(p1,p2) - α·d, max(p1,p2) + α·d]
    where d = |p1 - p2|.  With α=0.5, this is the standard BLX-0.5 which
    has been shown to maintain good diversity.
    """
    d = np.abs(p1 - p2)
    lower = np.minimum(p1, p2) - alpha * d
    upper = np.maximum(p1, p2) + alpha * d
    child = rng.uniform(lower, upper)
    return np.clip(child, lo, hi)


def optimize_ga_lap_strategy(
    start_interval: SSInterval,
    middle_interval: SSInterval,
    end_interval: SSInterval,
    num_middle_laps: int,
    v_min: float = 20.0,
    v_max: float = 100.0,
    *,
    pop_size: int = 50,
    generations: int = 80,
    crossover_rate: float = 0.85,
    mutation_rate: float = 0.15,
    mutation_sigma: float = 5.0,
    tournament_k: int = 3,
    elitism: int = 2,
    local_search: bool = True,
    slsqp_maxiter: int = 200,
    slsqp_ftol: float = 1e-4,
    seed: int = 42,
    verbose: bool = True,
) -> tuple[OptResult, LapStrategyResult]:
    """
    Genetic Algorithm optimizer for 3-lap strategy (START → MIDDLE×n → END).

    Optimizes speed profiles for three lap phases with constrained entry/exit speeds.
    The middle lap is repeated n times, so its entry and exit speeds must match.

    Parameters
    ----------
    start_interval : SSInterval
        First lap (full battery tactics).
    middle_interval : SSInterval
        Repeatable middle lap (fills most of race time).
    end_interval : SSInterval
        Final lap (manage remaining energy).
    num_middle_laps : int
        Number of times the middle lap is repeated.
    v_min, v_max : float
        Speed bounds (km/h).
    pop_size, generations, etc. : see optimize_ga()

    Returns
    -------
    (OptResult, LapStrategyResult)
        GA result with combined speeds, and lap strategy breakdown.
    """
    from scipy.optimize import minimize
    import copy

    # Build bounds for each interval
    bounds_start = build_bounds(start_interval, v_min, v_max)
    bounds_middle = build_bounds(middle_interval, v_min, v_max)
    bounds_end = build_bounds(end_interval, v_min, v_max)

    n_start = len(bounds_start)
    n_middle = len(bounds_middle)
    n_end = len(bounds_end)
    n_dims = n_start + n_middle + n_end

    lo_arr = np.array([b[0] for b in bounds_start + bounds_middle + bounds_end])
    hi_arr = np.array([b[1] for b in bounds_start + bounds_middle + bounds_end])

    rng = np.random.default_rng(seed)
    n_evals = 0

    def fitness(x: np.ndarray) -> float:
        """Fitness: total time across all three lap phases."""
        nonlocal n_evals
        n_evals += 1

        speeds_start = list(x[:n_start])
        speeds_middle = list(x[n_start : n_start + n_middle])
        speeds_end = list(x[n_start + n_middle :])

        # Simulate with entry speed constraints
        return _simulate_lap_sequence(
            start_interval, middle_interval, end_interval,
            speeds_start, speeds_middle, speeds_end,
            num_middle_laps
        )

    # ── Initialise population ──
    population = rng.uniform(lo_arr, hi_arr, size=(pop_size, n_dims))
    fit = np.array([fitness(ind) for ind in population])

    t0 = time.perf_counter()
    best_idx = int(np.argmin(fit))
    best_ever = population[best_idx].copy()
    best_fit = fit[best_idx]

    if verbose:
        print(f"GA (Lap Strategy): {n_dims}D ({n_start}+{n_middle}+{n_end}), "
              f"pop={pop_size}, gen={generations}, "
              f"middle_laps={num_middle_laps}")
        print(f"  Gen 0: best={best_fit:.1f}s  mean={np.mean(fit):.1f}s")

    for gen in range(1, generations + 1):
        new_pop = []

        # ── Elitism ──
        elite_indices = np.argsort(fit)[:elitism]
        for ei in elite_indices:
            new_pop.append(population[ei].copy())

        # ── Fill rest of population ──
        while len(new_pop) < pop_size:
            p1 = _tournament_select(population, fit, tournament_k, rng)
            p2 = _tournament_select(population, fit, tournament_k, rng)

            if rng.random() < crossover_rate:
                child = _blx_crossover(p1, p2, lo_arr, hi_arr, rng, alpha=0.5)
            else:
                child = p1.copy() if rng.random() < 0.5 else p2.copy()

            for i in range(n_dims):
                if rng.random() < mutation_rate:
                    child[i] += rng.normal(0, mutation_sigma)
                    child[i] = np.clip(child[i], lo_arr[i], hi_arr[i])

            new_pop.append(child)

        population = np.array(new_pop[:pop_size])
        fit = np.array([fitness(ind) for ind in population])

        gen_best_idx = int(np.argmin(fit))
        if fit[gen_best_idx] < best_fit:
            best_fit = fit[gen_best_idx]
            best_ever = population[gen_best_idx].copy()

        if verbose and (gen % max(1, generations // 10) == 0 or gen == 1):
            print(f"  Gen {gen:>3d}: best={best_fit:.1f}s  "
                  f"gen_best={fit[gen_best_idx]:.1f}s  "
                  f"mean={np.mean(fit):.1f}s")

    # ── Local Search ──
    ls_label = ""
    if local_search:
        if verbose:
            print("  Local search (SLSQP) from GA best …")
        ls_result = minimize(
            fitness, best_ever,
            method="SLSQP",
            bounds=list(zip(lo_arr, hi_arr)),
            options={"maxiter": slsqp_maxiter, "ftol": slsqp_ftol},
        )
        if ls_result.fun < best_fit:
            improvement = best_fit - ls_result.fun
            best_ever = ls_result.x.copy()
            best_fit = ls_result.fun
            ls_label = f"  (LS improved by {improvement:.2f}s)"

    wall = time.perf_counter() - t0

    # ── Build final result with proper speed profiles ──
    speeds_start = list(best_ever[:n_start])
    speeds_middle = list(best_ever[n_start : n_start + n_middle])
    speeds_end = list(best_ever[n_start + n_middle :])

    # Get actual times and build combined interval
    lap_result = _build_lap_strategy_result(
        start_interval, middle_interval, end_interval,
        speeds_start, speeds_middle, speeds_end,
        num_middle_laps, verbose=False
    )

    actual_time = lap_result.total_time
    all_speeds = speeds_start + (speeds_middle * num_middle_laps) + speeds_end

    if verbose:
        print(f"GA+LS: {n_evals:,} evals, {wall:.1f}s wall, "
              f"time={actual_time:.1f}s{ls_label}")
        print(f"  Start speeds: {[round(s, 1) for s in speeds_start]}")
        print(f"  Middle speeds: {[round(s, 1) for s in speeds_middle]} (×{num_middle_laps})")
        print(f"  End speeds: {[round(s, 1) for s in speeds_end]}")

    method_name = "ga+ls_lap" if local_search else "ga_lap"
    opt_result = OptResult(method_name, all_speeds, actual_time, n_evals, wall, lap_result)

    return opt_result, lap_result


def _simulate_lap_sequence(
    start_interval: SSInterval,
    middle_interval: SSInterval,
    end_interval: SSInterval,
    speeds_start: list[float],
    speeds_middle: list[float],
    speeds_end: list[float],
    num_middle_laps: int,
) -> float:
    """
    Simulate three-lap sequence with speed constraints.
    Returns total time across all laps.
    """
    lap_result = _build_lap_strategy_result(
        start_interval, middle_interval, end_interval,
        speeds_start, speeds_middle, speeds_end,
        num_middle_laps, verbose=False
    )
    return lap_result.total_time


def _build_lap_strategy_result(
    start_interval: SSInterval,
    middle_interval: SSInterval,
    end_interval: SSInterval,
    speeds_start: list[float],
    speeds_middle: list[float],
    speeds_end: list[float],
    num_middle_laps: int,
    verbose: bool = True,
) -> LapStrategyResult:
    """
    Simulate three-lap strategy with given speed profiles.
    Returns LapStrategyResult with combined interval and timing breakdown.
    """
    import copy
    from .coarse_to_fine import set_v_eff

    # Simulate start lap
    start_copy = copy.deepcopy(start_interval)
    set_v_eff(start_copy, speeds_start)
    start_copy.simulate_interval()
    time_start = start_copy.time_nodes[-1].time
    speed_at_start_exit = start_copy.time_nodes[-1].speed.kmph
    energy_start = 0  # Energy tracking not implemented on TimeNode

    # Simulate middle lap with entry speed from start
    middle_copy = copy.deepcopy(middle_interval)
    set_v_eff(middle_copy, speeds_middle)
    # Override entry speed to match start's exit
    middle_copy.startSpeed = Velocity(
        middle_copy.segments[0].unit_vector(),
        Speed(kmph=speed_at_start_exit)
    )
    middle_copy.simulate_interval()
    time_middle = middle_copy.time_nodes[-1].time
    speed_at_middle_exit = middle_copy.time_nodes[-1].speed.kmph
    energy_middle = 0  # Energy tracking not implemented on TimeNode

    # Simulate end lap with entry speed from middle
    end_copy = copy.deepcopy(end_interval)
    set_v_eff(end_copy, speeds_end)
    end_copy.startSpeed = Velocity(
        end_copy.segments[0].unit_vector(),
        Speed(kmph=speed_at_middle_exit)
    )
    end_copy.simulate_interval()
    time_end = end_copy.time_nodes[-1].time
    energy_end = 0  # Energy tracking not implemented on TimeNode

    # Build combined interval
    combined = copy.deepcopy(start_copy)
    for _ in range(num_middle_laps):
        middle_copy_for_combine = copy.deepcopy(middle_copy)
        combined += middle_copy_for_combine

    end_copy_for_combine = copy.deepcopy(end_copy)
    combined += end_copy_for_combine

    total_time = time_start + (num_middle_laps * time_middle) + time_end

    if verbose:
        print(f"  Start: {time_start:.1f}s ({energy_start:.0f}J)")
        print(f"  Middle: {time_middle:.1f}s ({energy_middle:.0f}J) × {num_middle_laps}")
        print(f"  End: {time_end:.1f}s ({energy_end:.0f}J)")
        print(f"  Total: {total_time:.1f}s")

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
