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
        # Set up the window
        self.setWindowTitle("RouteMap Viewer")
        self.resize(1100, 800)
        root = QWidget()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)

        # Controls at the top header
        ctrl = QHBoxLayout()

        ctrl.addWidget(QLabel("Placemark:"))
        self.placemark_input = QLineEdit()  # Text input. Probably should change to drop down later
        self.placemark_input.setPlaceholderText("e.g. A. Independence to Topeka")
        ctrl.addWidget(self.placemark_input)

        self.generate_placemark_btn = QPushButton("Generate from Placemark")
        self.generate_placemark_btn.clicked.connect(self.on_generate_placemark)
        ctrl.addWidget(self.generate_placemark_btn)

        self.generate_time_nodes_btn = QPushButton("Simulate & Generate from Time Nodes")
        self.generate_time_nodes_btn.clicked.connect(self.on_generate_time_nodes)
        ctrl.addWidget(self.generate_time_nodes_btn)

        self.hover_cb = QCheckBox("Hover tooltips")
        self.hover_cb.setChecked(True)
        ctrl.addWidget(self.hover_cb)

        ctrl.addWidget(QLabel("Time step (s):"))
        self.timestep_spin = QDoubleSpinBox()  # Input for a floating point number
        self.timestep_spin.setRange(0.1, 10.0)
        self.timestep_spin.setSingleStep(0.1)
        self.timestep_spin.setValue(0.5)
        ctrl.addWidget(self.timestep_spin)

        v.addLayout(ctrl)

        # Web view for the folium HTML
        self.webview = QWebEngineView()
        v.addWidget(self.webview)

        # Status bar at the bottom
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Make sure maps folder exists
        self.maps_dir = os.path.join(os.getcwd(), "maps")
        os.makedirs(self.maps_dir, exist_ok=True)

        # Keep a reference to worker so it doesn't get garbage collected
        self._worker: Optional[MapWorker] = None

    def set_busy(self, busy: bool):
        """
        Disables buttons when the busy argument is true
        """

        self.generate_placemark_btn.setDisabled(busy)
        self.generate_time_nodes_btn.setDisabled(busy)

    def on_generate_placemark(self):
        """
        Frontend function called when the generate placemark button is pressed
        """
        name = self.placemark_input.text().strip()  # get value from placemark_input widget
        if not name:
            self.status.showMessage("Enter a placemark name first", 4000)
            return

        self.set_busy(True)
        self.status.showMessage("Generating map from placemark...")

        # Calls the backend function in the first parameter by passing the second parameter as an argument
        self._worker = MapWorker(self._generate_from_placemark, name) # Map worker runs background tasks as a separate thread

        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished) # calls the _on_map_finished function based on the return value of _generate_from_placemark
        self._worker.error.connect(self._on_worker_error) # if _generate_from_placemark throws an error, call _on_Worker_error and pass in the exception as an argument
        self._worker.start()

    def _generate_from_placemark(self, name: str):
        """Backend function for generating from the placemark with the same name as the argument passed in
        Saves the map to a html output file.
        """
        rm = RouteMap()
        rm.generate_from_placemark(name)
        out = os.path.join(self.maps_dir, "gui_map_placemark")
        rm.save_map(out)
        # return absolute path to saved file
        return os.path.abspath(out + ".html")

    def on_generate_time_nodes(self):
        """
        Frontend function called when the generate from time nodes button is pressed
        """
        name = self.placemark_input.text().strip() # Similar to before, gets text input
        if not name:
            self.status.showMessage("Enter a placemark name first", 4000)
            return

        timestep = float(self.timestep_spin.value()) # Gets numerical input
        hover = bool(self.hover_cb.isChecked()) # Gets boolean input from a checkbox

        self.set_busy(True)
        self.status.showMessage("Parsing route and running simulation (this may take a while)...")

        self._worker = MapWorker(self._generate_from_time_nodes, name, timestep, hover) # Cals the first function with other parameters as arguments into the first parameter
        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _generate_from_time_nodes(self, name: str, timestep: float, hover: bool) -> str:
        """Backend function to generate map with tie node siulations
        """
        # parse route
        route = parse_route_table(name)

        # simulate (this mutates route and adds .segments and .time_nodes)
        # use TIME_STEP kwarg like existing code
        if hasattr(route, "simulate_interval"):
            route.simulate_interval(TIME_STEP=timestep)

        rm = RouteMap()
        # use hover options
        rm.generate_from_time_nodes(route.segments, route.time_nodes, hover_tooltips=hover)
        out = os.path.join(self.maps_dir, "gui_map_time_nodes")
        rm.save_map(out)
        return os.path.abspath(out + ".html")

    def _on_map_finished(self, filepath: str):
        """After map is generated, load it in the viewer
        """
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
