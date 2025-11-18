from __future__ import annotations
import os
import time
from typing import Optional

from PyQt5.QtCore import QThread, pyqtSignal, QUrl
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QCheckBox,
    QDoubleSpinBox,
    QStatusBar,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView

from .route_map import RouteMap
from ..database.parse_route_table import parse_route_table


class MapWorker(QThread):
    """Generic worker thread to run a blocking map generation or simulation function.

    Emits:
            finished(object): result returned by the function (usually the saved file path)
            error(str): error message if exception occurs
            progress(str): optional progress messages
    """

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.progress.emit("starting...")
            res = self.func(*self.args, **self.kwargs)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RouteMap Viewer")
        self.resize(1100, 800)

        root = QWidget()
        self.setCentralWidget(root)

        v = QVBoxLayout(root)

        # Controls
        ctrl = QHBoxLayout()

        ctrl.addWidget(QLabel("Placemark:"))
        self.placemark_input = QLineEdit()
        self.placemark_input.setPlaceholderText("e.g. A. Independence to Topeka")
        ctrl.addWidget(self.placemark_input)

        self.generate_placemark_btn = QPushButton("Generate from Placemark")
        self.generate_placemark_btn.clicked.connect(self.on_generate_placemark)
        ctrl.addWidget(self.generate_placemark_btn)

        self.generate_time_nodes_btn = QPushButton("Simulate & Generate from Time Nodes")
        self.generate_time_nodes_btn.clicked.connect(self.on_generate_time_nodes)
        ctrl.addWidget(self.generate_time_nodes_btn)

        self.markers_cb = QCheckBox("Show markers")
        ctrl.addWidget(self.markers_cb)

        self.hover_cb = QCheckBox("Hover tooltips")
        self.hover_cb.setChecked(True)
        ctrl.addWidget(self.hover_cb)

        ctrl.addWidget(QLabel("Time step (s):"))
        self.timestep_spin = QDoubleSpinBox()
        self.timestep_spin.setRange(0.1, 10.0)
        self.timestep_spin.setSingleStep(0.1)
        self.timestep_spin.setValue(0.5)
        ctrl.addWidget(self.timestep_spin)

        v.addLayout(ctrl)

        # Web view for the folium HTML
        self.webview = QWebEngineView()
        v.addWidget(self.webview)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Make sure maps folder exists
        self.maps_dir = os.path.join(os.getcwd(), "maps")
        os.makedirs(self.maps_dir, exist_ok=True)

        # Keep a reference to worker so it doesn't get GC'd
        self._worker: Optional[MapWorker] = None

    def set_busy(self, busy: bool):
        self.generate_placemark_btn.setDisabled(busy)
        self.generate_time_nodes_btn.setDisabled(busy)

    def on_generate_placemark(self):
        name = self.placemark_input.text().strip()
        if not name:
            self.status.showMessage("Enter a placemark name first", 4000)
            return

        self.set_busy(True)
        self.status.showMessage("Generating map from placemark...")

        self._worker = MapWorker(self._generate_from_placemark, name)
        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _generate_from_placemark(self, name: str):
        rm = RouteMap()
        rm.generate_from_placemark(name)
        out = os.path.join(self.maps_dir, "gui_map_placemark")
        rm.save_map(out)
        # return absolute path to saved file
        return os.path.abspath(out + ".html")

    def on_generate_time_nodes(self):
        name = self.placemark_input.text().strip()
        if not name:
            self.status.showMessage("Enter a placemark name first", 4000)
            return

        timestep = float(self.timestep_spin.value())
        show_markers = bool(self.markers_cb.isChecked())
        hover = bool(self.hover_cb.isChecked())

        self.set_busy(True)
        self.status.showMessage("Parsing route and running simulation (this may take a while)...")

        self._worker = MapWorker(self._generate_from_time_nodes, name, timestep, show_markers, hover)
        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _generate_from_time_nodes(self, name: str, timestep: float, show_markers: bool, hover: bool):
        # parse route
        route = parse_route_table(name)

        # simulate (this mutates route and adds .segments and .time_nodes)
        # use TIME_STEP kwarg like existing code
        if hasattr(route, "simulate_interval"):
            route.simulate_interval(TIME_STEP=timestep)

        rm = RouteMap()
        # use show_markers and hover options
        rm.generate_from_time_nodes(route.segments, route.time_nodes, show_markers=show_markers, hover_tooltips=hover)
        out = os.path.join(self.maps_dir, "gui_map_time_nodes")
        rm.save_map(out)
        return os.path.abspath(out + ".html")

    def _on_map_finished(self, filepath: str):
        try:
            if not filepath:
                raise RuntimeError("No file returned from worker")
            url = QUrl.fromLocalFile(str(filepath))
            self.webview.load(url)
            self.status.showMessage(f"Loaded: {filepath}", 5000)
        except Exception as e:
            self.status.showMessage(f"Error loading map: {e}")
        finally:
            self.set_busy(False)

    def _on_worker_error(self, msg: str):
        self.status.showMessage(f"Worker error: {msg}")
        self.set_busy(False)


def run_app():
    import sys

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_app()
