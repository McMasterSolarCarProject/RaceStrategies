import sqlite3
from pytz import timezone
import datetime
from .main_temp import get_route, route_to_ssinterval

def main():
    current_tz = timezone("US/Eastern")
    current_time: datetime = datetime.datetime.now(tz=current_tz)
    route = get_route(1)
    interval = route_to_ssinterval(route)
    interval.simulate_interval()

    # optionally: visualize
    from .utils.graph import plot_multiple_datasets
    plot_multiple_datasets([interval.time_nodes, interval.brakingNodes], "dist", "kmph", 'd_v')

if __name__ == "__main__":
    main()