# Pulls data from sqlite route data to identify objects of interest

import sqlite3
import requests
import json
import time
from math import cos, asin, sqrt, pi
from ..engine.kinematics import Coordinate, Displacement
from .parse_route_table import parse_route_table

BATCH_SIZE = 20 # Reduced to avoid rate limiting

# --- DEBUG SETUP ---
DEBUG = True # Toggle this to False to disable debug output

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
        # Fixed bbox format
        bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"
        query_string += f'\nnode[highway~"{"|".join(types)}"]{bbox_str};'
    query_string += '\n);out body;'

    return query_string

def overpass_batch_request(points, max_retries=20, base_delay=5):
    '''
    Makes a Overpass request with retries.
    Retries on:
      - 504 Gateway Timeout
      - 429 Too Many Requests
      - transient network errors
    Always returns a list.
    '''
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = overpass_query(points)

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                overpass_url,
                params={'data': query},
                timeout=60
            )

            # Retry-worthy HTTP errors
            if response.status_code in (429, 504):
                delay = base_delay * attempt
                debug_print(
                    f"Overpass HTTP {response.status_code}, "
                    f"retry {attempt}/{max_retries} in {delay}s..."
                )
                time.sleep(delay)
                continue

            response.raise_for_status()

            data = response.json()

            if 'elements' not in data:
                debug_print("Overpass response missing 'elements'")
                return []

            debug_print(
                f"SUCCESS ({len(data['elements'])} elements)"
            )
            return data['elements']

        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            delay = base_delay * attempt
            debug_print(
                f"Network error: {e}, retry {attempt}/{max_retries} "
                f"in {delay}s..."
            )
            time.sleep(delay)

        except json.JSONDecodeError as e:
            debug_print(f"JSON decode error: {e}")
            debug_print(f"Response snippet:\n{response.text[:300]}")
            return []

        except requests.exceptions.RequestException as e:
            debug_print(f"Fatal request error: {e}")
            return []

    debug_print("Max retries exceeded, returning empty result")
    return []


def lookup(nodes):
    '''
    Creates a hashmap for efficient node searching.
    '''
    lookup = {}
    for node in nodes:
        lat_key = round(node['lat'], 5)
        lon_key = round(node['lon'], 5)

        key = (lat_key, lon_key)
        
        if key not in lookup:
            lookup[key] = []
        lookup[key].append(node)
    
    return lookup

def find_closest_node(lookup, coord, threshold=50):
    '''
    Efficiently finds the closest node.
    '''
    matches = []

    # search main grid cell
    rounded_key = (round(coord.lat, 5), round(coord.lon, 5))
    keys_to_check = [rounded_key]

    # search 8 neighbors
    lat_step = 0.00001
    lon_step = 0.00001

    for lat_offset in [-lat_step, 0, lat_step]:
        for lon_offset in [-lon_step, 0, lon_step]:
            neighbor_key = (
                round(coord.lat + lat_offset, 5),
                round(coord.lon + lon_offset, 5)
            )
            if neighbor_key not in keys_to_check:
                keys_to_check.append(neighbor_key)

    # check all keys
    for key in keys_to_check:
        if key in lookup:
            for node in lookup[key]:
                node_coord = Coordinate(node["lat"], node["lon"])
                distance = Displacement(coord, node_coord).mag
                if distance <= threshold:
                    matches.append(node)

    return matches

def regroup(batchs, coords, threshold = 50):
    '''
    Groups nodes around original coordinate points.
    Args:
        batchs: Dict containing information ('id', 'lat', 'lon') on found nodes
        points: List containing original coordinate points [(reference_point)]
        threshold: Max distance a node can be from a point
    Returns:
        clusters: Dict {reference_point: [nodes]}
    '''
    # Flatten all nodes from batches
    all_nodes = []
    for batch in batchs:
        all_nodes.extend(batch)
    #Unduplicate 
    unique = {}
    for n in all_nodes:
        unique[n['id']] = n
    all_nodes = list(unique.values())
    debug_print(f"Total nodes from Overpass: {len(all_nodes)}")
    debug_print(f"Total coordinates to check: {len(coords)}")
    
    if not all_nodes:
        debug_print("No nodes found from Overpass")
        return {coord: [] for coord in coords}
    
    # Create spatial lookup for efficient searching
    spatial_lookup = lookup(all_nodes)
    
    clusters = {coord: [] for coord in coords}
    matches_found = 0
    
    for coord in coords:
        nearby = find_closest_node(spatial_lookup, coord, threshold)
        if nearby:
            matches_found += 1
            clusters[coord].extend(nearby)


    debug_print(f"Coordinates with traffic nodes: {matches_found}/{len(coords)}")
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
    priority_types = {}

    for ref, nodes in clusters.items():
        best_priority = float('inf')
        best_type = None

        for node in nodes:
            stop_type = node.get('tags', {}).get('highway')
            if stop_type is None:
                continue

            p = stop_priority.get(stop_type, float('inf'))
            if p < best_priority:
                best_priority = p
                best_type = stop_type

        priority_types[ref] = best_type

    return priority_types

def debugging_clusters(clusters):
    '''
    Prints each cluster (reference point) and the nodes surrounding it.
    Args:
        clusters: Dict {reference_point: [nodes]}
    Returns:
        None
    '''
    for i, (point, nodes) in enumerate(clusters.items(), 1):
        debug_print(f"\nCluster {i} (Reference: {point.lat:.6f}, {point.lon:.6f}):")
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
            debug_print(f"\nCluster at {ref}:")
            debug_print(f"  Priority node ID: {node['id']}")
            debug_print(f"  Type: {node.get('tags', {}).get('highway')}")
        else:
            debug_print(f"\nCluster at {ref}: No priority nodes found")
    debug_print()


def update_traffic(segment_id):
    traffic_data = []
    placemark = parse_route_table(segment_id)
    coord_points = [c.p1 for c in placemark.segments]
    batch_bboxes = [generate_boundary(coord.lat, coord.lon) for coord in coord_points]
    for i in range(0, len(batch_bboxes), BATCH_SIZE):
        #for quick check
        #if i == 100:
            #break
        batch = batch_bboxes[i:i+BATCH_SIZE]
        try:
            traffic_data.append(overpass_batch_request(batch))
            print(f"Data up to {i + BATCH_SIZE}") 
            #break, collects all traffic data
        except Exception as e:
            print(f"Error fetching batch: {e}")
            traffic_data.append([None] * len(batch))

    grouped = regroup(traffic_data, coord_points)
    priority_types = priority_stops(grouped)

    for ref, stop_type in priority_types.items():
        if stop_type is None:
            continue

        print(f"{ref}:\t{stop_type}")

        db = sqlite3.connect('data.sqlite')
        cursor = db.cursor()
        cursor.execute(
            'UPDATE route_data SET stop_type = ? WHERE lat = ? AND lon = ?',
            (stop_type, ref.lat, ref.lon)
        )
        db.commit()
        db.close()




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

    update_traffic("A. Independence to Topeka")

if __name__ == "__main__":
    main()