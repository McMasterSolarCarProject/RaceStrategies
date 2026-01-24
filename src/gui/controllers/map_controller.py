import os

from PyQt5.QtWidgets import QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from ..route_map import RouteMap
from ...database.fetch_route_intervals import fetch_route_intervals
from ...engine.interval_simulator import SSInterval


# make this into a widget
class MapController(QWidget):
    DEFAULT_DB_PATH = "ASC_2024.sqlite"

    def __init__(self, maps_dir: str, parent=None):
        super().__init__(parent)
        self.maps_dir = maps_dir
        self.simulated_route = None
        # Web view for the folium HTML
        self.webview = QWebEngineView()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.webview)
        self.setLayout(self.layout)

    def generate_from_placemark(self, name: str, db_path: str = DEFAULT_DB_PATH, split_at_stops: bool = False) -> str:
        """
        Backend function for generating from the placemark with the same name as the given argument.
        Saves the map to a html output file.
        """
        rm = RouteMap()
        rm.generate_from_placemark(name, db_path=db_path, layered=split_at_stops)
        self.simulated_route = None
        return self._save(rm, "gui_map_placemark")

    def generate_from_time_nodes(self, name: str, timestep: float, hover: bool, db_path: str = DEFAULT_DB_PATH, split_at_stops: bool = False) -> str:
        """
        Backend function to generate map with the node simulations.
        Saves the map to a html output file.
        """
        # parse route
        rm = RouteMap()
        self.simulated_route = rm.generate_simulated(name, timestep=timestep, hover=hover, db_path=db_path, layered=split_at_stops)
        return self._save(rm, "gui_map_time_nodes")

    def _save(self, rm: RouteMap, filename: str) -> str:
        """
        Function that saves the generated html file of the map in the map directory
        """
        out = os.path.join(self.maps_dir, filename)
        rm.save_map(out)
        # Return absolute path to saved file
        return os.path.abspath(out + ".html")
