class Coordinate:
    def __init__(self, lon: float, lat: float, elevation: float):
        self.lon = lon
        self.lat = lat
        self.elevation = elevation

    def __str__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"

    def __repr__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"