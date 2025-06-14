class Checkpoint:
    def __init__(self, lat: float, lon: float, distance: float, azimuth: float, elevation: float, ghi: int, winddir: float, windspeed: float, speedlimit: float):
        assert isinstance(lat, (int, float)), "Latitude must be a number"
        assert isinstance(lon, (int, float)), "Longitude must be a number"
        assert isinstance(distance, (int, float)), "Distance must be a number"
        assert isinstance(azimuth, (int, float)), "Azimuth must be a number"
        assert isinstance(elevation, (int, float)), "Elevation must be a number"
        assert isinstance(ghi, int), "GHI must be an integer"
        assert isinstance(winddir, (int, float)), "Wind direction must be a number"
        assert isinstance(windspeed, (int, float)), "Wind speed must be a number"
        assert isinstance(speedlimit, (int, float)), "Speed limit must be a number"

        self.lat = lat
        self.lon = lon
        self.distance = distance
        self.azimuth = azimuth
        self.elevation = elevation
        self.ghi = ghi
        self.winddir = winddir
        self.windspeed = windspeed
        self.speedlimit = speedlimit

    def __str__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Distance: {round(self.distance,2)} \n| Azimuth: {round(self.azimuth,1)} | Elevation: {round(self.elevation,1)} | ghi: {self.ghi} \n| Wind Dir: {self.winddir} | Wind Speed: {self.windspeed} | Speed Limit: {self.speedlimit}"

    def __repr__(self):
        return f"Checkpoint(lat={self.lat}, lon={self.lon}, distance={self.distance}, azimuth={self.azimuth}, elevation={self.elevation}, ghi={self.ghi}, winddir={self.winddir}, windspeed={self.windspeed}, speedlimit={self.speedlimit})"
