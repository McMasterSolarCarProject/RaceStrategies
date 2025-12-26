from __future__ import annotations
import os
import time
from typing import Optional
import sqlite3

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
    QComboBox,
    QFileDialog,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView

from .route_map import RouteMap
from ..database.parse_route_table import parse_route_table
from ..database.init_route_table import init_route_db


class MapWorker(QThread):
    """Generic worker thread to run a blocking map generation or simulation function.

    Emits:
            finished(object): result returned by the function (usually the saved file path)
            error(str): error message if exception occurs
            progress(str): optional progress messages
    """

    # Running self.finished.connect, self.error.connect, and self.progress.connect effectively causes those functions to be called when running .emit
    # eg. when connecting showMessage to self.progress, running self.progress.emit("Hello world") will run showMessage() with "Hello world" passed as an argument
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

        # For a file upload, have a readonly text
        ctrl.addWidget(QLabel("KML File"))
        self.kml_input = QLineEdit()
        self.kml_input.setReadOnly(True)
        self.kml_input.setPlaceholderText("Select a .kml file...")
        ctrl.addWidget(self.kml_input)

        self.upload_kml_btn = QPushButton("Browse…")
        self.upload_kml_btn.clicked.connect(self.on_upload_kml)
        ctrl.addWidget(self.upload_kml_btn)

        ctrl.addWidget(QLabel("Placemark:"))
        self.placemark_input = QComboBox()
        self.placemark_input.setEditable(False)
        self.placemark_input.setMinimumWidth(250)
        ctrl.addWidget(self.placemark_input)

        self.generate_placemark_btn = QPushButton("Generate from Placemark")
        self.generate_placemark_btn.clicked.connect(self.on_generate_placemark)
        ctrl.addWidget(self.generate_placemark_btn)

        self.generate_time_nodes_btn = QPushButton("Simulate && Generate from Time Nodes")
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

        # After creating all widgets, perform these initialization tasks
        self._populate_placemark_dropdown()

    def set_busy(self, busy: bool):
        """
        Disables buttons when the busy argument is true
        """

        self.generate_placemark_btn.setDisabled(busy)
        self.generate_time_nodes_btn.setDisabled(busy)

    def on_upload_kml(self):
        """
        Frontend function called when the upload kml button is pressed
        """
        # Opens a dialog that only filters for KML files
        file_path, _ = QFileDialog.getOpenFileName(self, "Select KML File", "", "KML Files (*.kml)")
        if file_path:
            self.kml_input.setText(file_path)
            print(f"Selected file: {file_path}")

        self.set_busy(True)  # Disables buttons until worker finished or worker error
        self.status.showMessage(f"Uploading kml file {file_path}...")

        # Calls the backend function in the first parameter by passing the second parameter as an argument
        self._worker = MapWorker(self._upload_kml, file_path)  # Map worker runs background tasks as a separate thread

        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._populate_placemark_dropdown)  # Populates the dropdown with new segment ids
        self._worker.error.connect(self._on_worker_error)  # if _upload_kml throws an error, call _on_worker_error and pass in the exception as an argument
        self._worker.start()

    def _upload_kml(self, path: str) -> None:
        """
        Backend function that uses the uploaded kml file to populate the data.sqlite file
        """
        init_route_db(remake=True, kml_path=path)

    def _populate_placemark_dropdown(self):
        """
        Populate the placemark dropdown using segment_id values in data.sqlite.
        """
        db_path = "data.sqlite"
        self.placemark_input.clear()
        if not os.path.exists(db_path):
            self.status.showMessage("data.sqlite not found")
            return

        try:
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT segment_id FROM route_data WHERE segment_id IS NOT NULL")
                segment_ids = sorted(row[0] for row in cur.fetchall())
            conn.close()  # With block doesn't automatically close sqlite connection

            if not segment_ids:
                self.status.showMessage("No segments found in database")
                return
            self.placemark_input.addItems(segment_ids)
            self.status.showMessage("All segments successfully uploaded")

        except Exception as e:
            self.status.showMessage(f"Error: {e}")
        finally:
            self.set_busy(False)

    def on_generate_placemark(self):
        """
        Frontend function called when the generate placemark button is pressed
        """
        name = self.placemark_input.currentText().strip()  # get value from placemark_input widget
        if not name:
            self.status.showMessage("Enter a placemark name first")
            return None

        self.set_busy(True)  # Disables buttons until worker finished or worker error
        self.status.showMessage("Generating map from placemark...")

        # Calls the backend function in the first parameter by passing the second parameter as an argument
        self._worker = MapWorker(self._generate_from_placemark, name)  # Map worker runs background tasks as a separate thread

        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished)  # calls the _on_map_finished function based on the return value of _generate_from_placemark
        self._worker.error.connect(self._on_worker_error)  # if _generate_from_placemark throws an error, call _on_worker_error and pass in the exception as an argument
        self._worker.start()

    def _generate_from_placemark(self, name: str):
        """
        Backend function for generating from the placemark with the same name as the argument passed in
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
        name = self.placemark_input.currentText().strip()  # Similar to before, gets text input
        if not name:
            self.status.showMessage("Enter a placemark name first", 4000)
            return

        timestep = float(self.timestep_spin.value())  # Gets numerical input
        hover = bool(self.hover_cb.isChecked())  # Gets boolean input from a checkbox

        self.set_busy(True)
        self.status.showMessage("Parsing route and running simulation (this may take a while)...")

        self._worker = MapWorker(self._generate_from_time_nodes, name, timestep, hover)  # Cals the first function with other parameters as arguments into the first parameter
        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _generate_from_time_nodes(self, name: str, timestep: float, hover: bool) -> str:
        """
        Backend function to generate map with the node simulations
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
        """
        After map is generated, load it in the viewer
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
