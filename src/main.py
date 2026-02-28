import time

from .engine.interval_simulator import SSInterval  # Adjust as needed
from .database import  fetch_route_intervals
from .engine.interval_simulator import join_intervals


def main():
    start = time.perf_counter()
    # update_traffic("A. Independence to Topeka")
    # init_route_db(remake= False)
    # # # placemarks = ["A. Independence to Topeka"]
    # placemarks = parse_kml_file()
    # for placemark in placemarks:
    #     if True:  # Set to True to update velocity data
    #         # print(f"Updating velocity data for {placemark}")
    #         upload_speed_limit(placemark)
    #         update_target_velocity(placemark)
    #         # update_traffic(placemark)
    # print(f"Finished creating Database: {time.perf_counter()-start}")


    # current_tz = timezone("US/Eastern")
    # current_time: datetime = datetime.datetime.now(tz=current_tz)

    intervals = fetch_route_intervals("A. Independence to Topeka", split_at_stops=True, max_nodes=None, db_path="ASC_2024.sqlite")
    intervals = [intervals] if type(intervals) is SSInterval else intervals
    print(len(intervals))
    # intervals = intervals
    for i in range(min(100000, len(intervals))):
        print(f"Simulating Interval {i+1} of {len(intervals)}")
        intervals[i].simulate_interval()
        intervals[i].plot("dist", ["speed.kmph", "segment.speed_limit.kmph", "segment.v_eff.kmph"], f"velocity_comparison_{i+1}")
        # intervals[i].plot("time", ["speed.kmph", "segment.speed_limit.kmph", "segment.v_eff.kmph"], "velocity_comparison")
        print("\n\n")
        # intervals[i].plot("dist", ["speed.kmph"], f"interval_{i+1}_velocity")
    master = join_intervals(intervals)
    print(f"{time.perf_counter()-start}")
    master.plot("dist", ["speed.kmph", "segment.v_eff.kmph"], "velocity_comparison", brake=False)
    # master.plot("dist", ["speed.kmph", "segment.speed_limit.kmph", "segment.v_eff.kmph"], f"master_interval_velocity")
    # master.plot("dist", ["segment.elevation"], f"master_interval_velocity")
    print(f"Completed Display: {time.perf_counter()-start}")
    
    import matplotlib.pyplot as plt
    plt.show()



if __name__ == "__main__":
    main()