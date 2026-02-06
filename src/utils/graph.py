import matplotlib.pyplot as plt
from .config import save_plot


import matplotlib.pyplot as plt

def plot_SSInterval(datasets, x_field, y_fields, name, labels=None, ax=None, xlabel=None, ylabel=None, title=None):
    import matplotlib.pyplot as plt

    def resolve_attr(obj, attr_path):
        for attr in attr_path.split('.'):
            obj = getattr(obj, attr)
        return obj

    # Allow both single and multiple y fields
    if isinstance(y_fields, str):
        y_fields = [y_fields]

    colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig = ax.get_figure()

    for i, points in enumerate(datasets):
        x_coords = [resolve_attr(point, x_field) for point in points]

        for j, y_field in enumerate(y_fields):
            y_coords = [resolve_attr(point, y_field) for point in points]
            label = (
                f"{labels[i]} - {y_field}"
                if labels
                else f"Dataset {i + 1} - {y_field}"
            )
            color = colors[(i * len(y_fields) + j) % len(colors)]
            ax.plot(x_coords, y_coords, marker='o', linestyle='-', color=color, label=label)

    ax.set_xlabel(xlabel if xlabel else x_field)
    ax.set_ylabel(ylabel if ylabel else ", ".join(y_fields))
    ax.set_title(title if title else f'{name}: {", ".join(y_fields)} vs {x_field}')
    ax.legend()
    ax.grid(True)
    if ax is None:
        fig.tight_layout()
        fig.show()
    return fig, ax


def plot_points(points, x_field, y_field, name):
    x_coords = [getattr(point.speed, x_field) for point in points]
    y_coords = [getattr(point, y_field) for point in points]

    plt.plot(x_coords, y_coords, marker='o', linestyle='-', color='b', label=f'{x_field} vs {y_field}')

    plt.xlabel(x_field)
    plt.ylabel(y_field)
    plt.title(f'Graph of {x_field} vs {y_field}')

    plt.xlim(min(x_coords), max(x_coords))
    plt.ylim(min(y_coords), max(y_coords))
    plt.legend()

    save_plot(plt.gcf(), f"{name}.png")
    plt.clf()

def plot_multiple_datasets(datasets, x_field, y_field, name, labels=None):
    """
    Plots multiple datasets on the same graph.

    :param datasets: List of datasets, each containing points.
    :param x_field: Attribute name for x-axis values.
    :param y_field: Attribute name for y-axis values.
    :param name: Name for the output file.
    :param labels: List of labels for each dataset (optional).
    """
    colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']  # Color cycle for different datasets

    plt.figure(figsize=(8, 6))  # Set figure size

    for i, points in enumerate(datasets):
        x_coords = [getattr(point.speed, x_field) for point in points]
        y_coords = [getattr(point, y_field) for point in points]

        label = labels[i] if labels else f'Dataset {i + 1}'
        plt.plot(x_coords, y_coords, marker='o', linestyle='-', color=colors[i % len(colors)], label=label)

    # Labels and titles
    plt.xlabel(x_field)
    plt.ylabel(y_field)
    plt.title(f'Graph of {x_field} vs {y_field}')
    plt.legend()
    plt.grid()

    # Save and show
    # save_plot(plt.gcf(), f"{name}.png")
    plt.show()
    # plt.clf()


import numpy as np


def plot_dual_axis_fit(
        x_values,
        y1_values,
        y2_values,
        model_y1,
        model_y2,
        x_label="X",
        y1_label="Y1",
        y2_label="Y2",
        title="Dual Axis Polynomial Fit",
        y1_color="blue",
        y2_color="green",
):
    """
    Plots two relationships on the same X-axis with two different Y-axes using fitted models.

    Parameters:
    - x_values: 1D array of x-axis values (shared)
    - y1_values: 1D array of values for the left Y-axis (e.g. Current)
    - y2_values: 1D array of values for the right Y-axis (e.g. RPM)
    - model_y1: fitted model to predict y1 from x
    - model_y2: fitted model to predict y2 from x
    - x_label, y1_label, y2_label: axis labels
    - title: plot title
    - y1_color, y2_color: colors for y1 and y2 data/lines
    """

    x_values = np.array(x_values)
    x_range = np.linspace(x_values.min(), x_values.max(), 300).reshape(-1, 1)

    fig, ax1 = plt.subplots(figsize=(10, 5))

    # First y-axis (left)
    ax1.scatter(x_values, y1_values, color=y1_color, label=f'Data ({x_label} vs {y1_label})')
    ax1.plot(x_range, model_y1.predict(x_range), color='red', label=f'Fit ({y1_label})')
    ax1.set_xlabel(x_label)
    ax1.set_ylabel(y1_label, color=y1_color)
    ax1.tick_params(axis='y', labelcolor=y1_color)
    ax1.set_title(title)

    # Second y-axis (right)
    ax2 = ax1.twinx()
    ax2.scatter(x_values, y2_values, color=y2_color, label=f'Data ({x_label} vs {y2_label})', alpha=0.6)
    ax2.plot(x_range, model_y2.predict(x_range), color='orange', linestyle='--', label=f'Fit ({y2_label})')
    ax2.set_ylabel(y2_label, color=y2_color)
    ax2.tick_params(axis='y', labelcolor=y2_color)

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center')

    plt.tight_layout()
    plt.show()


def plot_speed_current_datasets(datasets, labels=None, colors=None, title="Speed vs Current"):
    """
    Plots multiple speed-current relationships.

    Parameters:
        datasets: list of tuples [(speed_array_1, current_array_1), (speed_array_2, current_array_2), ...]
        labels: optional list of labels for each dataset
        colors: optional list of colors for each line
        title: title of the plot
    """
    plt.figure(figsize=(10, 6))

    for i, (speed, current) in enumerate(datasets):
        label = labels[i] if labels else f"Dataset {i + 1}"
        color = colors[i] if colors else None
        plt.plot(speed, current, label=label, color=color)
        plt.scatter(speed, current, s=30)

    plt.xlabel("Speed (m/s)")
    plt.ylabel("Current (A)")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()