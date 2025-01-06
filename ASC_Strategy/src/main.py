from tzlocal import get_localzone
import datetime
import queries


def init_time():
    curr_tz = get_localzone()
    return curr_tz, datetime.datetime.now(tz=curr_tz)


def get_route(segment_id):
    return queries.get_route(segment_id)


def main():
    curr_tz, curr_time = init_time()
    route = get_route(1)


if __name__ == "__main__":
    main()