import sqlite3
from pytz import timezone
import time
import datetime
from .engine.kinematics import Coordinate, Speed
from .engine.interval_simulator import SSInterval  # Adjust as needed
from .engine.nodes import Segment
from .database.init_route_table import init_route_db
from .database.parse_route_table import parse_route_table
from .database.update_velocity import update_target_velocity

def main():
    start = time.time()

    table_remake_flag = False
    if table_remake_flag:
        init_route_db(remake= table_remake_flag)
        print(f"Finished creating Database: {time.time()-start}")
        update_target_velocity("A. Independence to Topeka")
        print(f"Finished updating velocity and torque values: {time.time()-start}")

    current_tz = timezone("US/Eastern")
    current_time: datetime = datetime.datetime.now(tz=current_tz)
    intervals = parse_route_table("A. Independence to Topeka", stops=True, max_segments=1000)
    for i in range(len(intervals)):
        print(f"Simulating Interval {i+1} of {len(intervals)}")
        intervals[i].simulate_interval()
        intervals[i].plot("dist", ["speed.kmph", "segment.speed_limit.kmph", "segment.v_eff.kmph"], "velocity_comparison")
    print(f"Completed Display: {time.time()-start}")

    input()



if __name__ == "__main__":
    main()