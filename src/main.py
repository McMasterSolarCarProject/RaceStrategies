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
    remake = False
    if remake:
        start = time.time()
        init_route_db(remake= remake)
        print(f"Finished creating Database: {time.time()-start}")
        update_target_velocity("A. Independence to Topeka")
        print(f"Finished updating values: {time.time()-start}")

    current_tz = timezone("US/Eastern")
    current_time: datetime = datetime.datetime.now(tz=current_tz)
    interval = parse_route_table("A. Independence to Topeka")
    interval.simulate_interval()

    interval.plot("dist", "velocity.kmph", 'd_v')
    input()



if __name__ == "__main__":
    main()