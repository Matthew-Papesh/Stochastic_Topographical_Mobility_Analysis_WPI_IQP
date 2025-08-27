import requests
from enum import Enum as enum
from decimal import Decimal as decimal
from collections import defaultdict
from datetime import datetime
import time
import csv

def GPS(latitude: float, longitude: float) -> str: 
    """
    Converts GPS coordinates to acceptable DistanceMatrix location input. 
    :param latitude [float] Specified latitude 
    :param longitude [float] Specified longitude 
    :return geographical location
    """
    return f"{latitude},{longitude}"
def TIMING(year: int, month: int, day: int, hour: int, minute: int) -> str:
    """
    Formats date and time for the `timing` enum field. 
    :param year [int] Year formatted as 20XX or 19XX
    :param month [int] Month formatted as XX
    :param day [int] Day formatted as XX
    :param hour [int] Hour formatted in 24-hr format
    :param minute [int] Minutes
    """
    # clamp values
    month = min(12, max(0, month))
    day = min(31, max(0, day))
    hour = min(24, max(0, hour))
    minute = min(60, max(0, minute))
    # format values
    month_str = f"0{month}" if month <= 9 else f"{month}"
    day_str = f"0{day}" if day <= 9 else f"{day}"
    hour_str = f"0{hour}" if hour <= 9 else f"{hour}"
    minute_str = f"0{minute}" if minute <= 9 else f"{minute}"
    # return formatted date-time
    return f"{year}-{month_str}-{day_str} {hour_str}:{minute_str}:00"

class time_units(enum): 
    """Allowable `DistanceMatrix` units for time."""
    MINUTE = "min"
    MINUTES = "mins" 
    HOUR = "hour"
class distance_units(enum):
    """Allowable `DistanceMatrix` units for distance."""
    METER = "m" 
    KILOMETER = "km"

def convert_time(input: float, in_type: time_units, out_type: time_units) -> float:
    """
    Converts time between given units. 
    :param input [float] The specified input time
    :param in_type [time_units] The input time units 
    :param out_type [time_units] The output time units
    :returns The time in the needed units
    """
    # re-map types
    if in_type.value == time_units.MINUTE.value:
        in_type = time_units.MINUTES
    if out_type.value == time_units.MINUTE.value:
        out_type = time_units.MINUTES
    # handle conversions 
    def get_mins(value: float, type: time_units) -> float:
        """Handles converting time to minutes."""
        if type.value == time_units.MINUTES.value:
            return value
        elif type.value == time_units.HOUR.value:
            return 60.0 * value
    def get_hrs(value: float, type: time_units) -> float:
        """Handles converting time to hours."""
        if type.value == time_units.MINUTES.value:
            return (1.0/60.0) * value
        elif type.value == time_units.HOUR.value:
            return value
        
    # calculate and return output value
    if out_type.value == time_units.MINUTES.value:
        return get_mins(input, in_type)
    elif out_type.value == time_units.HOUR.value:
        return get_hrs(input, in_type)
    
def convert_distance(input: float, in_type: distance_units, out_type: distance_units) -> float:
    """
    Converts distance between given units. 
    :param input [float] The specified input distance
    :param in_type [distance_units] The input distance units 
    :param out_type [distance_units] The output distance units
    :returns The distance in the needed units
    """
    # handle conversions 
    def get_meters(value: float, type: distance_units) -> float:
        """Handles converting distance to meters (m)"""
        if type.value == distance_units.METER.value:
            return value 
        if type.value == distance_units.KILOMETER.value:
            return 1000.0 * value 
    def get_kilometers(value: float, type: distance_units) -> float:
        """Handles converting distance to kilometers (km)"""
        if type.value == distance_units.METER.value:
            return (1.0/1000.0) * value 
        elif type.value == distance_units.KILOMETER.value:
            return value 
    
    # calculate and return output value
    if out_type.value == distance_units.METER.value:
        return get_meters(input, in_type)
    elif out_type.value == distance_units.KILOMETER.value:
        return get_kilometers(input, in_type)

# note: duration_in_traffic field is only returned conditionally; may be useful
# note: class enums (excluding `required` and `timing`) type names are query field names with enumerations as the allowable inputs
class mode(enum):
    """
    Enforces a specified means of travel.
    """
    DRIVING = "driving" 
    WALKING = "walking" 
    BIKING = "bicycling"  
    TRANSIT = "transit" 
