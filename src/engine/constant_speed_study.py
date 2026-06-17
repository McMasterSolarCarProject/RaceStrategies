from .nodes import Segment, StateNode
from .kinematics import Speed, Coordinate
from ..utils import constants
import matplotlib.pyplot as plt


def constant_speed_mass_study(
    segment: Segment,
    speed: Speed,
    masses: list[float],
    duration_hours: float = 8.0,
) -> list[dict]:
    """
    Evaluate constant-speed cruise feasibility and power for each candidate mass.

    Returns one row per mass with:
    - feasible: whether cruise-state solve succeeded at the requested speed
    - power_w: motor electrical input power (P_in)
    - total_power_w: P_in + passive vehicle consumption
    - distance_km: distance traveled in duration_hours at the requested speed
    - energy_wh: total energy used over duration_hours
    """
    original_profile = constants.get_active_profile()
    results: list[dict] = []

    for mass in masses:
        constants.set_active_profile(original_profile.override("vehicle.car_mass", mass))
        node = StateNode(segment=segment, speed=speed)
        feasible = node.solve_cruise_state()

        distance_km = speed.kmph * duration_hours
        row = {
            "mass_kg": mass,
            "speed_kmph": speed.kmph,
            "duration_h": duration_hours,
            "feasible": feasible,
            "distance_km": distance_km,
            "power_w": None,
            "total_power_w": None,
            "energy_wh": None,
            "torque_nm": None,
        }

        if feasible:
            total_power_w = node.P_in + constants.passive_consumption
            row["power_w"] = node.P_in
            row["total_power_w"] = total_power_w
            row["energy_wh"] = total_power_w * duration_hours
            row["torque_nm"] = node.torque

        results.append(row)

    constants.set_active_profile(original_profile)
    return results


def print_constant_speed_mass_study(results: list[dict]) -> None:
    """Pretty-print rows produced by constant_speed_mass_study."""
    if not results:
        print("No results to display.")
        return

    print("mass_kg | speed_kmph | feasible | distance_km | total_power_w | energy_wh")
    for row in results:
        total_power = "NA" if row["total_power_w"] is None else f"{row['total_power_w']:.2f}"
        energy = "NA" if row["energy_wh"] is None else f"{row['energy_wh']:.2f}"
        print(f"{row['mass_kg']:>7.1f} | {row['speed_kmph']:>10.2f} | {str(row['feasible']):>8} | {row['distance_km']:>11.2f} | {total_power:>13} | {energy:>9}")


def find_flattest_segment(segments: list[Segment]) -> Segment:
    """Return the segment with gradient closest to zero."""
    if not segments:
        raise ValueError("No segments provided")
    return min(segments, key=lambda seg: abs(seg.gradient.sin()))


def build_zero_gradient_segment(
    speed_limit_kmph: float = 120.0,
    start: Coordinate = Coordinate(39.0, -94.0, 100.0),
    end: Coordinate = Coordinate(39.01, -94.0, 100.0),
) -> Segment:
    """Create a synthetic segment with zero elevation change (flat gradient)."""
    return Segment(
        p1=start,
        p2=end,
        id=-1,
        speed_limit=Speed(kmph=speed_limit_kmph),
    )


def constant_speed_power_sweep(
    segment: Segment,
    mass_kg: float,
    duration_hours: float = 8.0,
    min_speed_kmph: float = 5.0,
    max_speed_kmph: float | None = None,
    speed_step_kmph: float = 1.0,
) -> list[dict]:
    """Sweep speeds for a fixed mass and return 8-hour power/energy results."""
    if max_speed_kmph is None:
        max_speed_kmph = max(5.0, segment.speed_limit.kmph)

    original_profile = constants.get_active_profile()
    constants.set_active_profile(original_profile.override("vehicle.car_mass", mass_kg))

    rows: list[dict] = []
    speed_kmph = min_speed_kmph
    while speed_kmph <= max_speed_kmph:
        speed = Speed(kmph=speed_kmph)
        node = StateNode(segment=segment, speed=speed)
        feasible = node.solve_cruise_state()

        row = {
            "speed_kmph": speed_kmph,
            "feasible": feasible,
            "duration_h": duration_hours,
            "distance_km": speed_kmph * duration_hours,
            "motor_power_w": None,
            "total_power_w": None,
            "energy_wh": None,
            "torque_nm": None,
        }

        if feasible:
            total_power_w = node.P_in + constants.passive_consumption
            row["motor_power_w"] = node.P_in
            row["total_power_w"] = total_power_w
            row["energy_wh"] = total_power_w * duration_hours
            row["torque_nm"] = node.torque

        rows.append(row)
        speed_kmph += speed_step_kmph

    constants.set_active_profile(original_profile)
    return rows


