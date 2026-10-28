from collections.abc import Iterable, Mapping, Sequence
import math

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.engine.nodes import StateNode


def plot_dynamic_nodes(
    profiles: Mapping[str, Iterable[StateNode]],
    x_parameter: str = "time",
    y_parameters: Sequence[str] = ("velocity",),
    *,
    title: str | None = None,
    show: bool = True,
) -> tuple[Figure, Axes]:
    """Plot selected StateNode attributes for one or more profiles."""
    profile_nodes = {name: list(nodes) for name, nodes in profiles.items()}
    if not profile_nodes:
        raise ValueError("profiles must contain at least one profile")
    if not y_parameters:
        raise ValueError("y_parameters must contain at least one attribute")

    parameters = [x_parameter, *y_parameters]
    missing_parameters = [
        parameter
        for parameter in dict.fromkeys(parameters)
        if any(
            not nodes or not hasattr(nodes[0], parameter)
            for nodes in profile_nodes.values()
        )
    ]
    if missing_parameters:
        raise AttributeError(
            f"StateNode has no attribute(s): {', '.join(missing_parameters)}"
        )

    figure, axis = plt.subplots()
    for profile_name, nodes in profile_nodes.items():
        x_values = [getattr(node, x_parameter) for node in nodes]
        for parameter in y_parameters:
            axis.plot(
                x_values,
                [getattr(node, parameter) for node in nodes],
                marker="o",
                linestyle="-",
                label=f"{profile_name}: {parameter}",
            )

    axis.set_xlabel(x_parameter)
    axis.set_ylabel("State value")
    axis.grid(True)
    axis.legend()
    if title is not None:
        axis.set_title(title)

    if show:
        plt.show()

    return figure, axis


def plot_efficiency_vs_speed(
    nodes: Iterable[StateNode],
    *,
    title: str | None = None,
    show: bool = True,
) -> tuple[Figure, Axes]:
    """Plot the requested power-over-speed efficiency against speed."""
    profile_nodes = list(nodes)
    if not profile_nodes:
        raise ValueError("nodes must contain at least one StateNode")

    velocities = []
    efficiencies = []
    for node in profile_nodes:
        node.Power_calc(node.velocity)
        velocities.append(node.velocity)
        efficiencies.append(
            node.Power / node.velocity if not math.isclose(node.velocity, 0) else math.nan
        )

    figure, axis = plt.subplots()
    axis.plot(velocities, efficiencies, marker="o", linestyle="-")
    axis.set_xlabel("Velocity (m/s)")
    axis.set_ylabel("Efficiency (power / velocity)")
    axis.grid(True)
    if title is not None:
        axis.set_title(title)

    if show:
        plt.show()

    return figure, axis