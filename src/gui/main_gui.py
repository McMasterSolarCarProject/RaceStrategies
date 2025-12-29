from __future__ import annotations
import os
import sys
from typing import Optional

from PyQt5.QtCore import QUrl
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
    QSplitter,
)

from .worker import Worker, WorkerResult
from .services.kml_service import upload_kml
from .services.db_service import get_segment_ids
from .controllers.state_controller import StateController
from .controllers.map_controller import MapController
from .controllers.graph_controller import GraphController


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

        # Splitter to show both map and graphs
        splitter = QSplitter()

        # Create a map controller (may eventually want to do something similar for graphs)
        self.map_controller = MapController(os.path.join(os.getcwd(), "maps"))
        os.makedirs(self.map_controller.maps_dir, exist_ok=True)

        splitter.addWidget(self.map_controller)

        # Graph controller widget
        self.graph_controller = GraphController(None, self.on_generate_graphs)
        splitter.addWidget(self.graph_controller)
        splitter.setSizes([600, 400])

        v.addWidget(splitter)

        # Status bar at the bottom
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Keep a reference to worker so it doesn't get garbage collected
        self._worker: Optional[Worker] = None

        # Used to control busy and idle states. Add more buttons here to control state
        self.state = StateController(self.status, self.generate_placemark_btn, self.generate_time_nodes_btn, self.upload_kml_btn, self.graph_controller.generate_button)

        # Store current interval simulator for graph controller
        # self._current_interval_simulator = None

        # After creating all widgets, perform these initialization tasks
        self._populate_placemark_dropdown()

    def on_upload_kml(self):
        """
        Frontend function called when the upload kml button is pressed
        """
        # Opens a dialog that only filters for KML files
        file_path, _ = QFileDialog.getOpenFileName(self, "Select KML File", "", "KML Files (*.kml)")
        if file_path:
            self.kml_input.setText(file_path)
            print(f"Selected file: {file_path}")

        self.state.busy(f"Uploading kml file {file_path}...")  # Disables buttons until worker finished or worker error

        # Calls the backend function in the first parameter by passing the second parameter as an argument
        self._worker = Worker(upload_kml, file_path)  # Map worker runs background tasks as a separate thread

        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_kml_uploaded)  # Populates the dropdown with new segment ids
        self._worker.start()

    def _on_kml_uploaded(self, result: WorkerResult):
        """
        After KML is loaded, populate the placemark dropdown
        """
        if result.error:
            self.state.idle(f"Worker error: {str(result.error)}")
        else:
            self._populate_placemark_dropdown()
        self.state.idle()

    def _populate_placemark_dropdown(self):
        """
        Populate the placemark dropdown using segment_id values in data.sqlite.
        """
        self.placemark_input.clear()

        try:
            segment_ids = get_segment_ids()
            if not segment_ids:
                self.status.showMessage("No segments found in database")
                return
            self.placemark_input.addItems(segment_ids)
            self.status.showMessage("Segments loaded successfully")
        except Exception as e:
            self.status.showMessage(f"Error: {e}", 3000)

    def on_generate_placemark(self):
        """
        Frontend function called when the generate placemark button is pressed
        """
        name = self.placemark_input.currentText().strip()  # get value from placemark_input widget
        if not name:
            self.status.showMessage("Enter a placemark name first")
            return

        self.state.busy("Generating map from placemark...")  # Disables buttons until worker finished or worker error

        # Calls the backend function in the first parameter by passing the second parameter as an argument
        self._worker = Worker(self.map_controller.generate_from_placemark, name)  # Map worker runs background tasks as a separate thread

        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished)  # calls the _on_map_finished function based on the return value of _generate_from_placemark
        self._worker.start()

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

        self.state.busy("Parsing route and running simulation (this may take a while)...")

        self._worker = Worker(self.map_controller.generate_from_time_nodes, name, timestep, hover)  # Calls the first function with other parameters as arguments into the first parameter
        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_map_finished)
        self._worker.start()

    def on_generate_graphs(self):
        """
        Frontend function called when the generate graphs button is pressed
        """
        if self.map_controller.simulated_route is None:
            self.status.showMessage("No route simulated yet. Please generate a map first.", 4000)
            return

        self.state.busy("Generating graphs...")
        self._worker = Worker(self.graph_controller.generate_graphs)
        self._worker.progress.connect(self.status.showMessage)
        self._worker.finished.connect(self._on_graphs_finished)
        self._worker.start()

    def _on_map_finished(self, result: WorkerResult):
        """
        After map is generated, load it in the viewer
        """
        if result.error:
            self.state.idle(f"Worker error: {str(result.error)}")
            return

        filepath = result.value
        try:
            if not filepath:
                raise RuntimeError("No file returned from worker")
            url = QUrl.fromLocalFile(str(filepath))
            self.map_controller.webview.load(url)
            self.status.showMessage(f"Loaded: {filepath}", 5000)

            self.graph_controller.simulated_route = self.map_controller.simulated_route
        except Exception as e:
            self.status.showMessage(f"Error loading map: {e}")
        finally:
            self.state.idle()

    def _on_graphs_finished(self, result: WorkerResult):
        """
        After graphs are generated, load them in the viewer
        """
        if result.error:
            self.state.idle(f"Worker error: {str(result.error)}")
            return
        self.state.idle("Graphs generated successfully")


def run_app():
    """
    Launches the PyQT application
    """
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_app()
