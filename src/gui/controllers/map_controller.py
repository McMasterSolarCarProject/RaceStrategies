import os

from PyQt5.QtWidgets import QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from ..route_map import RouteMap
from ...database.fetch_route_intervals import fetch_route_intervals


# make this into a widget
class MapController(QWidget):
    def __init__(self, maps_dir: str, parent=None):
        super().__init__(parent)
        self.maps_dir = maps_dir
        self.simulated_route = None
        # Web view for the folium HTML
        self.webview = QWebEngineView()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.webview)
        self.setLayout(self.layout)

    def generate_from_placemark(self, name: str) -> str:
        """
        Backend function for generating from the placemark with the same name as the given argument.
        Saves the map to a html output file.
        """
        rm = RouteMap()
        rm.generate_from_placemark(name)
        self.simulated_route = None
        return self._save(rm, "gui_map_placemark")

    def generate_from_time_nodes(self, name: str, timestep: float, hover: bool) -> str:
        """
        Backend function to generate map with the node simulations.
        Saves the map to a html output file.
        """
        # parse route
        route = fetch_route_intervals(name)[0]

        # simulate (this mutates route and adds .segments and .time_nodes)
        # use TIME_STEP kwarg like existing code
        if hasattr(route, "simulate_interval"):
            route.simulate_interval(TIME_STEP=timestep)
            self.simulated_route = route

        print(f"Length of time nodes: {len(route.time_nodes)}")
        rm = RouteMap()
        # use hover options
        rm.generate_from_time_nodes(route.segments, route.time_nodes, hover_tooltips=hover)
        return self._save(rm, "gui_map_time_nodes")

    def _save(self, rm: RouteMap, filename: str) -> str:
        """
        Function that savs the generated html file of the map in the map directory
        """
        out = os.path.join(self.maps_dir, filename)
        rm.save_map(out)
        # Return absolute path to saved file
        return os.path.abspath(out + ".html")
