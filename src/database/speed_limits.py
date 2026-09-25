import sqlite3
import os
import csv
from .route_table import RouteTable


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
        return 60, 0
    
    while limit_index + 1 < len(speed_limits) and speed_limits[limit_index][0] <= tdist:
        limit_index += 1
    
    return speed_limits[limit_index][1], limit_index


def update_speed_limits_from_csv(placemark_name: str, db_path: str) -> None:
    print(f"Updating speed limits for {placemark_name} from CSV...")
    speed_limits = get_speed_limits(placemark_name)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        rows = RouteTable.fetch_route_rows(placemark_name, cursor)

        limit_index = 0
        for row in rows:
            speed_limit, limit_index = lookup_speed_limit(speed_limits, row.distance, limit_index)
            row.speed_limit = speed_limit

        RouteTable.update_rows(rows, cursor)

    print(f"Speed limits updated for {placemark_name} in database {db_path}.")

# if __name__ == "__main__":
#     update_speed_limits_from_csv("A. Independence to Topeka")
#     update_curvature_speed_limits("A. Independence to Topeka", display= True)
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