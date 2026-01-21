import xml.etree.ElementTree as ET
from ..engine.kinematics import Coordinate

def parse_kml_file(filename: str = "data/Main Route.kml") -> dict[str, list[Coordinate]]:
    root = ET.parse(filename).getroot()
    placemarks = {}
    for child in root[0]:
        if child.tag == "{http://www.opengis.net/kml/2.2}Placemark":
            # name tag
            name = child.find("{http://www.opengis.net/kml/2.2}name").text

            coords = []
            p_coords = child.find("{http://www.opengis.net/kml/2.2}LineString").find("{http://www.opengis.net/kml/2.2}coordinates")
            for i, line in enumerate(p_coords.text.split("\n")):
                # if i == 60: break # rigged
                line = line.strip()
                if len(line) == 0:
                    continue

                parts = line.split(",")
                coords.append(Coordinate(float(parts[1]), float(parts[0]), float(parts[2])))
            placemarks[name] = coords

    if filename == "data/Main Route.kml":
        placemarks = parse_ASC2024(placemarks)
    return placemarks

def parse_ASC2024(placemarks):
    keys = list(placemarks.keys())
    placemarks = {k:placemarks[k] for k in [keys[0], keys[-1]] + keys[1:-1]}
    return placemarks



if __name__ == "__main__":
    # Bunches all the places and their respective checkpoints
    placemarks = parse_ASC2024()
    for place in placemarks.keys():
        print(place)
        print(placemarks[place])