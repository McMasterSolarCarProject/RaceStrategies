class Checkpoint:
    def __init__(
        self,
        lat: float,
        lon: float,
        distance: float,
        azimuth: float,
        elevation: float,
        ghi: int,
        wind_dir: float,
        wind_speed: float,
        speed_limit: float
    ):
        self.lat = lat
        self.lon = lon
        self.distance = distance
        self.azimuth = azimuth
        self.elevation = elevation
        self.ghi = ghi
        self.wind_dir = wind_dir
        self.wind_speed = wind_speed
        self.speed_limit = speed_limit

    def __str__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Distance: {round(self.distance,2)} \n| Azimuth: {round(self.azimuth,1)} | Elevation: {round(self.elevation,1)} | ghi: {self.ghi} \n| Wind Dir: {self.wind_dir} | Wind Speed: {self.wind_speed} | Speed Limit: {self.speed_limit}"

    def __repr__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Distance: {round(self.distance,2)} \n| Azimuth: {round(self.azimuth,1)} | Elevation: {round(self.elevation,1)} | ghi: {self.ghi} \n| Wind Dir: {self.wind_dir} | Wind Speed: {self.wind_speed} | Speed Limit: {self.speed_limit}"
