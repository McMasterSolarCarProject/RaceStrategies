import xml.etree.ElementTree as ET
from ..engine.kinematics import Coordinate

KML_NS = "{http://www.opengis.net/kml/2.2}"

def parse_kml_file(filename: str = "data/ASC_2024.kml") -> dict[str, list[Coordinate]]:
    """
    Takes a .kml file and returns a dictionary mapping placemark names to lists of Coordinate objects.
    """
    root = ET.parse(filename).getroot()
    placemarks = {}
    for child in root[0]:
        if child.tag == f"{KML_NS}Placemark":
            name = child.find(f"{KML_NS}name").text

            coords = []
            p_coords = child.find(f"{KML_NS}LineString").find(f"{KML_NS}coordinates")
            for i, line in enumerate(p_coords.text.split("\n")):
                line = line.strip()
                if len(line) == 0:
                    continue

                parts = line.split(",")
                coords.append(Coordinate(float(parts[1]), float(parts[0]), float(parts[2])))
            placemarks[name] = coords
    return placemarks


if __name__ == "__main__":
    # Bunches all the places and their respective checkpoints
    placemarks = parse_kml_file()
    for place in placemarks.keys():
        print(place)
        print(placemarks[place])