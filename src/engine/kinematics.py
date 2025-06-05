import math


class Vec:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.mag = math.sqrt(self.x ** 2 + self.y ** 2)

    def __sub__(self, other: 'Vec'):
        return Vec(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float):
        return Vec(self.x * scalar, self.y * scalar)

    def sin(self):
        return self.y / self.mag

    def cos(self):
        return self.x / self.mag

    def unit_vector(self):
        if self.mag == 0:
            print("zero div")
            return Vec(0, 1)
        return Vec(self.x / self.mag, self.y / self.mag)

    def __str__(self):
        return f"Vector: {self.x, self.y}, Magnitude: {self.mag}"


UNIT_VEC = Vec(1, 0)
ZERO_VEC = Vec(0, 0)


class Coordinate:  # Should Be Calculated in Meters
    def __init__(self, lon: float, lat: float, elevation: float):
        self.lon = lon
        self.lat = lat
        self.elevation = elevation
        self.haversine()

    def haversine(self):
        R = 6371000 + self.elevation  # Earth's radius in meters
        lon_rad = math.radians(self.lon)
        lat_rad = math.radians(self.lat)
        x = R * math.cos(lat_rad) * math.cos(lon_rad)
        y = R * math.cos(lat_rad) * math.sin(lon_rad)
        self.position = Vec(x, y)

    def __str__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"

    def __repr__(self):
        return f"Lat: {self.lat} | Lon: {self.lon} | Elevation: {self.elevation}"


class Displacement(Vec):  # Meters
    def __init__(self, p1: Coordinate, p2: Coordinate):
        self.p1 = p1
        self.p2 = p2
        vec = p2.position - p1.position
        super().__init__(vec.x, vec.y)
        self.gradient = Vec(self.mag, p2.elevation - p1.elevation)
        self.dist = self.gradient.mag
        self.elevation = p2.elevation - p1.elevation

    def __str__(self):
        return f"Distance: {self.dist} | Vector {self.unit_vector()} | Elevation: {self.elevation}"

    def __repr__(self):
        return f"Distance: {self.dist} | Vector{self.unit_vector()} | Elevation: {self.elevation}"


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

    def rps(self, radius: float = 0.2):  # radians per secound (SI units)
        return self.mps / (2 * math.pi * radius)


class Velocity(Vec, Speed):
    def __init__(self, unit_vec: Vec = UNIT_VEC, mps: float = None, kmph: float = None, mph: float = None):
        Speed.__init__(self, mps, kmph, mph)  # order is important here
        vec = unit_vec * self.mps
        Vec.__init__(self, vec.x, vec.y)

    @classmethod
    def S(cls, unit_vec: Vec = None, speed: Speed = Speed()):
        return cls(unit_vec, mps=speed.mps)

    def __str__(self):
        return super().__str__()


class Segment(Displacement):  # Meters
    def __init__(self, p1: Coordinate, p2: Coordinate, v_eff: Velocity, p_eff: float = 0, wind: Velocity = ZERO_VEC,
                 speed_limit=0):
        super().__init__(p1, p2)
        self.v_eff = v_eff
        self.p_eff = p_eff
        self.wind = wind
        self.speed_limit = speed_limit
        self.tdist = self.dist

    def __str__(self):
        return f"Total Distance: {self.tdist} | V eff: {self.v_eff} |P eff: {self.p_eff}"


if __name__ == "__main__":
    p1 = Coordinate(-94.417077, 39.092185, 98.4698903750406)
    # print(p1)
    p2 = Coordinate(-94.417187, 39.092184, 98.48702242713266)
    # print(p2)
    d1 = Displacement(p1, p2)
    print(d1)
    s1 = Segment(p1, p2, Velocity(d1.unit_vector(), 50))
    v1 = Velocity(d1.unit_vector(), 50)
    v2 = Velocity.S(d1.unit_vector(), Speed(kmph=50))
    print(v2)
