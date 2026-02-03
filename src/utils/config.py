import os
from matplotlib.figure import Figure

GRAPH_OUTPUT_DIR = "graphs/"
DATA_DIR = "data/"

def save_plot(plot: Figure, filename):
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(GRAPH_OUTPUT_DIR, filename)
    plot.savefig(filepath)
    print(f"Graph saved to {filepath}")

