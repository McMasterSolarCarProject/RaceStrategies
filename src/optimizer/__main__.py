"""
CLI entry point for the optimizer benchmark and route optimizer.

Usage:
    # Benchmark all methods on a small interval (1 segment):
    python -m src.optimizer benchmark

    # Benchmark specific methods:
    python -m src.optimizer benchmark --methods de,ga,dp

    # Benchmark on the full route (no node limit):
    python -m src.optimizer benchmark --route "A. Independence to Topeka" --no-limit

    # Optimise a full route with a specific method:
    python -m src.optimizer route --method ga

    # List available route names:
    python -m src.optimizer routes
"""
from __future__ import annotations

import argparse
import sqlite3
import sys

from ..database.fetch_route_intervals import fetch_route_intervals
from ..engine.interval_simulator import SSInterval
from .benchmark import benchmark_interval, optimize_route


ALL_METHODS = ["coarse_to_fine", "de", "slsqp", "ga", "dp"]


def _list_routes(db_path: str = "ASC_2024.sqlite") -> list[str]:
    """Fetch all distinct placemark names from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT DISTINCT placemark_name FROM route_data ORDER BY placemark_name"
    )
    routes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return routes


def cmd_routes(args: argparse.Namespace) -> None:
    """List available route (placemark) names."""
    routes = _list_routes(args.db)
    print(f"Available routes ({len(routes)}):")
    for r in routes:
        print(f"  {r}")


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Benchmark optimizers on a single interval."""
    placemark = args.route
    max_nodes = None if args.no_limit else args.max_nodes

    print(f"Loading route '{placemark}' "
          f"(max_nodes={'unlimited' if max_nodes is None else max_nodes}) ...")
    intervals = fetch_route_intervals(
        placemark, split_at_stops=True,
        max_nodes=max_nodes, db_path=args.db,
    )
    if isinstance(intervals, SSInterval):
        intervals = [intervals]

    # Pick the interval to benchmark
    if args.interval is not None:
        if args.interval < 1 or args.interval > len(intervals):
            print(f"Error: --interval must be 1–{len(intervals)}, "
                  f"got {args.interval}")
            sys.exit(1)
        interval = intervals[args.interval - 1]
    else:
        # Default: largest interval (most segments)
        interval = max(intervals, key=lambda iv: len(iv.segments))

    print(f"Interval: {len(interval.segments)} segments, "
          f"{interval.total_dist:.0f} m\n")

    methods = args.methods.split(",") if args.methods else None
    benchmark_interval(
        interval,
        v_min=args.v_min,
        v_max=args.v_max,
        methods=methods,
        verbose=True,
    )


def cmd_route(args: argparse.Namespace) -> None:
    """Optimise a full route with a single method."""
    max_nodes = None if args.no_limit else args.max_nodes
    optimize_route(
        placemark_name=args.route,
        db_path=args.db,
        max_nodes=max_nodes,
        v_min=args.v_min,
        v_max=args.v_max,
        method=args.method,
        verbose=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m src.optimizer",
        description="Solar car race strategy optimizer",
    )
    parser.add_argument(
        "--db", default="ASC_2024.sqlite",
        help="Path to SQLite database (default: ASC_2024.sqlite)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── routes ──
    sp_routes = subparsers.add_parser(
        "routes", help="List available route names"
    )
    sp_routes.set_defaults(func=cmd_routes)

    # ── benchmark ──
    sp_bench = subparsers.add_parser(
        "benchmark", help="Benchmark optimizers on a single interval",
        aliases=["bench"],
    )
    sp_bench.add_argument(
        "--route", "-r",
        default="A. Independence to Topeka",
        help="Placemark / route name (default: A. Independence to Topeka)",
    )
    sp_bench.add_argument(
        "--methods", "-m",
        default=None,
        help="Comma-separated methods to run "
             f"(options: {', '.join(ALL_METHODS)}). "
             "Default: auto-selects based on segment count.",
    )
    sp_bench.add_argument(
        "--max-nodes", "-n", type=int, default=20,
        help="Max route nodes to load (default: 20). Use --no-limit for all.",
    )
    sp_bench.add_argument(
        "--no-limit", action="store_true",
        help="Load all route nodes (overrides --max-nodes).",
    )
    sp_bench.add_argument(
        "--interval", "-i", type=int, default=None,
        help="Which interval to benchmark (1-based). Default: largest.",
    )
    sp_bench.add_argument("--v-min", type=float, default=5.0, help="Min speed km/h (default: 5)")
    sp_bench.add_argument("--v-max", type=float, default=45.0, help="Max speed km/h (default: 45)")
    sp_bench.set_defaults(func=cmd_benchmark)

    # ── route ──
    sp_route = subparsers.add_parser(
        "route", help="Optimise a full route with one method",
    )
    sp_route.add_argument(
        "--route", "-r",
        default="A. Independence to Topeka",
        help="Placemark / route name",
    )
    sp_route.add_argument(
        "--method", "-m", default="ga",
        help=f"Optimizer method (options: {', '.join(ALL_METHODS)}). Default: ga",
    )
    sp_route.add_argument(
        "--max-nodes", "-n", type=int, default=None,
        help="Max route nodes (default: unlimited).",
    )
    sp_route.add_argument(
        "--no-limit", action="store_true",
        help="Load all route nodes.",
    )
    sp_route.add_argument("--v-min", type=float, default=5.0, help="Min speed km/h (default: 5)")
    sp_route.add_argument("--v-max", type=float, default=45.0, help="Max speed km/h (default: 45)")
    sp_route.set_defaults(func=cmd_route)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
