import numpy as np
from scipy.signal import savgol_filter
from .fetch_route_intervals import fetch_route_intervals
import sqlite3
import csv

def curvature_speed_limits(lats, lons, elevs, azimuths, s, window=31, poly=3, mu = 0.90, g = 9.81):
    #lat lon elev --> x y z
    azimuths = np.radians(np.array(azimuths))
    lats = np.array(lats)
    lons = np.array(lons)
    elevs = np.array(elevs)
    s = np.array(s)
    
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

    #curvature
    s = np.asarray(s)

    x_s = np.gradient(x,s)
    y_s = np.gradient(y,s)
    z_s = np.gradient(z,s)

    x_ss = np.gradient(x_s,s)
    y_ss = np.gradient(y_s,s)
    z_ss = np.gradient(z_s,s)

    # kappa = |v x a| / |v|^3
    cross_x = y_s*z_ss - z_s*y_ss
    cross_y = z_s * x_ss - x_s * z_ss
    cross_z = x_s * y_ss - y_s * x_ss
    numerator = np.sqrt(cross_x**2 + cross_y**2 + cross_z**2)
    v = np.sqrt(x_s**2 + y_s**2 + z_s**2 + 1e-16)
    denominator = v ** 3
    curvature = numerator / denominator
    curvature = np.clip(curvature, 1e-4, 0.2)

    #vmax = sqrt(mu*g*cos(theta)/kappa)
    theta = np.arctan2(z_s, np.sqrt(x_s**2 + y_s**2))
    speed_limit = list(np.sqrt(mu * g * np.cos(theta) / curvature) * 3.6)
    speed_limit = savgol_filter(speed_limit, 11, poly)
    speed_limit = np.clip(speed_limit, 0, 120)
    return [float(speed) for speed in speed_limit]

def update_curvature_speed_limits(placemark_name: str, display: bool= False):
    # for now just pick one with epm of 100
    lat,lon,dist,az,elev = [],[],[],[],[]
    # with open("data\generated\A. Independence to Topeka.csv",'r') as file:
    #     data = [line.strip().split(',') for line in file]
    data = fetch_route_intervals(placemark_name).segments
    for i in range(len(data)):
        lat.append(data[i].p1.lat)
        lon.append(float(data[i].p1.lon))
        elev.append(float(data[i].elevation))
        dist.append(float(data[i].tdist))
        az.append(float(data[i].azimuth))
    speeds = curvature_speed_limits(lat,lon,elev, az, dist)


    db = sqlite3.connect('data.sqlite')
    cursor = db.cursor()
    for i, segment in enumerate(data):
        # nodes = sim_velocity_an_shi(segment, segment.speed_limit)
        if speeds[i] <= 5:
            # print("curvature shi",speeds[i], i, segment.id)
            pass
        cursor.execute(
            '''
            UPDATE route_data
            SET speed_limit = MIN(speed_limit, ?)
            WHERE segment_id = ? AND id = ?
            ''', (speeds[i], placemark_name, segment.id))
    db.commit()
    db.commit()
    db.close()

    if display:
        import matplotlib.pyplot as plt
        speeds = np.array(speeds)
        dist = np.array(dist)

        plt.figure(figsize=(10,6))
        plt.plot(dist/1000, speeds, color='blue', linewidth=1, label='Raw Speed Limit')
        plt.grid(True, linestyle='--', alpha=0.6)
        low_speed_mask = speeds < 80
        plt.scatter(dist[low_speed_mask]/1000, speeds[low_speed_mask],
                color='red', s=20, label='Low-Speed Zones (<80 km/h)')
        plt.tight_layout()
        plt.show()

def update_speed_limits_from_csv(placemark_name: str, db_path: str = "data.sqlite") -> None:
    """Update speed limits in existing database from CSV files."""
    print(f"Updating speed limits from CSV files...")
    
    
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        
        # Read speed limits from CSV
        with open(f"data/limits/{placemark_name} Limits.csv", "r") as file:
            reader = csv.reader(file)
            speed_limits = [(float(row[1]), float(row[2])) for row in reader]
        
        # Update speed limits in database for this placemark
        for i, (distance, speed) in enumerate(speed_limits):
            next_distance = speed_limits[i + 1][0] if i + 1 < len(speed_limits) else float('inf')
            cursor.execute(
                "UPDATE route_data SET speed_limit = ? WHERE segment_id = ? AND cumulative_distance >= ? AND cumulative_distance < ?",
                (speed, placemark_name, distance, next_distance)
            )
    
    print("Speed limits updated.")

if __name__ == "__main__":
    update_speed_limits_from_csv("A. Independence to Topeka")
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