def run_mass_variation_speed_sweep(
    segment: Segment,
    masses_kg: list[float],
    duration_hours: float = 8.0,
    min_speed_kmph: float = 5.0,
    max_speed_kmph: float | None = None,
    speed_step_kmph: float = 1.0,
) -> dict[float, list[dict]]:
    """Run speed sweep for each mass and return rows keyed by mass."""
    results: dict[float, list[dict]] = {}
    for mass in masses_kg:
        results[mass] = constant_speed_power_sweep(
            segment=segment,
            mass_kg=mass,
            duration_hours=duration_hours,
            min_speed_kmph=min_speed_kmph,
            max_speed_kmph=max_speed_kmph,
            speed_step_kmph=speed_step_kmph,
        )
    return results


def plot_constant_speed_power_sweep(rows: list[dict], title: str = "8h Constant-Speed Study") -> None:
    """Plot 8-hour energy versus speed for feasible points."""
    feasible_rows = [row for row in rows if row["feasible"]]
    if not feasible_rows:
        print("No feasible points to plot.")
        return

    speeds = [row["speed_kmph"] for row in feasible_rows]
    energy_wh = [row["energy_wh"] for row in feasible_rows]

    plt.figure(figsize=(10, 6))
    plt.plot(speeds, energy_wh, color="tab:red", marker="o", label="Energy in 8h (Wh)")
    plt.xlabel("Speed (km/h)")
    plt.ylabel("Energy in 8h (Wh)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left")
    plt.title(title)
    plt.tight_layout()
    plt.show()


def plot_mass_variation_energy_sweep(
    mass_results: dict[float, list[dict]],
    title: str = "8h Constant-Speed Study (Mass Variation)",
) -> None:
    """Plot energy-vs-speed curves for multiple masses."""
    plt.figure(figsize=(10, 6))

    plotted = 0
    for mass, rows in mass_results.items():
        feasible_rows = [row for row in rows if row["feasible"]]
        if not feasible_rows:
            continue

        speeds = [row["speed_kmph"] for row in feasible_rows]
        energy_wh = [row["energy_wh"] for row in feasible_rows]
        plt.plot(speeds, energy_wh, marker="o", linewidth=1.5, label=f"{mass:.0f} kg")
        plotted += 1

    if plotted == 0:
        print("No feasible points to plot for any mass.")
        return

    plt.xlabel("Speed (km/h)")
    plt.ylabel("Energy in 8h (Wh)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left", title="Mass")
    plt.title(title)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    flat_segment = build_zero_gradient_segment(speed_limit_kmph=120.0)
    masses_to_test = [685, 690]  # Edit this list for specific masses

    print(f"Using synthetic flat segment: id={flat_segment.id}, gradient_sin={flat_segment.gradient.sin():.6f}, speed_limit={flat_segment.speed_limit.kmph:.2f} km/h")

    mass_results = run_mass_variation_speed_sweep(
        segment=flat_segment,
        masses_kg=masses_to_test,
        duration_hours=8.0,
        min_speed_kmph=5.0,
        max_speed_kmph=max(5.0, flat_segment.speed_limit.kmph),
        speed_step_kmph=1.0,
    )

    for mass in masses_to_test:
        rows = mass_results[mass]
        feasible_count = len([row for row in rows if row["feasible"]])
        print(f"Mass {mass:.0f} kg: computed {len(rows)} speeds, feasible points: {feasible_count}")

    plot_mass_variation_energy_sweep(
        mass_results,
        title="Synthetic Flat Segment | 8h Constant-Speed | Mass Variation",
    )
