CREATE TABLE route_data (
        placemark_name TEXT not null,
        id integer not null,
        lat float not null,
        lon float not null,
        elevation float not null,
        distance float not null,
        speed_limit float not null,
        stop_type string,
        ghi int,
        wind_dir float,
        wind_speed float,
        speed float,
        torque float,
        PRIMARY KEY (placemark_name, id)
    );