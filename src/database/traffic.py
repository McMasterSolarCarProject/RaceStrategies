# Pulls data from sqlite route data to identify objects of interest

import requests
import json
from math import cos, asin, sqrt, pi
from ..engine.kinematics import Coordinate, Displacement

# --- DEBUG SETUP ---
DEBUG = False # Toggle this to False to disable debug output

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# --------------------

stop_priority = {
    "stop": 1,
    "traffic_signals": 2,
    "crossing": 3,
    "give_way": 4,
    "bus_stop": 5
}

def generate_boundary(lat: float, lon: float):
    '''
    Generates a ~50m x ~50m boundary box around each coordinate point.
    Args:
        lat: the latitude at a coordinate given as a float
        lon: the longitude at a coordinate given as a float
    Returns:
        boundary: Tuple of 4 points for the boundary box (south, west, north, east)
    '''
    lat_radius = 0.00023
    lon_radius = 0.00032
    north = lat + lat_radius
    south = lat - lat_radius
    east = lon + lon_radius
    west = lon - lon_radius

    boundary = (south, west, north, east)
    return boundary

def overpass_query(points):
    '''
    Generates a query string for Overpass.
    Args:
        points: List of boundary box tuples [(south, west, north, east)]
    Returns:
        query_string: Str to be used for a Overpass request
    '''
    types = ["stop", "crossing", "traffic_signals", "bus_stop", "give_way"]

    query_string = "[out:json];("
    for bbox in points:
        query_string += f'''\nnode[highway~"{'|'.join(types)}"]{bbox};'''
    query_string += '''\n);out body;'''

    return query_string

def overpass_batch_request(points):
    '''
    Makes an Overpass request for traffic data.
    Args:
        points: List of boundary box tuples [(south, west, north, east)]
    Returns:
        data['elements']: Dict containing information ('id', 'lat', 'lon', 'tags') on found nodes
    '''
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = overpass_query(points)

    response = requests.get(overpass_url, params={'data': query})

    if response.status_code == 200:
        debug_print("SUCCESS")
        try:
            data = response.json()
            return data['elements']
        except json.JSONDecodeError as e:
            debug_print(f"Error decoding JSON: {e}")
    else:
        debug_print(f"Error: HTTP status code {response.status_code}")
        debug_print(f"Response content:\n{response.text}")
    return []

def regroup(nodes, coords, threshold = 0.055):
    '''
    Groups nodes around original coordinate points.
    Args:
        nodes: Dict containing information ('id', 'lat', 'lon') on found nodes
        points: List containing original coordinate points [(reference_point)]
        threshold: Max distance a node can be from a point
    Returns:
        clusters: Dict {reference_point: [nodes]}
    '''
    clusters = {coord : [] for coord in coords}
    print(nodes, coords)
    for node in nodes:
        min_distance = float('inf')
        closest_point = None

        for coord in coords:
            # convert point to dict for haversine function
            # point_dict = {'lat': coord[0], 'lon': coord[1]}
            node_coord = Coordinate(node["lat"], node["lon"])
            distance = Displacement(coord, node_coord).mag
            if (distance < min_distance and distance <= threshold):
                min_distance = distance
                closest_point = coord

        clusters[closest_point].append(node)
        print("something")

    return clusters

# def haversine(point1, point2):
#     '''
#     Calculates the distance between two coordinate points.
#     Args:
#         point1: Dict ['lat': float, 'lon': float]
#         point2: Dict ['lat': float, 'lon': float]
#     Returns:
#         The distance between two points in km
#     '''
#     r = 6371
#     p = pi / 180
#     a = 0.5 - cos((point2['lat']-point1['lat'])*p)/2 + cos(point1['lat']*p) * cos(point2['lat']*p) * (1 - cos((point2['lon'] - point1['lon'])*p))/2
#     return 2 * r * asin(sqrt(a))

def priority_stops(clusters):
    """
    Finds the highest priority node in each cluster based on stop_priority.
    Args:
        clusters: Dict {reference_point: [nodes]}
    Returns:
        Dict {reference_point: highest_priority_stop}
    """
    priority_nodes = {}
    
    for ref, nodes in clusters.items():
        high = None
        best_node = None
        
        for node in nodes:
            stop_type = node.get('tags', {}).get('highway')
            current = stop_priority.get(stop_type, float('inf'))
            
            if (high is None or current < high):
                high = current
                best_node = node
        
        priority_nodes[ref] = best_node
    
    return priority_nodes

def debugging_clusters(clusters):
    '''
    Prints each cluster (reference point) and the nodes surrounding it.
    Args:
        clusters: Dict {reference_point: [nodes]}
    Returns:
        None
    '''
    for i, (point, nodes) in enumerate(clusters.items(), 1):
        debug_print(f"\nCluster {i} (Reference: {point[0]:.6f}, {point[1]:.6f}):")
        debug_print(f"Nodes found: {len(nodes)}")
        for node in nodes:
            debug_print(f"  - ID: {node['id']}", end="")
            if 'tags' in node:
                tags = node['tags']
                debug_print(f" | Type: {tags.get('highway', 'unknown')}", end="")
            debug_print()

def debugging_priority(nodes):
    '''
    Prints the highest priority stop at each reference point.
    Args:
        nodes: Dict {reference_point: highest_priority_stop}
    Returns:
        None
    '''
    for ref, node in nodes.items():
        if node:
            if node:
                debug_print(f"\nCluster at {ref}:")
                debug_print(f"  Priority node ID: {node['id']}")
                debug_print(f"  Type: {node.get('tags', {}).get('highway')}")
            else:
                debug_print(f"\nCluster at {ref}: No priority nodes found")
    debug_print()

def main():
    '''
    # DEBUGGING (Should result as traffic_signal, traffic_signal, bus_stop, None)
    test = [(43.856, -79.256), (43.849, -79.28), (43.856, -79.255), (43.856, -79.257)]
    box = [generate_boundary(point[0], point[1]) for point in test]
    start = time.time_ns()
    stuff = overpass_batch_request(box)
    grouped = regroup(stuff, test)
    debugging_clusters(grouped)
    priority_nodes = priority_stops(grouped)
    debugging_priority(priority_nodes)
    end = time.time_ns()
    debug_print(f"Elapsed time: {(end - start)/1_000_000_000} seconds")
    '''

if __name__ == "__main__":
    main()