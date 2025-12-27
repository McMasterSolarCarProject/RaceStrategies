import os
from ..route_map import RouteMap
from ...database.parse_route_table import parse_route_table


class MapController:
    def __init__(self, maps_dir: str):
        self._maps_dir = maps_dir
    
    @property
    def maps_dir(self) -> str:
        """
        Directory that holds the html files for the generated routes
        """
        return self._maps_dir

    def generate_from_placemark(self, name: str) -> str:
        """
        Backend function for generating from the placemark with the same name as the given argument.
        Saves the map to a html output file.
        """
        rm = RouteMap()
        rm.generate_from_placemark(name)
        return self._save(rm, "gui_map_placemark")

    def generate_from_time_nodes(self, name: str, timestep: float, hover: bool) -> str:
        """
        Backend function to generate map with the node simulations.
        Saves the map to a html output file.
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
        return self._save(rm, "gui_map_time_nodes")

    def _save(self, rm: RouteMap, filename: str) -> str:
        """
        Function that savs the generated html file of the map in the map directory
        """
        out = os.path.join(self._maps_dir, filename)
        rm.save_map(out)
        # Return absolute path to saved file
        return os.path.abspath(out + ".html")