class avoid(enum):
    """
    Enforces restrictions for travel. 
    """
    TOLLS = "tolls" 
    HIGHWAYS = "highways" 
    FERRIES = "ferries" 
    INDOOR = "indoor"  
    MANY = "many"
class traffic_model(enum):
    """
    Enforces a given assumption about traffic for travel.
    """
    EXPECTED = "best_guess" # most accurate guess based on traffic history
    PESSIMISTIC = "pessimistic" # worst case given traffic history
    OPTIMISTIC = "optimistic" # best case given traffic history
class transit_mode(enum):
    """
    Enforces a specified means of traveling by public transit.
    """
    BUS = "bus" # by train travel
    SUBWAY = "subway" # by subway travel
    TRAIN = "train" # by train travel
    TRAM = "tram" # by tram travel
    RAIL = "rail" # by train, tram, light-rail, and subway (presumably all mentioned transit excluding by-bus) 

class timing(enum):
    """
    Enforces specified timing. Specifier enums are exclusive to each other. 
    FORMAT: YYYY-MM-DDTHH:MM:SSZ
    """
    SET_DEPARTURE = "departure_time", # names of required fields
    SET_ARRIVAL = "arrival_time"

class required(enum):
    """
    Potentially required specifiers for querying. 
    """
    ORIGINS = "origins" # names of required fields
    DESTINATIONS = "destinations"

