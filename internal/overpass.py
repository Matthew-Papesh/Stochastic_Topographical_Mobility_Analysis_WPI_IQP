import requests 
import json

# note: Visit the API online website for see what other data we can query if needed! (e.g. wheelchair accessibility)

# Query metro file:
DEST_METRO_FILE = "./../cph_mobility_data/metro_gps.csv"
# Overpass API metro query
METRO_QUERY = """
[out:json][timeout:25];
// Step 1: Find all metro line relations in Copenhagen Metro
(
  relation["route"="subway"](55.5, 11.9, 55.9, 12.8);
)->.lines;

// Step 2: Get all nodes (stations) that are part of these metro lines
node(r.lines)->.stations;

// Step 3: Output stations and their metro line relations
(
  .stations;
  .lines;
);
out body;
>;
out skel qt;
"""

# Query train file:
DEST_TRAIN_FILE = "./../cph_mobility_data/train_gps.csv"
# Overpass API train query
TRAIN_QUERY = """
[out:json][timeout:25];
// Step 1: Find all train line relations in Copenhagen 
(
  relation["route"="train"](55.5, 11.9, 55.9, 12.8);
  relation["route"="light_rail"](55.5, 11.9, 55.9, 12.8);
  relation["route"="railway"](55.5, 11.9, 55.9, 12.8);
)->.lines;

// Step 2: Get all nodes (stations) that are part of these lines
node(r.lines)->.stations;

// Step 3: Output stations and their relations
(
  .stations;
  .lines;
);
out body;
>;
out skel qt;
"""
# Query bus file:
DEST_BUS_FILE = "./../cph_mobility_data/bus_gps.csv"
# Overpass API bus query
BUS_QUERY = """
[out:json][timeout:25];
// Step 1: Find all bus line relations in Copenhagen area
(
  relation["route"="bus"](55.5, 11.9, 55.9, 12.8);
)->.routes;

// Step 2: Get all nodes (bus stops) that are part of these bus lines
node(r.routes)->.stops;

// Step 3: Output stops and their bus line relations
(
	.routes;
  	.stops;
);
out body;
>;
out skel qt;
"""

# fetch queries
URL = "https://overpass-api.de/api/interpreter"
metro_response = requests.post(URL, data={"data": METRO_QUERY})
train_response = requests.post(URL, data={"data": TRAIN_QUERY})
bus_response = requests.post(URL, data={"data": BUS_QUERY})

# record metro data
metro_data = metro_response.json()
metro_stations = []
metro_relations = {}

# read Overpass metro line elements for related metro stops 
for element in metro_data["elements"]:
    if element["type"] == "relation":
        line_name = element["tags"].get("name", "Unknown_Line")
        for member in element["members"]:
            if member["type"] == "node" and member["role"] == "stop":
                station_id = member["ref"]
                metro_relations[station_id] = line_name
# read Overpass metro stops and append appropriate metro line data
for element in metro_data["elements"]:
    try:
        if element["type"] == "node": # metro stations
            metro_line = metro_relations[element["id"]]
            metro_stations.append((float(element["lat"]), float(element["lon"]), metro_line))
    except:
        pass

# record train data
train_data = train_response.json()
train_stations = []
train_relations = {}

# read Overpass train line elements for related train stops 
for element in train_data["elements"]:
    if element["type"] == "relation":
        line_name = element["tags"].get("name", "Unknown_Line")
        for member in element["members"]:
            if member["type"] == "node" and member["role"] == "stop":
                station_id = member["ref"]
                train_relations[station_id] = line_name
# read Overpass train stops and append appropriate train line data
for element in train_data["elements"]:
    try:
        if element["type"] == "node": # train stations 
            train_line = train_relations[element["id"]]
            train_stations.append((float(element["lat"]), float(element["lon"]), train_line))
    except:
        pass

# record bus data
bus_data = bus_response.json()
bus_stops = []
bus_relations = {}

# read Overpass bus line elements for related bus relations
for element in bus_data["elements"]:
    if element["type"] == "relation":
        line_name = element["tags"].get("name", "Unknown_Line")
        stop_ids = []
        for member in element["members"]:
            if member["type"] == "node" and member["role"] == "stop":
                stop_id = member["ref"]
                bus_relations[stop_id] = line_name
