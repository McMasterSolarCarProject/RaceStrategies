from typing import Callable
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QComboBox, QLabel, QGridLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from ...engine.interval_simulator import SSInterval
from ...engine.nodes import TimeNode
from ...utils.graph import plot_SSInterval


class GraphController(QWidget):
    """
    Widget to handle graph generation for an SSInterval.
    Contains a button to generate plots and a canvas to display them.
    """

    def __init__(self, frontend_func: Callable, parent=None):
        super().__init__(parent)

        self.simulated_route: SSInterval | None = None
        # Layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Add dropdown for x field 1, y field 1, x field 2, y field 2
        dropdown_layout = QGridLayout()
        # Dropdowns
        self.x1_dropdown = QComboBox()
        self.y1_dropdown = QComboBox()
        self.x2_dropdown = QComboBox()
        self.y2_dropdown = QComboBox()
        # Labels
        dropdown_layout.addWidget(QLabel("Graph 1 X Value"), 0, 0)
        dropdown_layout.addWidget(self.x1_dropdown, 0, 1)
        dropdown_layout.addWidget(QLabel("Graph 1 Y Value"), 1, 0)
        dropdown_layout.addWidget(self.y1_dropdown, 1, 1)
        dropdown_layout.addWidget(QLabel("Graph 2 X Value"), 2, 0)
        dropdown_layout.addWidget(self.x2_dropdown, 2, 1)
        dropdown_layout.addWidget(QLabel("Graph 2 Y Value"), 3, 0)
        dropdown_layout.addWidget(self.y2_dropdown, 3, 1)
        self.layout.addLayout(dropdown_layout)
        # Populate with TimeNode metrics
        self.populate_dropdowns()

        # Button to generate graphs
        self.generate_button = QPushButton("Generate Graphs")
        self.generate_button.clicked.connect(frontend_func)
        self.layout.addWidget(self.generate_button)

        # Matplotlib figure and canvas
        self.figure, self.axes = plt.subplots(2, 1)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

    def populate_dropdowns(self):
        """
        Populates the x and y field drop downs with all graphable measurements such as dist, time, kmph, etc.
        """
        metrics = TimeNode.get_numerical_metrics()
        dropdowns = [
            self.x1_dropdown,
            self.y1_dropdown,
            self.x2_dropdown,
            self.y2_dropdown,
        ]

        for dropdown in dropdowns:
            dropdown.clear()
            dropdown.addItems(metrics)

        # Set defaults:
        self.x1_dropdown.setCurrentText("dist")
        self.y1_dropdown.setCurrentText("speed.kmph")
        self.x2_dropdown.setCurrentText("time")
        self.y2_dropdown.setCurrentText("soc")

    def generate_graphs(self):
        """
        Run the interval simulator plotting functions and display in the embedded canvas.
        """
        if self.simulated_route is None:
            raise ValueError("No route selected. Please generate a map first.")

        self.figure.clear()
        self.axes = self.figure.subplots(2, 1)

        if not hasattr(self.simulated_route, "time_nodes"):
            self.simulated_route.simulate_interval()
        time_nodes = self.simulated_route.time_nodes
        braking_nodes = self.simulated_route.brakingNodes
        datasets = [time_nodes, braking_nodes]
        labels = ["Time Nodes", "Braking Nodes"]

        x1 = self.x1_dropdown.currentText()
        x2 = self.x2_dropdown.currentText()
        y1 = self.y1_dropdown.currentText()
        y2 = self.y2_dropdown.currentText()

        plot_SSInterval(
            datasets=datasets,
            x_field=x1,
            y_fields=y1,
            name=f"1_{x1}_vs_{y1}",
            labels=labels,
            ax=self.axes[0],
            xlabel=f"{TimeNode.NUMERICAL_METRICS[x1]}",
            ylabel=f"{TimeNode.NUMERICAL_METRICS[y1]}",
            title=f"{TimeNode.NUMERICAL_METRICS[x1]} vs {TimeNode.NUMERICAL_METRICS[y1]}",
        )
        plot_SSInterval(
            datasets=datasets,
            x_field=x2,
            y_fields=y2,
            name=f"2_{x2}_vs_{y2}",
            labels=labels,
            ax=self.axes[1],
            xlabel=f"{TimeNode.NUMERICAL_METRICS[x2]}",
            ylabel=f"{TimeNode.NUMERICAL_METRICS[y2]}",
            title=f"{TimeNode.NUMERICAL_METRICS[x2]} vs {TimeNode.NUMERICAL_METRICS[y2]}",
        )

        # Adjust layout and redraw
        self.figure.tight_layout()
        self.canvas.draw_idle()
