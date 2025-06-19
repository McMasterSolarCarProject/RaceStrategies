from __future__ import annotations
import math


class Vec:
    def __init__(self, x, y, z = 0):
        self._x = x
        self._y = y
        self._z = z
        self._mag = math.sqrt(self.x ** 2 + self.y ** 2)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y
    
    @property
    def z(self):
        return self._z
    
    @property
    def mag(self):
        return self._mag
    
    def __add__(self, other: Vec):
        return Vec(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec):
        return Vec(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float):
        return Vec(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __truediv__(self, scalar: float):
        return Vec(self.x / scalar, self.y / scalar, self.z / scalar)

    def sin(self):
        return self.y / self.mag

    def cos(self):
        return self.x / self.mag

    def unit_vector(self):
        if self.mag == 0:
            print("zero div")
            return Vec(0, 1)
        return Vec(self.x / self.mag, self.y / self.mag, self.z / self.mag)

    def __str__(self):
        return f"Vector: {self.x, self.y} | Magnitude: {self.mag}"


UNIT_VEC = Vec(1, 0)
ZERO_VEC = Vec(0, 0)


class Coordinate:  # Should Be Calculated in Meters
    """Longitude, Latitude & Elevation taken from KML files"""
    def __init__(self, lat: float, lon: float, elevation: float = 0):
        self.lat = lat
        self.lon = lon
        self.elevation = elevation
        # self.position = self.gcs_to_ecef()

    # def gcs_to_ecef(self) -> Vec:
    #     # gcs = lat lon, ecef = 3D cartesian

    #     # WGS84 constants
    #     a = 6378137.0  # Equatorial radius (meters)
    #     e2 = 6.69437999014e-3  # Square of eccentricity

    #     lat = math.radians(self.lat)
    #     lon = math.radians(self.lon)
    #     elevation_m = self.elevation

    #     N = a / math.sqrt(1 - e2 * math.sin(lat)**2)

    #     x = (N + elevation_m) * math.cos(lat) * math.cos(lon)
    #     y = (N + elevation_m) * math.cos(lat) * math.sin(lon)
    #     z = (N * (1 - e2) + elevation_m) * math.sin(lat)

    #     return Vec(x, y, z)

    def __str__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"

    def __repr__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"


class Displacement(Vec):  # East-North-Up
    def __init__(self, p1: Coordinate, p2: Coordinate):
        self.p1 = p1
        self.p2 = p2
        # Surface Displacement
        super().__init__(*self.enu_vector())
        self.elevation = p2.elevation - p1.elevation
        self.gradient = Vec(self.mag, self.elevation)
        self.dist = self.gradient.mag

    def enu_vector(self):
        R = 6371000 + self.p1.elevation # mean Earth radius in meters
        lat1, lon1, lat2, lon2 = map(math.radians, [self.p1.lat, self.p1.lon, self.p2.lat, self.p2.lon])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Azimuth
        self.azimuth = math.degrees(math.atan2(math.sin(dlon) * math.cos(lat2), math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon),)) % 360

        # Haversine (Distance) Calculation
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        # Flat ENU Vector with Haversine Distance
        east = dlon * math.cos(lat1)
        north = dlat
        enu_vec = Vec(east, north).unit_vector() * distance
        return enu_vec.x, enu_vec.y





    def __str__(self):
        return f"Distance: {self.dist} | {self.unit_vector()} | Elevation: {self.elevation}"

    def __repr__(self):
        return f"Distance: {self.dist} | {self.unit_vector()} | Elevation: {self.elevation}"


class Speed:
    def __init__(self, mps: float = None, kmph: float = None, mph: float = None):
        if mps is not None:
            self.mps = mps
            self.kmph = mps * 3.6
            self.mph = mps * 2.23694

        elif kmph is not None:
            self.mps = kmph / 3.6
            self.kmph = kmph
            self.mph = kmph / 1.60934

        elif mph is not None:
            self.mps = mph / 2.23694
            self.kmph = mph * 1.60934
            self.mph = mph
        else:
            self.mps = self.mph = self.kmph = 0

    @classmethod
    def rpm(cls, rpm: float = None, rps: float = None, radius: float = 0.2):
        if rpm is not None:
            return cls(mps=2 * math.pi * radius * rpm / 60)
        elif rps is not None:
            return cls(mps=2 * math.pi * radius * rps)
        else:
            return cls()

    def rpm(self, radius: float = 0.2):
        return self.mps * 60 / (2 * math.pi * radius)

    def rps(self, radius: float = 0.2):  # radians per second (SI units)
        return self.mps / (2 * math.pi * radius)
    
    def __str__(self):
        return f"Speed: {self.mps} m/s"

class Velocity(Vec, Speed):
    def __init__(self, unit_vec: Vec = UNIT_VEC, speed: Speed = Speed(0)):
        Speed.__init__(self, speed.mps)
        vec = unit_vec * self.mps
        Vec.__init__(self, vec.x, vec.y)

    def __str__(self):
        return f"{Speed.__str__(self)} | {Vec.__str__(self)}"
    
ZERO_VELOCITY = Velocity(ZERO_VEC, Speed(0))


if __name__ == "__main__":
    p1 = Coordinate(39.092185, -94.417077, 98.4698903750406)
    # print(p1)
    p2 = Coordinate(39.092184, -94.417187, 98.48702242713266)
    # print(p2)
    d1 = Displacement(p1, p2)
    print(f"d1: {d1}")
    v1 = Velocity(d1.unit_vector(), Speed(kmph=50))
    v2 = Velocity(d1.unit_vector(), Speed(kmph=80))
    # print(f"p1: {p1}, Position: {p1}")
    print(f"Velocity: {v1}")