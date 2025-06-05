import os
import matplotlib.pyplot as plt

GRAPH_OUTPUT_DIR = "graphs/"
DATA_DIR = "data/"

def save_plot(plot: plt, filename):
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(GRAPH_OUTPUT_DIR, filename)
    plot.savefig(filepath)
    print(f"Graph saved to {filepath}")

