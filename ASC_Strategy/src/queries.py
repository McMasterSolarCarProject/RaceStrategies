import sqlite3

from classes import Checkpoint, Route


def get_speed_limits(segment_id):
    conn = sqlite3.connect("data.sqlite")
    cursor = conn.cursor()

    query = """
    SELECT id, distance, speed_limit FROM route_data
    WHERE segment_id = ?
    ORDER BY id
    """
    cursor.execute(query, (segment_id,))

    results = cursor.fetchall()
    # if results:
    #     print(f"Speed limits for segment {segment_id}: {results}")
    # else:
    #     print("No speed limit data found for the specified segment.")

    cursor.close()
    conn.close()

    out = {}
    for row in results:
        out[row[1]] = row[2]

    return out


def get_weather_conditions(segment_id):
    conn = sqlite3.connect("data.sqlite")
    cursor = conn.cursor()

    query = """
    SELECT ghi, wind_speed, wind_dir FROM route_data
    WHERE segment_id = ?
    ORDER BY id
    """
    cursor.execute(query, (segment_id,))

    results = cursor.fetchall()
    if results:
        print(f"Weather conditions for segment {segment_id}:")
        for result in results:
            print(f"GHI: {result[0]} W/mÂ², Wind Speed: {result[1]} km/h, Wind Direction: {result[2]} degrees")
    else:
        print("No weather data found for the specified segment.")

    cursor.close()
    conn.close()

    return results


def get_route(segment_id):
    conn = sqlite3.connect("data.sqlite")
    cursor = conn.cursor()

    query = """
    SELECT segment_id, lat, lon, distance, azimuth, elevation, ghi, wind_dir, wind_speed, speed_limit FROM route_data
    WHERE segment_id = ?
    ORDER BY id
    """
    cursor.execute(query, (segment_id,))


    results = cursor.fetchall()
    # if results:
    #     print(f"Route for segment {segment_id}:")
    #     for result in results:
    #         print(f"ID: {result[0]}, Azimuth: {result[1]} degrees, Elevation: {result[2]} meters, Distance: {result[3]} meters")
    # else:
    #     print("No data found for the specified segment.")

    checkpoints = []
    for result in results:
        checkpoints.append(Checkpoint(
            result[1],
            result[2],
            result[3],
            result[4],
            result[5],
            result[6],
            result[7],
            result[8],
            result[9],
        ))

    cursor.close()
    conn.close()

    return Route(result[0], checkpoints)