import streamlit as st
import plotly.graph_objects as go

from src.engine.interval_simulator import SSInterval
from src.engine.nodes import TimeNode


def get_available_metrics():
    """Get list of plottable metrics from TimeNode."""
    return list(TimeNode.NUMERICAL_METRICS.keys())


def resolve_attr(obj, attr_path):
    """Resolve dot-notation attribute path (e.g., 'speed.kmph')."""
    for attr in attr_path.split("."):
        obj = getattr(obj, attr)
    return obj


def get_metric_name(metric: str):
    """Get the name of a metric from a TimeNode, supporting nested attributes."""
    return TimeNode.NUMERICAL_METRICS.get(metric, metric)


def extract_data_from_nodes(nodes: list, x_field: str, y_field: str):
    """Extract x and y data from a list of TimeNodes."""
    x_data = []
    y_data = []
    for node in nodes:
        try:
            x_val = resolve_attr(node, x_field)
            y_val = resolve_attr(node, y_field)
            if x_val is not None and y_val is not None:
                x_data.append(x_val)
                y_data.append(y_val)
        except (AttributeError, TypeError):
            continue
    return x_data, y_data


def create_plotly_chart(intervals: list[SSInterval], x_field: str, y_field: str, title: str, show_braking: bool = True):
    """Create an interactive Plotly chart from simulation data."""
    fig = go.Figure()

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

    for i, interval in enumerate(intervals):
        if not hasattr(interval, "time_nodes"):
            continue

        color = colors[i % len(colors)]

        x_data, y_data = extract_data_from_nodes(interval.time_nodes, x_field, y_field)
        if x_data and y_data:
            fig.add_trace(
                go.Scatter(
                    x=x_data,
                    y=y_data,
                    mode="lines",
                    name=f"Interval {i+1}",
                    line=dict(color=color, width=2),
                    hovertemplate=f"{x_field}: %{{x:.2f}}<br>{y_field}: %{{y:.2f}}<extra>Interval {i+1}</extra>",
                )
            )

        if show_braking and hasattr(interval, "brakingNodes"):
            x_brake, y_brake = extract_data_from_nodes(interval.brakingNodes, x_field, y_field)
            if x_brake and y_brake:
                fig.add_trace(
                    go.Scatter(
                        x=x_brake,
                        y=y_brake,
                        mode="lines",
                        name=f"Braking {i+1}",
                        line=dict(color=color, width=1, dash="dash"),
                        hovertemplate=f"{x_field}: %{{x:.2f}}<br>{y_field}: %{{y:.2f}}<extra>Braking {i+1}</extra>",
                    )
                )

    x_label = TimeNode.NUMERICAL_METRICS.get(x_field, x_field)
    y_label = TimeNode.NUMERICAL_METRICS.get(y_field, y_field)

    fig.update_layout(
        title=title, xaxis_title=x_label, yaxis_title=y_label, hovermode="closest", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=60, r=20, t=60, b=60)
    )

    return fig


def create_master_chart(master_interval: SSInterval, x_field: str, y_fields: list[str], title: str, show_braking: bool = False):
    """Create a chart for the master (joined) interval with multiple y-fields."""
    fig = go.Figure()

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    if hasattr(master_interval, "time_nodes"):
        for j, y_field in enumerate(y_fields):
            x_data, y_data = extract_data_from_nodes(master_interval.time_nodes, x_field, y_field)
            if x_data and y_data:
                y_label = TimeNode.NUMERICAL_METRICS.get(y_field, y_field)
                fig.add_trace(
                    go.Scatter(
                        x=x_data,
                        y=y_data,
                        mode="lines",
                        name=y_label,
                        line=dict(color=colors[j % len(colors)], width=2),
                        hovertemplate=f"{x_field}: %{{x:.2f}}<br>{y_field}: %{{y:.2f}}<extra>{y_label}</extra>",
                    )
                )

        if show_braking and hasattr(master_interval, "brakingNodes"):
            for j, y_field in enumerate(y_fields):
                x_brake, y_brake = extract_data_from_nodes(master_interval.brakingNodes, x_field, y_field)
                if x_brake and y_brake:
                    fig.add_trace(
                        go.Scatter(
                            x=x_brake,
                            y=y_brake,
                            mode="lines",
                            name=f"Braking - {y_field}",
                            line=dict(color=colors[j % len(colors)], width=1, dash="dash"),
                        )
                    )

    x_label = TimeNode.NUMERICAL_METRICS.get(x_field, x_field)

    fig.update_layout(
        title=title, xaxis_title=x_label, yaxis_title="Value", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=60, r=20, t=60, b=60)
    )

    return fig
