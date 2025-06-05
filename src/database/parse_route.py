import xml.etree.ElementTree as ET
import math
from .classes import Coordinate, Placemark

# used in scripts
def parse_kml_file(filename): # Make this code better and Document it
    root = ET.parse(filename).getroot()
    placemarks = []
    for child in root[0]:
        if child.tag == "{http://www.opengis.net/kml/2.2}Placemark":
            # name tag
            name = child.find("{http://www.opengis.net/kml/2.2}name").text
            coords = []
            # coordinates tag
            p_coords = child.find("{http://www.opengis.net/kml/2.2}LineString").find("{http://www.opengis.net/kml/2.2}coordinates")
            for line in p_coords.text.split("\n"):
                line = line.strip()
                if len(line) == 0:
                    continue

                parts = line.split(",")
                coords.append(Coordinate(float(parts[0]), float(parts[1]), float(parts[2])))
            placemarks.append(Placemark(name, coords))
    return placemarks

def parse_ASC2024():
    placemarks = parse_kml_file("data/Main Route.kml")
    return [placemarks[0], placemarks[-1]]+ placemarks[1:-1]

def parse_FSGP_2025():
    return parse_kml_file("data/FSGP_Track.kml")

if __name__ == "__main__":
    # placemarks = parse_ASC2024()
    # Bunches all the places and their respective checkpoints
    placemarks = parse_FSGP_2025()
    for place in placemarks:
        print(place.name)
# rewrite this, this sucks
# # used in scripts
def calc_distance(coords: list[Coordinate], current_coord: Coordinate):
    sum_distance = 0
    stop_index = coords.index(current_coord)
    for i in range(stop_index + 1):
        if i > 0:
            sum_distance += heversine_and_azimuth(coords[i - 1].lon, coords[i - 1].lat, coords[i].lon, coords[i].lat)[0]
    return sum_distance * 1000  # convert to meters

# # used in scripts
# # TODO: this should be a method the Coordinate class, either static or instance
def calc_azimuth(coords: list[Coordinate], current_coord: Coordinate):
    current_index = coords.index(current_coord)

    if current_index < len(coords) - 1:
        next_coord = coords[current_index + 1]

        lat1 = math.radians(current_coord.lat)
        lon1 = math.radians(current_coord.lon)
        lat2 = math.radians(next_coord.lat)
        lon2 = math.radians(next_coord.lon)

        dlon = lon2 - lon1
        azimuth = math.degrees(math.atan2(math.sin(dlon) * math.cos(lat2), math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon),))
        azimuth %= 360
        return azimuth
    else:
        return 0


# # document and edit this
def heversine_and_azimuth(lon1: float, lat1: float, lon2: float, lat2: float):
    R = 6371.0  # Radius of the Earth in km
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    azimuth = math.atan2(math.sin(dlon) * math.cos(lat2), math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon))

    azimuth %= math.pi * 2

    return distance, azimuth