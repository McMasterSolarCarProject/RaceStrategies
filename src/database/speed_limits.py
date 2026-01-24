import numpy as np
from scipy.signal import savgol_filter
from .fetch_route_intervals import fetch_route_intervals
import sqlite3
import os
import csv


def get_speed_limits(placemark_name: str) -> list[tuple[float, float]]:
    """
    Reads speed limit data from CSV for the given placemark.
    Returns a list of tuples (distance_index, speed_limit).
    """
    limits_path = f"data/limits/{placemark_name} Limits.csv"
    if os.path.exists(limits_path):
        with open(limits_path, "r") as file:
            reader = csv.reader(file)
            speed_limits = [(float(row[1]), float(row[2])) for row in reader]
        speed_limits.sort(key=lambda x: x[0])  # Ensures all speed limit data is sorted in order of index
    else:
        print(f"WARNING: Missing speed limits for {placemark_name}")
        speed_limits = []
    return speed_limits


def lookup_speed_limit(speed_limits: list, tdist: float, limit_index: int = 0) -> tuple[float, int]:
    """
    Look up the speed limit for a given distance.
    """
    if not speed_limits:
        return -1, 0
    
    while limit_index + 1 < len(speed_limits) and speed_limits[limit_index][0] <= tdist:
        limit_index += 1
    
    return speed_limits[limit_index][1], limit_index


def curvature_speed_limits(lats, lons, elevs, azimuths, s, window=31, poly=3, mu=0.90, g=9.81):
    """Calculate speed limits based on road curvature."""
    azimuths = np.radians(np.array(azimuths))
    lats = np.array(lats)
    lons = np.array(lons)
    elevs = np.array(elevs)
    s = np.array(s)
    
    # Convert lat/lon/elev to x/y/z
    x = np.zeros_like(s)
    y = np.zeros_like(s)
    z = elevs - elevs[0]
    for i in range(1, len(s)):
        segment_length = s[i] - s[i-1]
        x[i] = x[i-1] + segment_length * np.sin(azimuths[i-1])
        y[i] = y[i-1] + segment_length * np.cos(azimuths[i-1])
    
    x = savgol_filter(x, window, poly)
    y = savgol_filter(y, window, poly)
    z = savgol_filter(z, window, poly)

    # Calculate gradients
    x_s = np.gradient(x, s)
    y_s = np.gradient(y, s)
    z_s = np.gradient(z, s)

    x_ss = np.gradient(x_s, s)
    y_ss = np.gradient(y_s, s)
    z_ss = np.gradient(z_s, s)

    # Curvature: kappa = |v x a| / |v|^3
    cross_x = y_s * z_ss - z_s * y_ss
    cross_y = z_s * x_ss - x_s * z_ss
    cross_z = x_s * y_ss - y_s * x_ss
    
    numerator = np.sqrt(cross_x**2 + cross_y**2 + cross_z**2)
    v = np.sqrt(x_s**2 + y_s**2 + z_s**2 + 1e-16)
    curvature = numerator / (v ** 3)
    curvature = np.clip(curvature, 1e-4, 0.2)

    # Speed limit: vmax = sqrt(mu*g*cos(theta)/kappa)
    theta = np.arctan2(z_s, np.sqrt(x_s**2 + y_s**2))
    speed_limit = np.sqrt(mu * g * np.cos(theta) / curvature) * 3.6
    speed_limit = savgol_filter(speed_limit, 11, poly)
    speed_limit = np.clip(speed_limit, 0, 120)
    
    return speed_limit

def update_curvature_speed_limits(placemark_name: str, display: bool=False, db_path: str="ASC_2024.sqlite") -> None:
    """Update speed limits in database based on road curvature."""
    
    # Fetch route segments
    intervals = fetch_route_intervals(placemark_name)
    segments = intervals.segments
    
    # Extract coordinate data
    lats = np.array([seg.p1.lat for seg in segments])
    lons = np.array([seg.p1.lon for seg in segments])
    elevs = np.array([seg.elevation for seg in segments])
    dists = np.array([seg.tdist for seg in segments])
    azimuths = np.array([seg.azimuth for seg in segments])
    
    # Calculate speeds
    speeds = curvature_speed_limits(lats, lons, elevs, azimuths, dists)
    
    # Prepare batch update data
    update_data = [(float(speeds[i]), placemark_name, segments[i].id) for i in range(len(segments))]
    
    # Batch update database
    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.executemany(
            "UPDATE route_data SET speed_limit = MIN(speed_limit, ?) WHERE placemark_name = ? AND id = ?",
            update_data
        )
        db.commit()
    
    if display:
        import matplotlib.pyplot as plt
        low_speed_mask = speeds < 80
        
        plt.figure(figsize=(10, 6))
        plt.plot(dists/1000, speeds, color='blue', linewidth=1, label='Curvature Speed Limit')
        plt.scatter(dists[low_speed_mask]/1000, speeds[low_speed_mask],
                    color='red', s=20, label='Low-Speed Zones (<80 km/h)')
        plt.xlabel('Distance (km)')
        plt.ylabel('Speed Limit (km/h)')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.show()

def update_speed_limits_from_csv(placemark_name, db_path: str = "ASC_2024.sqlite") -> None:
    """Update speed limits in existing database from CSV files."""
    print(f"Updating speed limits from CSV files...")
    
    placemark = fetch_route_intervals(placemark_name, db_path=db_path)
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        speed_limits = get_speed_limits(placemark_name)
        update_data = []
        limit_index = 0
        for s in placemark.segments:

            speed_limit, limit_index = lookup_speed_limit(speed_limits, s.tdist, limit_index)
            update_data.append((speed_limit, placemark_name, s.id))
            # update_data = [(float(speeds[i]), placemark_name, segments[i].id) for i in range(len(placemark.segments))]
    
        cursor.executemany(
            "UPDATE route_data SET speed_limit = ? WHERE placemark_name = ? AND id = ?",
            update_data
        )

    
    print("Speed limits updated.")

if __name__ == "__main__":
    update_speed_limits_from_csv("A. Independence to Topeka")
    update_curvature_speed_limits("A. Independence to Topeka", display= True)
    # update_curvature_speed_limits("A. Independence to Topeka", display= True)
    # lat,lon,dist,az,elev = [],[],[],[],[]
    # with open("data\generated\A. Independence to Topeka.csv",'r') as file:
    #     data = [line.strip().split(',') for line in file]
    # for i in range(2,len(data)):
    #     lat.append(float(data[i][0]))
    #     lon.append(float(data[i][1]))
    #     elev.append(float(data[i][4]))
    #     dist.append(float(data[i][2]))
    #     az.append(float(data[i][3]))
    # speeds = curvature_speed_limits(lat,lon,elev, az, dist)
    
    # import matplotlib.pyplot as plt
    # speeds = np.array(speeds)
    # dist = np.array(dist)

    # plt.figure(figsize=(10,6))
    # plt.plot(dist/1000, speeds, color='blue', linewidth=1, label='Raw Speed Limit')
    # plt.grid(True, linestyle='--', alpha=0.6)
    # low_speed_mask = speeds < 80
    # plt.scatter(dist[low_speed_mask]/1000, speeds[low_speed_mask],
    #         color='red', s=20, label='Low-Speed Zones (<80 km/h)')
    # plt.tight_layout()
    # plt.show()