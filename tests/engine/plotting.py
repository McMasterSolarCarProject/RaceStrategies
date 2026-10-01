from collections.abc import Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.engine.nodes import DynamicNode


def plot_dynamic_nodes(
    profiles: Mapping[str, Iterable[DynamicNode]],
    x_parameter: str = "time",
    y_parameters: Sequence[str] = ("velocity",),
    *,
    title: str | None = None,
    show: bool = True,
) -> tuple[Figure, Axes]:
    """Plot selected DynamicNode attributes for one or more named profiles."""
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
            f"DynamicNode has no attribute(s): {', '.join(missing_parameters)}"
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
    axis.set_ylabel("DynamicNode value")
    axis.grid(True)
    axis.legend()
    if title is not None:
        axis.set_title(title)

    if show:
        plt.show()

    return figure, axis