class MobilityProfile:
    """
    Represents the handler for fetching data queries from the distancematrix.ai platform. Profiles the travel time and distance
    provided known specifiers for modes of travels and other criteria. 
    """
    def __init__(self, connection_id: str=None, origin_node_id: str=None, destination_node_id: str=None):
        """
        Creates a `MobilityProfile` instance that creates a attached connection between an origin and destination node. 
        param: connection_id [str] The unique identifier for this profile 
        param: origin_node_id [str] The unique identifier of the start node 
        param: destination_node_id [str] The unique identifier of the end node 
        """
        # access key and base url for fetching
        self.API_KEY = "DistanceMatrixAI API KEY"
        self.BASE_URL = "https://api.distancematrix.ai/maps/api/distancematrix/json"
        self.timing_param = False # flag for the timing enum type
        # api fields:
        self.origins = ""
        self.destinations = ""
        self.timing = ""
        self.transit_mode = ""
        self.traffic_model = ""
        self.avoid = ""
        self.mode = ""
        # api key field
        self.api_key = ""
        # memoized data from batch fetches
        self.memoized_data = []
        # routing counts: 
        self.origin_count = 0
        self.destination_count = 0
        # unique identifiers 
        self.connection_id = connection_id
        self.origin_node_id = origin_node_id
        self.destination_node_id = destination_node_id

    def attach(self, connect_id: str, origin_node_id: str, destination_node_id: str):
        """
        Attaches a unique identifier to a connection between the specified mobility nodes. 
        param: connect_id [str] The specified unique connection identifier
        param: origin_node_id [str] The specified origin node identifier 
        param: destination_node_id [str] The specified destination node identifier 
        """
        self.connection_id = connect_id if connect_id is not None else self.connection_id
        self.origin_node_id = origin_node_id if origin_node_id is not None else self.origin_node_id
        self.destination_node_id = destination_node_id if destination_node_id is not None else self.destination_node_id

    def set(self, param, value=None):
        """
        Chain method for creating a route search query.
        param: param [any] Specifies what in addition to consider for querying
        param: value [any] Optional argument to specify the parameter value when appropriate
        """
        if isinstance(param, required):
            DELIM = "?" if param == required.ORIGINS else "&" # handling delimiting based on type
            token = f"{DELIM}{str(param.value)}=" # param var is the field name
            for i in range(0, len(value)):
                if i > 0: # pipe additional locations 
                    token += f"|{value[i]}"
                else: # add first location
                    token += f"{value[i]}"
            # query locations 
            if param == required.ORIGINS:
                self.origins = token
                self.origin_count = len(value)
            elif param == required.DESTINATIONS:
                self.destinations = token
                self.destination_count = len(value)
        
        elif isinstance(param, timing):
            # exit chain addition if timing has already been added
            if self.timing_param:
                return self
            # compute unix time from date and time format
            formatted_time = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
            unix_time = int(time.mktime(formatted_time.timetuple()))
            # param var is the field name
            self.timing = f"&{str(param.value)}={unix_time}"
            self.timing_param = True # enabled timing
        
        elif isinstance(param, mode):
            # param var is the field input; no expected value var
            self.mode = f"&mode={str(param.value)}"

        elif isinstance(param, avoid):
            if param != avoid.MANY: # only one type for the field
                # param var is the field input; no expected value var
                self.avoid = f"&avoid={str(param.value)}"
            else: # many types for the field
                token = f"&avoid=" # param var is the field name
                for i in range(0, len(value)):
                    if i > 0: # pipe additional locations 
                        token += f"|{str(value[i].value)}"
                    else: # add first location
                        token += f"{str(value[i].value)}"
                # query locations 
                self.avoid = token   

        elif isinstance(param, traffic_model):
            # param var is the field input; no expected value var
            self.traffic_model = f"&traffic_model={str(param.value)}"

        elif isinstance(param, transit_mode):
            # param var is the field input; no expected value var
            self.transit_mode = f"&transit_mode={str(param.value)}"

        return self

    def fetch_data_batch(self, sub_origins: list, sub_destinations: list): 
        """
        Fetches data of chained query.
        return: The fetched data
        """
        # set fields for url
        self.api_key = f"&key={self.API_KEY}"
        self.set(required.ORIGINS, sub_origins)
        self.set(required.DESTINATIONS, sub_destinations)
        # create the url and return fetched data batch
        url = f"{self.BASE_URL}{self.origins}{self.destinations}{self.timing}{self.transit_mode}{self.traffic_model}{self.avoid}{self.mode}{self.api_key}"
        data = requests.get(url).json()

        if data["status"] == "OK":
            return data["rows"]
        return None

    def get_data_batch_cell(self, sub_origin: int, sub_destination: int, data_batch):
        """
        Parses the time [mins] and distance [km] of a route between specified origin and destination from given fetched batch of data. 
        ASSUMPTION: time is within 24 [hr] travel for distances within 1000 [km]
        param: sub_origin [int] Specified origin index 
        param: sub_destination [int] Specified destination index 
        param: data_batch [any] Specified data batch that was fetched 
        return: 2D tuple of travel route time and distance in [min] and [km] respectively
        """
        sub_origin = max(0, min(self.origin_count - 1, sub_origin))
        sub_destination = max(0, min(self.destination_count - 1, sub_destination))
        # pull estimates from given data batch 
        data = data_batch[sub_origin]["elements"][sub_destination]
        distance_data = str(data["distance"]["text"]).split()
        time_data = str(data["duration"]["text"]).split()
       
        # time and distance data
        est_distance, distance_u = float(distance_data[0]), distance_units(str(distance_data[1]))
        time_mins = 0.0 # sum estimated time parts in [mins]

        # time is split into many parts of varying units (e.g. 2 hrs 34 mins <=> split = ['2', 'hrs', '34', 'mins'])
        # step through parts of quantities and unit type; convert to [mins] and sum
        time_data_part, time_u_part, add_time_part = 0.0, "", False
        for i in range(0, len(time_data)):
            print(f"time_data[i] == {time_data[i]}")
            if i % 2 == 0: # even index or zero; numerical data
                time_data_part = float(time_data[i])
            else: # odd index; data units
                time_u_part = time_units(str(time_data[i]))
                add_time_part = True # ready to add part
            if add_time_part: # completed part
                time_mins += convert_time(time_data_part, time_u_part, time_units("mins"))
                add_time_part = False 

        # convert data to desired units and return
        distance_km = convert_distance(est_distance, distance_u, distance_units("km"))
        return (time_mins, distance_km)
    
    def query_profile(self, origins: list, destinations: list, file: str):
        """
        This computes the estimation data for traveling between two nodes and writes locally.
        param: origins [list] The specified origins to set and get data for
        param: destinations [list] The specified destinations to set and get data for  
        """
        def sub_inv_cartesian_product(row_ids: list, col_ids: list, p0: tuple, p1: tuple) -> list:
            """
            Given row and column lists that can map to a parent cartesian product matrix, a sub matrix specified by start and end points within the parent,
            `p0` and `p1`, can be indicated such that the sub row and sub column lists used to compute the sub matrix as its own cartesian product can be found. 
            param: row_ids [list] The specified row names to find the parent matrix
            param: col_ids [list] The specified col names to find the parent matrix
            param: p0 [tuple[int,int]] The specified starting element of the sub-matrix
            param: p1 [tuple[int,int]] The specified end element of the sub-matrix
            return: The sub lists of row and column ids needed to compute the sub-matrix as a cartesian product 
            """
            p0 = (max(0, min(len(col_ids) - 1, p0[0])), max(0, min(len(row_ids) - 1, p0[1])))
            p1 = (max(0, min(len(col_ids) - 1, p1[0])), max(0, min(len(row_ids) - 1, p1[1])))
            sub_row_ids, sub_col_ids = row_ids[p0[1]:p1[1] + 1], col_ids[p0[0]:p1[0] + 1]
            return (sub_col_ids, sub_row_ids)
        
        with open(file, "a") as conn_file: # open profile/connection file 
            # sub sample matrix size of the larger cartesian product
            kernel_dims = (10,10) # largest allowable size for distancematrix api
            # cartesian product matrix dimensions
            total_dims = (len(origins), len(destinations))
            # walk through all possible routes between the given origins and destinations
            # consider format of this as a matrix; x-axis is the list of origins, y-axis the destinations, and the grid elements as the combinations of the two
            for y in range(0, total_dims[0], kernel_dims[1]):
                for x in range(0, total_dims[1], kernel_dims[0]):
                    # find sub row and col ids from main id lists 
                    sub_destinations, sub_origins = sub_inv_cartesian_product(row_ids=origins, col_ids=destinations, p0=(x, y), p1=(x + kernel_dims[0] - 1, y + kernel_dims[1] - 1))
                    # fetch sub data routes with distancematrix api
                    data_batch = self.fetch_data_batch(sub_origins=sub_origins, sub_destinations=sub_destinations)
                    print(f"data batch: {data_batch}")
                    # step through getting cell estimation data and memoize 
                    for destination_index in range(0, len(sub_destinations)):
                        for origin_index in range(0, len(sub_origins)):
                            try:
                                # find current cell estimation data for distance [km] and time [min]
                                cell_data = self.get_data_batch_cell(sub_origin=origin_index, sub_destination=destination_index, data_batch=data_batch)
                                # find index pair of (origin-destination) route; consider base point (x,y) and offset for each cell 
                                memoized_origin_index = x + origin_index
                                memoized_destination_index = y + destination_index
                                # get parsed gps data
                                origin_gps = sub_origins[origin_index].split(sep=',')
                                dest_gps = sub_destinations[destination_index].split(sep=',')
                                origin_lat, origin_lon = origin_gps[0].strip(), origin_gps[1].strip()
                                dest_lat, dest_lon = dest_gps[0].strip(), dest_gps[1].strip()
                                # store cell data in file
                                self.memoized_data.append((cell_data[0], cell_data[1], origin_lat, origin_lon, dest_lat, dest_lon))
                                conn_file.write(f"{self.connection_id},{self.origin_node_id},{self.destination_node_id},{origin_lat},{origin_lon},{dest_lat},{dest_lon},{memoized_origin_index},{memoized_destination_index},{cell_data[0]},{cell_data[1]}\n")
                            except:
                                print("QUERYING: DATA BATCH FAILED\n")
                                continue

    def read_profile(self, file: str):
        """
        Reads in estimation data for traveling between two nodes given a file to import from locally. 
        param: file [str] The file to import from
        """
        with open(file, newline='') as conn_file:
            for record in csv.reader(conn_file):
                # add record if it is the correct connection
                if str(record[0].strip()) == self.connection_id:
                    # connection data
                    time_min, distance_km = float(decimal(record[9].strip())), float(decimal(record[10].strip()))
                    orig_lat, orig_lon = float(decimal(record[3].strip())), float(decimal(record[4].strip()))
                    dest_lat, dest_lon = float(decimal(record[5].strip())), float(decimal(record[6].strip()))
                    # map connection id to data
                    self.memoized_data.append((time_min, distance_km, orig_lat, orig_lon, dest_lat, dest_lon))

    def get(self):
        """
        Gets the time [mins] and distance [km] of all sampled trips between the origin and destination node. 
        return: A list of the estimated trips' data as a 6D tuples (time [min], distance [km], origin_lat, origin_lon, dest_lat, dest_lon)
        """
        return self.memoized_data

    def reset(self):
        """
        Resets and clears the chained query. 
        """
        self.origins = ""
        self.destinations = ""
        self.timing = ""
        self.transit_mode = ""
        self.traffic_model = ""
        self.avoid = ""
        self.mode = ""
        # reset memoized data
        self.memoized_data.clear()
        # reset flags
        self.timing_param = False 
        # reset route counters 
        self.origin_count = 0
        self.destination_count = 0
# short-hand alias
MProfile = MobilityProfile