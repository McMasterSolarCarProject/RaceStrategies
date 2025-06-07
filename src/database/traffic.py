# Pulls data from sqlite route data to identify objects of interest

import sqlite3
import requests
import json
import time
from math import cos, asin, sqrt, pi

# --- DEBUG SETUP ---
DEBUG = False  # Toggle this to False to disable debug output

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# --------------------

file = "data.sqlite"

stop_priority = {
    "stop": 1,
    "traffic_signals": 2,
    "crossing": 3,
    "give_way": 4,
    "bus_stop": 5
}

def overpass_query(points):
    types = ["stop", "crossing", "traffic_signals", "bus_stop", "give_way"]

    query_string = "[out:json];("
    for bbox in points:
        query_string += f'''\nnode["highway"="{'|'.join(types)}"]{bbox};'''
    query_string += '''\n);out body;'''

    return query_string

def overpass_batch_request(points):
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

def haversine(point1, point2):
    r = 6371
    p = pi / 180
    a = 0.5 - cos((point2['lat']-point1['lat'])*p)/2 + \
        cos(point1['lat']*p) * cos(point2['lat']*p) * (1 - cos((point2['lon'] - point1['lon'])*p))/2
    return 2 * r * asin(sqrt(a))

def priority_stop(data_list):
    stops = []
    for data in data_list:
        stop = None
        for sign in data:
            sign_type = sign.get('tags', {}).get('highway')
            if sign_type in stop_priority:
                if stop is None or stop_priority[sign_type] < stop_priority[stop]:
                    stop = sign_type
        stops.append(stop)

    return stops

def generate_boundary(lat: float, lon: float):
    radius = 0.0001
    north = lat + radius
    south = lat - radius
    east = lon + radius
    west = lon - radius

    boundaries = (south, west, north, east)
    return boundaries

def main():
    start = time.time_ns()
    # ... do something here ...
    end = time.time_ns()
    debug_print(f"Elapsed time: {(end - start)/1_000_000_000} seconds")

if __name__ == "__main__":
    main()
