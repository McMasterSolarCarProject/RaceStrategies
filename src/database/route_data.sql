CREATE TABLE route_data (
        segment_id integer not null,
        id integer not null,
        lat float not null,
        lon float not null,
        distance float not null,
        speed_limit float not null,
        azimuth float not null,
        elevation float not null,
        ghi int,
        wind_dir float,
        wind_speed float,
        PRIMARY KEY (segment_id, id)
    );