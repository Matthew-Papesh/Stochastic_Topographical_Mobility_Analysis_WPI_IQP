from decimal import Decimal as decimal
from internal.gps_sample import *
import internal.mobility_profile as mp
import itertools

class buses(enum):
    """bus line types"""
    all = "all"
class metros(enum):
    """metro line types"""
    all = "all"
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
class trains(enum):
    """train line types"""
    all = "all"
    A = "A"
    B = "B"
    Bx = "Bx"
    C = "C"
    E = "E"
    F = "F"
    H = "H"

class MobilityNode(GPSSample): 
    """
    Represents a physical area of space that has specific ways to travel and move. Mobility nodes 
    inherit `GPSSample` and accept `MobilityProfile` interfaces. A `MobilityNode` is also aliased as `MNode`.
    """
    def __init__(self,bus_stops_gps: dict, metro_stops_gps: dict, train_stops_gps: dict, id: str, root_lat: float=None, root_lon: float=None, 
                 area_radius: float=None, n: float=None, catchment_node: 'MobilityNode'=None, transit_type: transit_mode=None, transit_line=None,
                 filter_gps_zones: list=None, set_locations: list=None):
        """
        Creates a `MobilityNode` instance by either API query or imported locally by file. Catchment nodes are areas of traffic to attract to this transit 
        node of transit stop locations. A transit node is nearby to another node if the transit node locations are the set of closest 
        transit stops to each location of the other node. If `catchment_node` is specified, this node is assumed to be a transit node; its locations will be 
        computed based on the catchment node. If `set_locations` is specified, this node assumes its locations sampled are taken from this list and the locations 
        will not be quered. If this argument is used and no locations are queried, qualitative data on locations, such as municipality and region, will not be known. 
        param: root_lat [float] The specified latitude of the area center
        param: root_lon [float] The specified longitude of the area center 
        param: area_radius [float] The specified radius of the node area
        param: n [float] The sample size of locations collected within the area   
        param: catchment_node [MobilityNode] The catchment area 
        param: transit_type [any] The type of transit identifier
        param: transit_line [any] The line of transit identifier
        param: filter_gps_zones [list] The list of 8D tuples for each element (x0,y0,x1,y1,x2,y2,x3,y3) bounds a convex shape to not sample from. 
        param: set_locations [list] The list of predetermined locations as a set of 2D tuples of GPS coordinates
        """
        super().__init__()
        print(f"Creating node: {id}")
        # look-up hash maps for gps transit stop data; data by transit type and has the lists: "all", and transit specific ones (e.g. metro: "M1", "M2", etc)
        self.bus_stops_gps = bus_stops_gps
        self.metro_stops_gps = metro_stops_gps
        self.train_stops_gps = train_stops_gps
        # get transit stops mapping and other data
        self.transit_stop_mapping = {transit_mode.BUS: self.bus_stops_gps, transit_mode.SUBWAY: self.metro_stops_gps, transit_mode.TRAIN: self.train_stops_gps}
        self.transit_name_mapping = {transit_mode.BUS: "bus", transit_mode.SUBWAY: "metro", transit_mode.TRAIN: "train"}
        self.transit_type = transit_type
        self.transit_line = transit_line
        self.filter_gps_zoes = filter_gps_zones

        # dictionary samples of collected qualitative data on gps locations; 
        # municipality and region - specifies rough geographical area 
        # type - specifies the kind of location (e.g. house, bench, park, gov building, etc)
        # locations - list of `Location` instances that have gps coords to the aforementioned corresponding qualitative data 
        self.root_lat, self.root_lon, self.area_radius, self.n = root_lat, root_lon, area_radius, n
        # location list should be empty for location sampling; if predetermined set-locations are given, then wrap in `self.Location` objects and assign that as the list
        self.locations = [] if set_locations is None else [self.Location(lat=location[0], lon=location[1], type="n/a", municipality="n/a", region="n/a") for location in set_locations]
        self.mobilities = {} # mapping of ways to estimate travel efficiency from "this" node / area 
        self.mobility_data = {} # mapping of estimated travel data for each mobility; maps to vectors of distance (km) and time (min)
        self.mobility_ids = [] # list of mobility identifiers
        self.node_id = id # node id
        self.catchment_node = catchment_node
        self.data_file = None # local storage of data
        self.queried = False # flag for if the node has been queried 

    def get_closest_transit_stops(self, gps_list: list, transit_stops: dict, type: any) -> list:
        """
        Determines the closet transit stop near each given GPS position, provided a dataset specifying a transit type. 
        Transit stops given being a dictionary of lists mapped by transit line types such as "M1", "M2", "all", etc. 
        Type given is expected from the `buses`, `metros`, and `trains` enums specified above. 
        param: gps_list [list] The specified positions 
        param: transit_stops [dict] The dataset of lists filtered by transit line type
        param: type [enum] The type of transit line
        return: The list of nearby transit stops
        """
        # closest nearby stop to each gps location and its distance
        nearby_gps_stops = list(itertools.repeat((0,0), len(gps_list)))
        min_distances = list(itertools.repeat(None, len(gps_list)))
        # step through list of gps stops 
        for gps_stop in transit_stops[type]:
            for i in range(0, len(gps_list)):
                # calculate distance to this gps location from transit stop
                distance = pow(pow(gps_stop[0] - gps_list[i][0], 2.0) + pow(gps_stop[1] - gps_list[i][1], 2.0), 0.5)
                # should a closer stop be found, account for it
                if min_distances[i] is None or distance < min_distances[i]:
                    nearby_gps_stops[i] = (gps_stop[0], gps_stop[1])
                    min_distances[i] = distance
        # return closest transit stop
        return nearby_gps_stops

    def query_node(self, file: str):
        if not self.queried:
            self.data_file = file
            with open(file, "a") as node_file:
                locations = []
                # sample locations only if there are none yet
                if self.locations is None or len(self.locations) == 0:
                    # randomly sample locations 
                    if self.catchment_node is None: 
                        _,_,_, locations = self.fetch_radial_location_sample(self.root_lat, self.root_lon, self.area_radius, self.n, self.filter_gps_zoes)   
                    # catchment is present; this node must be a transit node. Find locations accordingly
                    else:   
                        # query the catchment node if needed as a dependency for this node querying 
                        if not self.catchment_node.queried:
                            self.catchment_node.query_node(file)

                        # get lists of location gps positions - QUERY STEP
                        gps_catchment_locations = [location.gps_coordinate for location in self.catchment_node.locations]
                        all_transit_stops = self.transit_stop_mapping.get(self.transit_type)
                        # print catchment onto "this" node
                        print(f"node_id={self.node_id},\ncatchment locs: {gps_catchment_locations}")

                        # get transit stops closest to origin and dest nodes - QUERY STEP
                        gps_transit_stops = self.get_closest_transit_stops(gps_list=gps_catchment_locations, transit_stops=all_transit_stops, type=self.transit_line)

                        # create node stop locations - QUERY STEP
                        for i in range(0, len(gps_transit_stops)):
                            location_type = f"{self.transit_name_mapping.get(self.transit_type)}_stop"
                            location_municipality = self.catchment_node.locations[0].municipality
                            location_region = self.catchment_node.locations[0].region
                            location = self.Location(lat=gps_transit_stops[i][0], lon=gps_transit_stops[i][1], type=location_type, municipality=location_municipality, region=location_region)
                            locations.append(location) # locations ordered to correspond to location ordered list of catchment node
                            # the i-th location in the catchment node has its nearby transit stop at the i-th location in this node 
                    # set node locations from what was queried if possible
                    self.locations = locations if locations is not None else self.locations
                # set locations to write from current node locations 
                elif self.locations is not None and len(self.locations) > 0:
                    locations = self.locations
                # write locations
                for location in locations:
                    # store data in file 
                    node_file.write(f"{self.node_id},{location.gps_coordinate[0]},{location.gps_coordinate[1]},{location.municipality},{location.region},{location.type}\n") 
                self.queried = locations is not None # flag queried state 
        print(f"Done querying node: {id}")

    def read_node(self, file: str):
        """
        Samples locations for this node from local storage. 
        param: file [str] The specified file to import data from  
        """
        with open(file, newline='') as node_file:
            # reset locations list for reading 
            self.locations.clear()
            for record in csv.reader(node_file):
                # add record if for this node
                if str(record[0]) == self.node_id:
                    location = self.Location(lat=float(record[1]), lon=float(record[2]), type=str(record[5]), municipality=str(record[3]), region=str(record[4]))
                    self.locations.append(location)
            self.queried = self.locations is not None

    def add_mobility(self, connection_id, dest_node, profile):
        """
        Creates a means mobility between this node and another via a specified means of travel. 
        param: connection_id [str] The specified unique identifier of this mobility relationship
        param: dest_node [MobilityNode] The destination node or area 
        param: profile [MobilityProfile] The means of travel  
        """
        if connection_id is not None and dest_node is not None and profile is not None:
            self.mobilities[str(connection_id)] = (dest_node, profile)
            print(f"Added mobility {connection_id} to node {self.node_id} connecting to {dest_node.node_id}")
            self.mobility_ids.append(str(connection_id))

    def query_profiles(self, file: str):
        """
        Queries all mobility profiles belonging to this node to retrieve estimation data to store locally. 
        param: file [str] The file to import estimation data to 
        """
        print(f"Querying all {len(self.mobilities)} mobility profiles for node {self.node_id}")
        # step through mobilities between "this" node and adjacent nodes by respective mobility profile
        for mobility in self.mobilities.values():
            # adjacent node and means of travel profile for estimating data
            dest_node, profile = mobility[0], mobility[1]
    
            # retrieve origin and destination gps sample data; data was sampled upon creation of each `MobilityNode` instance
            # If the dest has catchment, the orig is a catchment node
            # Only query the i-th orig location to the i-th dest location
            if (self.catchment_node is not None or dest_node.catchment_node is not None) and not (self.catchment_node is not None and dest_node.catchment_node is not None):
                print(f"Catchment Connection! origin node count = {len(self.locations)}, dest node count = {len(dest_node.locations)}")
                n = max(0, min(len(self.locations), len(dest_node.locations))) # number of sub trips between nodes; should be the same in the catchment case
                print(f"Query for n={n} sub trips")
                import time 
                time.sleep(2.0)
                # query only the i-th origin location to the i-th dest location
                for i in range(0, n): # the i-th location in both nodes represents the closest dest node location to the given catchment origin node location
                    origin, destination = self.locations[i], dest_node.locations[i]
                    profile.query_profile(origins=[mp.GPS(latitude=origin.gps_coordinate[0], longitude=origin.gps_coordinate[1])],
                                          destinations=[mp.GPS(latitude=destination.gps_coordinate[0],longitude=destination.gps_coordinate[1])],
                                          file=file)
            else: # query all origins against all destination locations at once; find all possible permutations of sub trips between nodal locations 
                print(f"Normal querying!")
                origins, destinations = [], []
                for origin in self.locations:
                    origins.append(mp.GPS(latitude=origin.gps_coordinate[0], longitude=origin.gps_coordinate[1]))
                for destination in dest_node.locations:
                    destinations.append(mp.GPS(latitude=destination.gps_coordinate[0], longitude=destination.gps_coordinate[1]))
                # fetch chunks of route data in sub lists:
                profile.query_profile(origins=origins, destinations=destinations, file=file) 
            
            print(f"Fetched data for node\nDone computing for node {self.node_id}")

    def read_profiles(self, file: str):
        """
        Reads in estimation data for all mobility profiles for traveling between this node and another given a file to import from locally. 
        param: file [str] The file to import from
        """
        print(f"Querying all {len(self.mobilities)} mobility profiles for node {self.node_id}")
        # step through mobilities between "this" node and adjacent nodes by respective mobility profile
        for mobility in self.mobilities.values():
            profile = mobility[1] # get profile
            profile.read_profile(file=file) # read local data into profile 

    def get(self, id: str, origin_index: int, dest_index: int):
        """
        Looks up and returns the memoized distance [km] and time [min] data associated between indexed 
        origin and destinations points belonging to "this" node and adjacent local node specified by a given id
        respectively. Returns `None` if local get fails. 
        param: id [str] The specified identifier of the mobility relationship
        param: origin_index [int] The specified origin index in the relationship mobility data
        param: dest_index [int] The specified destination index in the relationship mobility data
        return: 2D tuple of origin-destination route data of time and distance in [min] and [km] respectively
        """
        if id in self.mobilities.keys:
            print(f"Retrieving route data for edge {(origin_index, dest_index)} of relationship {id}")
            mobility = self.mobilities[id] # get corresponding mobility relationship
            # get corresponding node and associated mobility profile 
            dest_node, profile = mobility[0], mobility[1]
            # clamp point indices for origin/dest between expected values 
            origin_index = max(0, min(len(self.locations), origin_index))
            dest_index = max(0, min(len(dest_node.locations), dest_index))
            # return estimated data 
            print(f"Done retrieving data")
            return profile.get(origin_index, dest_index)
        return None # failed to find id; do nothing 
# short-hand alias
MNode = MobilityNode