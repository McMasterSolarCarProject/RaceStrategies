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

        self._lat = lat
        self._lon = lon
        self._distance = distance
        self._azimuth = azimuth
        self._elevation = elevation
        self._ghi = ghi
        self._winddir = winddir
        self._windspeed = windspeed
        self._speedlimit = speedlimit

    def get_lat(self) -> float:
        return self._lat

    def get_lon(self) -> float:
        return self._lon

    def get_distance(self) -> float:
        return self._distance

    def get_azimuth(self) -> float:
        return self._azimuth

    def get_elevation(self) -> float:
        return self._elevation

    def get_ghi(self) -> int:
        return self._ghi

    def get_winddir(self) -> float:
        return self._winddir

    def get_windspeed(self) -> float:
        return self._windspeed

    def get_speedlimit(self) -> float:
        return self._speedlimit

    def __str__(self):
        return f"Lat: {self._lat} | Lon: {self._lon} | Distance: {round(self._distance,2)} \n| Azimuth: {round(self._azimuth,1)} | Elevation: {round(self._elevation,1)} | ghi: {self._ghi} \n| Wind Dir: {self._winddir} | Wind Speed: {self._windspeed} | Speed Limit: {self._speedlimit}"

    def __repr__(self):
        return f"Checkpoint(lat={self._lat}, lon={self._lon}, distance={self._distance}, azimuth={self._azimuth}, elevation={self._elevation}, ghi={self._ghi}, winddir={self._winddir}, windspeed={self._windspeed}, speedlimit={self._speedlimit})"