# read Overpass bus stops and append appropriate bus line data
for element in bus_data["elements"]:
    try:
        if element["type"] == "node": # bus stops 
            bus_line = bus_relations[element["id"]]
            bus_stops.append((float(element["lat"]), float(element["lon"]), bus_line))
    except:
        pass

def has_digits(token: str):
    """
    Determines if there are digits within the given token.
    param: token [str] The specified token
    """
    for i in range(0, 9):
        # return if a digit is found 
        if token.__contains__(str(i)):
            return True 
    return False 

def parse_metro_line(line: str):
    """
    Parses a line description of a metro route stop to 
    return the metro line ID. Potential IDs: M1, M2, M3, M4
    param: line [str] The specified line  
    return: The metro line ID
    """
    if line == "Unknown_Line":
        return "n/a" # unknown; do nothing 
    # map found type to desired convention 
    elif line.__contains__("M1"):
        return "M1"
    elif line.__contains__("M2"):
        return "M2"
    elif line.__contains__("Cityringen"):
        return "M3"    
    elif line.__contains__("Nordhavnsmetro"):
        return "M4"

def parse_train_line(line: str):
    """
    Parses a line description of a s-train route stop to 
    return the train line ID. Potential IDs: n/a, A, B, Bx, C, E, F, H
    param: line [str] The specified line 
    return the train line ID
    """
    if line == "Unknown_Line" or line.__contains__("Regional") or line.__contains__("InterCity"):
        return "n/a" # unknown or unwanted type; do nothing 
    # look for non-(IC/regional) trains; assume unwanted types are gone 
    tokens = line.split() # get tokens 
    is_s_train = False # s-train flag
    for token in tokens:
        # check if token is s-train;
        if token.__contains__("S-tog"):
            is_s_train = True 
            continue # go to next token
        # check through s-train types 
        if is_s_train and token.__contains__("A"):
            return "A"
        # check Bx before B since both contain "B"; 
        # checking "Bx" would be flagged when checking "B" 
        elif is_s_train and token.__contains__("Bx"):
            return "Bx"
        elif is_s_train and token.__contains__("B"):
            return "B"
        elif is_s_train and token.__contains__("C"):
            return "C"
        elif is_s_train and token.__contains__("E"):
            return "E"
        elif is_s_train and token.__contains__("F"):
            return "F"
        elif is_s_train and token.__contains__("H"):
            return "H"
    # no type to return 
    return "n/a"

def parse_bus_line(line: str):
    """
    Parses a line description of a bus route stop to 
    return the bus line ID. Potential IDs: n/a, A, S, R, C, E, N 
    param: line [str] The specified line  
    """
    # unknown; do nothing
    if line == "Unkown_Line":
        return "n/a"
    tokens = line.split() # get tokens 
    for token in tokens: 
        # check if token is bus ID;
        if has_digits(token): 
            # check through bus types 
            if token.__contains__("A"):
                return "A"
            elif token.__contains__("S"):
                return "S"
            elif token.__contains__("R"):
                return "R"
            elif token.__contains__("C"):
                return "C"
            elif token.__contains__("E"):
                return "E"
            elif token.__contains__("N"):
                return "N"
    # no type found to return
    return "n/a" 

# write metro station data contents 
with open(DEST_METRO_FILE, 'w') as file:
    file.truncate(0)
    file.write("latitude, longitude, name, metro_line\n")
    for station in metro_stations:
        parsed = parse_metro_line(station[2])
        file.write(f"{station[0]},{station[1]},{parsed},\"{station[2]}\"\n")
# write train station data contents 
with open(DEST_TRAIN_FILE, 'w') as file:
    file.truncate(0)
    file.write("latitude, longitude, name, train_line\n")
    for station in train_stations:
        parsed = parse_train_line(station[2])
        file.write(f"{station[0]},{station[1]},{parsed},\"{station[2]}\"\n")
# write bus stop data contents 
with open(DEST_BUS_FILE, 'w') as file:
    file.truncate(0)
    file.write("latitude, longitude, name, bus_line\n")
    for stop in bus_stops:
        parsed = parse_bus_line(stop[2])
        file.write(f"{stop[0]},{stop[1]},{parsed},\"{stop[2]}\"\n")
