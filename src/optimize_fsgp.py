"""
Optimize FSGP Track by repeating the full course N times.

This script:
1. Initializes the FSGP database from KML
2. Repeats the entire course N times
3. Optimizes speed profiles using GA
4. Updates database with optimized target velocities and torques
5. Plots and displays results
"""
import time
import sys
import sqlite3
import copy
from pathlib import Path

from .database import init_route_db, fetch_route_intervals
from .database.parse_kml import parse_kml_file
from .engine.interval_simulator import SSInterval, join_intervals
from .optimizer.optimize_ga import optimize_ga, optimize_ga_lap_strategy
from .optimizer.coarse_to_fine import set_v_eff


def update_fsgp_database_with_optimized_speeds(
    track_name: str,
    lap_result,
    db_path: str = "FSGP_2024.sqlite",
    verbose: bool = True,
) -> None:
    """
    Update FSGP database with optimized target velocities and torques.
    
    Parameters
    ----------
    track_name : str
        Placemark name in KML (usually "FSGP_Track").
    lap_result : LapStrategyResult
        Result object from optimize_ga_lap_strategy containing optimized interval.
    db_path : str
        Path to SQLite database.
    verbose : bool
        Print diagnostics.
    """
    if verbose:
        print(f"\n[Database Update] Updating {db_path} with optimized speeds...")
    
    combined_interval = lap_result.combined_interval
    
    if not combined_interval.segments:
        if verbose:
            print("  Warning: No segments in combined interval. Skipping database update.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        update_count = 0
        for segment in combined_interval.segments:
            # Extract v_eff and t_eff from the segment
            v_eff_kmph = segment.v_eff.kmph if segment.v_eff else 0
            t_eff = segment.t_eff if segment.t_eff else 0
            
            # Update database
            cursor.execute(
                'UPDATE route_data SET speed = ?, torque = ? WHERE placemark_name = ? AND id = ?',
                (v_eff_kmph, t_eff, track_name, segment.id)
            )
            update_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if verbose:
            print(f"  Updated {update_count} segments in {track_name}")
    
    except sqlite3.Error as e:
        if verbose:
            print(f"  Error updating database: {e}")


def setup_fsgp_database(
    db_path: str = "FSGP_2024.sqlite",
    kml_path: str = "data/FSGP_Track.kml",
    remake: bool = False,
    verbose: bool = True,
) -> None:
    """Initialize FSGP database from KML file."""
    if verbose:
        print(f"[FSGP Setup] Initializing database from {kml_path}...")
    
    start = time.perf_counter()
    init_route_db(db_path=db_path, kml_path=kml_path, remake=remake)
    
    if verbose:
        print(f"  Database initialized in {time.perf_counter() - start:.2f}s")


def fetch_fsgp_sections(
    track_name: str = "FSGP_Track",
    db_path: str = "FSGP_2024.sqlite",
    start_node: int = 0,
    start_nodes: int = None,
    middle_nodes: int = None,
    end_nodes: int = None,
    verbose: bool = True,
) -> tuple[SSInterval, SSInterval, SSInterval]:
    """
    Fetch start, middle, and end sections from FSGP track.
    
    Parameters
    ----------
    track_name : str
        Placemark name in KML (usually "FSGP_Track").
    db_path : str
        Path to SQLite database.
    start_node : int
        Starting node index.
    start_nodes : int
        Number of nodes for start section (auto-calc if None).
    middle_nodes : int
        Number of nodes for middle section (auto-calc if None).
    end_nodes : int
        Number of nodes for end section (auto-calc if None).
    verbose : bool
        Print diagnostics.
    
    Returns
    -------
    (start_interval, middle_interval, end_interval)
        Three SSInterval objects.
    """
    # Fetch entire track
    full_track = fetch_route_intervals(
        track_name, 
        split_at_stops=False, 
        db_path=db_path
    )
    if isinstance(full_track, list):
        full_track = full_track[0]
    
    total_segments = len(full_track.segments)
    
    if verbose:
        print(f"[FSGP Sections] Total segments: {total_segments}")
    
    # Auto-calculate section sizes if not specified
    if start_nodes is None:
        start_nodes = max(1, total_segments // 6)  # ~17% for start
    if middle_nodes is None:
        middle_nodes = max(1, total_segments // 2)  # ~50% for middle
    if end_nodes is None:
        end_nodes = max(1, total_segments - start_nodes - middle_nodes)
    
    if verbose:
        print(f"[FSGP Sections] Dividing into: "
              f"start={start_nodes}, middle={middle_nodes}, end={end_nodes}")
    
    # Split into three sections
    start_segments = full_track.segments[start_node : start_node + start_nodes]
    middle_segments = full_track.segments[start_node + start_nodes : start_node + start_nodes + middle_nodes]
    end_segments = full_track.segments[start_node + start_nodes + middle_nodes : start_node + start_nodes + middle_nodes + end_nodes]
    
    if verbose:
        print(f"[FSGP Sections] Actual segment counts: "
              f"start={len(start_segments)}, middle={len(middle_segments)}, end={len(end_segments)}")
    
    start_interval = SSInterval(start_segments)
    middle_interval = SSInterval(middle_segments)
    end_interval = SSInterval(end_segments)
    
    return start_interval, middle_interval, end_interval


def optimize_fsgp_strategy(
    track_name: str = "FSGP_Track",
    db_path: str = "FSGP_2024.sqlite",
    num_laps: int = 3,
    v_min: float = 20.0,
    v_max: float = 100.0,
    pop_size: int = 50,
    generations: int = 80,
    local_search: bool = True,
    seed: int = 42,
    verbose: bool = True,
    plot_result: bool = True,
) -> tuple:
    """
    Optimize FSGP track by repeating full course N times.
    
    Parameters
    ----------
    track_name : str
        Placemark name in KML.
    db_path : str
        Path to SQLite database.
    num_laps : int
        Number of times to repeat the full course for baseline.
    v_min, v_max : float
        Speed bounds (km/h).
    pop_size, generations : int
        GA parameters.
    local_search : bool
        Whether to use SLSQP polishing.
    seed : int
        Random seed for reproducibility.
    verbose : bool
        Print diagnostics.
    plot_result : bool
        Generate plots.
    
    Returns
    -------
    (opt_result, lap_result)
        Optimization result and lap breakdown.
    """
    if verbose:
        print("\n" + "=" * 70)
        print(f"FSGP TRACK OPTIMIZATION ({num_laps}-Lap Course)")
        print("=" * 70)
    
    t0 = time.perf_counter()
    
    # Fetch full track
    full_track = fetch_route_intervals(
        track_name, 
        split_at_stops=False, 
        db_path=db_path
    )
    if isinstance(full_track, list):
        full_track = full_track[0]
    
    if verbose:
        print(f"\n[Track] Total segments: {len(full_track.segments)}")
        print(f"[Track] Total distance: {full_track.total_dist:.1f} m")
    
    # Create full course repeated N times
    combined_course = SSInterval(full_track.segments)
    for i in range(num_laps - 1):
        lap_copy = copy.deepcopy(full_track)
        combined_course += lap_copy
    
    if verbose:
        print(f"\n[Optimization] Starting GA optimization for {num_laps} laps...")
    
    # Optimize the entire course
    from .optimizer.optimize_ga import optimize_ga
    opt_result = optimize_ga(
        combined_course,
        v_min=v_min,
        v_max=v_max,
        pop_size=pop_size,
        generations=generations,
        local_search=local_search,
        seed=seed,
        verbose=verbose,
    )
    
    wall_time = time.perf_counter() - t0
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"OPTIMIZATION COMPLETE in {wall_time:.1f}s")
        print(f"{'='*70}")
        print(f"Total time: {opt_result.total_time:.1f}s ({opt_result.total_time/3600:.2f} hours)")
        print(f"Total distance: {combined_course.total_dist/1000:.2f} km")
        print(f"GA evaluations: {opt_result.n_evals:,}")
        print(f"Method: {opt_result.method}")
    
    # Plot results
    if plot_result:
        if verbose:
            print(f"\nGenerating plots...")
        try:
            import matplotlib.pyplot as plt
            
            # Plot 1: Distance vs velocity
            combined_course.plot(
                "dist", ["speed.kmph", "segment.v_eff.kmph"],
                f"fsgp_optimized_{num_laps}laps_distance"
            )
            
            # Plot 2: Time vs velocity
            combined_course.plot(
                "time", ["speed.kmph", "segment.v_eff.kmph"],
                f"fsgp_optimized_{num_laps}laps_time"
            )
            
            if verbose:
                print(f"  Displaying plots...")
            plt.show()
        except Exception as e:
            if verbose:
                print(f"  Warning: Could not generate plots: {e}")
    
    return opt_result, combined_course


def extract_middle_lap(
    full_track: SSInterval,
    combined_course: SSInterval,
    num_laps: int = 3,
    verbose: bool = True,
) -> SSInterval:
    """
    Extract the middle lap from an N-lap optimized course.
    
    For a 3-lap course: START + MIDDLE + END, extract just the MIDDLE lap.
    
    Parameters
    ----------
    full_track : SSInterval
        The single-lap track.
    combined_course : SSInterval
        The optimized N-lap combined course.
    num_laps : int
        Number of laps in combined_course.
    verbose : bool
        Print diagnostics.
    
    Returns
    -------
    SSInterval
        The middle lap segments from the combined course.
    """
    single_lap_segments = len(full_track.segments)
    total_segments = len(combined_course.segments)
    
    if verbose:
        print(f"[Middle Lap] Single lap segments: {single_lap_segments}")
        print(f"[Middle Lap] Total combined segments: {total_segments}")
    
    if num_laps != 3:
        if verbose:
            print(f"[Middle Lap] Warning: Extraction designed for 3 laps, got {num_laps}")
    
    # For 3 laps: segments 0 to n = START, n to 2n = MIDDLE, 2n to 3n = END
    middle_start = single_lap_segments
    middle_end = 2 * single_lap_segments
    
    # Bounds check
    if middle_end > total_segments:
        if verbose:
            print(f"[Middle Lap] Warning: Not enough segments. Expected >= {middle_end}, got {total_segments}")
        # Fallback: use middle third
        third = total_segments // 3
        middle_start = third
        middle_end = 2 * third
    
    middle_segments = combined_course.segments[middle_start : middle_end]
    
    if not middle_segments:
        if verbose:
            print(f"[Middle Lap] Error: No segments extracted ({middle_start}:{middle_end})")
        # Fallback: use middle lap by distance
        total_dist = combined_course.total_dist
        target_start = total_dist / 3
        target_end = 2 * total_dist / 3
        
        accumulated_dist = 0
        middle_segments = []
        for seg in combined_course.segments:
            accumulated_dist += seg.dist
            if target_start <= accumulated_dist <= target_end:
                middle_segments.append(seg)
            elif accumulated_dist > target_end:
                break
    
    middle_lap = SSInterval(middle_segments)
    
    if verbose:
        print(f"[Middle Lap] Extracted {len(middle_segments)} segments")
        print(f"[Middle Lap] Distance: {middle_lap.total_dist:.1f} m")
        sim_result = middle_lap.simulate()
        print(f"[Middle Lap] Time: {sim_result.sim_time:.1f} s")
    
    return middle_lap


def analyze_lap_repetitions(
    full_track: SSInterval,
    combined_course: SSInterval,
    num_baseline_laps: int = 3,
    time_budget: float = None,
    verbose: bool = True,
) -> dict:
    """
    Analyze how many middle laps can fit in the time budget.
    
    Given a 3-lap baseline optimization, extract the start/middle/end segments
    and calculate how many complete middle laps fit in the total time.
    
    Parameters
    ----------
    full_track : SSInterval
        Single-lap track.
    combined_course : SSInterval
        Optimized multi-lap course (currently just treated as 3 laps).
    num_baseline_laps : int
        Number of laps in the baseline optimization (default 3).
    time_budget : float
        Total time budget in seconds. If None, uses combined_course total time.
    verbose : bool
        Print diagnostics.
    
    Returns
    -------
    dict
        Analysis results including:
        - total_time: Budget or optimized time
        - start_time, middle_time, end_time: Individual segment times
        - available_time_for_middle: Time available for repeating middle
        - num_complete_middle_laps: How many full middle laps fit
        - num_total_laps: Start + middle*n + end
        - middle_lap: The extracted SSInterval for the middle section
    """
    # Extract middle lap
    middle_lap = extract_middle_lap(
        full_track, combined_course, 
        num_laps=num_baseline_laps, 
        verbose=verbose
    )
    
    # Simulate baseline 3 laps to get individual times
    single_lap_segments = len(full_track.segments)
    
    # Start segment: first lap (indices 0 to n)
    start_segments = combined_course.segments[0 : single_lap_segments]
    start_lap = SSInterval(start_segments)
    start_result = start_lap.simulate()
    start_time = start_result.sim_time
    
    # End segment: last lap (indices 2n to 3n)
    end_start_idx = 2 * single_lap_segments
    end_segments = combined_course.segments[end_start_idx :]
    end_lap = SSInterval(end_segments)
    end_result = end_lap.simulate()
    end_time = end_result.sim_time
    
    # Middle lap: already extracted
    middle_result = middle_lap.simulate()
    middle_time = middle_result.sim_time
    
    # Time budget
    if time_budget is None:
        total_time = combined_course.simulate().sim_time
    else:
        total_time = time_budget
    
    # Calculate how many middle laps fit
    available_for_middle = total_time - start_time - end_time
    num_complete_middle = max(0, int(available_for_middle / middle_time))
    num_total_laps = 1 + num_complete_middle + 1  # start + middle*n + end
    
    result = {
        'total_time': total_time,
        'start_time': start_time,
        'middle_time': middle_time,
        'end_time': end_time,
        'available_time_for_middle': available_for_middle,
        'num_complete_middle_laps': num_complete_middle,
        'num_total_laps': num_total_laps,
        'middle_lap': middle_lap,
        'start_lap': start_lap,
        'end_lap': end_lap,
    }
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"LAP REPETITION ANALYSIS")
        print(f"{'='*70}")
        print(f"Total time budget: {total_time:.1f}s ({total_time/3600:.2f} hours)")
        print(f"\nSegment breakdown:")
        print(f"  START lap:  {start_time:.1f}s")
        print(f"  MIDDLE lap: {middle_time:.1f}s (repeatable)")
        print(f"  END lap:    {end_time:.1f}s")
        print(f"\nAvailable for middle repeats: {available_for_middle:.1f}s")
        print(f"Number of complete MIDDLE laps: {num_complete_middle}")
        print(f"Total race strategy: START + MIDDLE×{num_complete_middle} + END")
        print(f"Total laps: {num_total_laps}")
        print(f"{'='*70}\n")
    
    return result


def main(
    setup_db: bool = True,
    num_laps: int = 3,
    remake_db: bool = False,
    update_db: bool = True,
    analyze_repetitions: bool = False,
    pop_size: int = 50,
    generations: int = 80,
    local_search: bool = True,
    **kwargs
) -> dict:
    """
    Main entry point for FSGP optimization.
    
    Parameters
    ----------
    setup_db : bool
        Initialize database from KML if True.
    num_laps : int
        Number of times to repeat the full course for baseline (default 3).
    remake_db : bool
        Force database recreation.
    update_db : bool
        Update database with optimized speeds/torques.
    analyze_repetitions : bool
        Analyze how many middle laps fit in the time budget (disabled by default).
    pop_size : int
        GA population size (default 50).
    generations : int
        Number of GA generations (default 80).
    local_search : bool
        Whether to use SLSQP polishing (default True).
    **kwargs
        Additional arguments passed to optimize_fsgp_strategy().
    
    Returns
    -------
    dict
        Contains 'opt_result', 'combined_course', 'full_track', and 'analysis'.
    """
    # Setup database
    if setup_db:
        try:
            setup_fsgp_database(remake=remake_db, verbose=True)
        except Exception as e:
            print(f"Error setting up database: {e}")
            print("Attempting to continue with existing database...")
    
    # Fetch full track for later analysis
    track_name = kwargs.get('track_name', 'FSGP_Track')
    db_path = kwargs.get('db_path', 'FSGP_2024.sqlite')
    
    full_track = fetch_route_intervals(
        track_name, 
        split_at_stops=False, 
        db_path=db_path
    )
    if isinstance(full_track, list):
        full_track = full_track[0]
    
    # Run optimization
    opt_result, combined_course = optimize_fsgp_strategy(
        track_name=track_name,
        db_path=db_path,
        num_laps=num_laps,
        pop_size=pop_size,
        generations=generations,
        local_search=local_search,
        verbose=True,
        plot_result=kwargs.get('plot_result', True),
    )
    
    # Update database if requested
    if update_db:
        # Create simple result object for database update
        class SimpleResult:
            def __init__(self, interval):
                self.combined_interval = interval
        
        lap_result = SimpleResult(combined_course)
        update_fsgp_database_with_optimized_speeds(
            track_name=track_name,
            lap_result=lap_result,
            db_path=db_path,
            verbose=True,
        )
    
    # Lap analysis - currently disabled due to SSInterval API limitations
    analysis = None
    
    return {
        'opt_result': opt_result,
        'combined_course': combined_course,
        'full_track': full_track,
        'analysis': analysis,
    }


if __name__ == "__main__":
    result = main(
        setup_db=True,
        num_laps=3,
        remake_db=False,
        pop_size=50,
        generations=80,
        local_search=True,
        analyze_repetitions=True,
        plot_result=True,
    )
    
    if result['analysis']:
        print("Lap analysis completed. See console output above for details.")
