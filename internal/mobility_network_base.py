from internal.mobility_node import *
from internal.mobility_sample import *
from enum import Enum as enum
from decimal import Decimal as decimal
import internal.mobility_profile as mp
from internal.handler import *
import itertools
import os.path
import csv
import numpy as np 

class MobilityNetworkBase(MobilityTripSampler):
    """
    Represents the high-level mobility graph made between mobility nodes (areas) and connections (profiles). 
    This class makes interfacing and building a graph more straight forward and imports transit stop gps data. 
    This class does two tasks (1) QUERIES FROM ONLINE SOURCES and (2) Computes mobility samples from local already-queried data on computer
    """
    # Copenhagen Central (gps coord) areas to avoid when sampling; tuples of the form (x0,y0,x1,y1,x2,y2,x3,y3)
    copenhagen_central_avoid_gps_filter = [
        [-0.111, -0.754, 0.192, -0.324,  0.108, -0.304, -0.272, -0.750],
        [ 0.182, -0.342, 0.207, -0.120,  0.112, -0.091,  0.089, -0.330],
        [ 0.204, -0.134, 0.177, -0.046,  0.112, -0.091,  0.110, -0.110],
        [ 0.197, -0.012, 0.084,  0.169, -0.022,  0.094,  0.800, -0.081]
    ]
    # Nordhavn (gps coord) areas to avoid when sampling; tuples of the form (x0,y0,x1,y1,x2,y2,x3,y3)
    nordhavn_avoid_gps_filters = [
        [-0.380, 0.650, -0.323, 0.830, -0.828, 0.713, -0.730, 0.466],
        [-0.384, 0.636, -0.490, 0.677, -0.655, 0.266, -0.586, 0.160],
        [-0.390, 0.047, -0.593, 0.413, -0.655, 0.266, -0.515, -0.014],
        [ 0.090, 1.183,  0.306, 2.246, -0.950, 1.166, -0.902, 0.850], 
        [-0.310, 0.810, -0.097, 1.247, -0.420,  1.00, -0.420, 0.842],
        [ 0.317, 0.934,  0.370, 1.074, -0.118, 1.242, -0.176, 1.068],
        [ 1.656, -1.488, 1.523, 0.523, -0.005, -0.621, -0.235, -1.487]
    ]

    def __init__(self, name: str):
        """
        Creates a `MobilityNetwork` instance.
        param: name [str] The name of the network
        """    
        super().__init__(network_name=name)
        def get_memoized_transit(csv_file: str, attributes: list, all:bool=None):
            """
            Creates a dictionary of sub list groups of transit types.
            param: csv_file [str] The file to read
            param: attributes [list] The list of attribute names to make sub lists for 
            param: all [bool] Toggles if a sub list of all content should be made 
            """
            # add "all" sub list if specified 
            if all is not None and all: 
                attributes.append('all')
            # create dictionary of sub lists mapped by keys as their names 
            data_sets = {}
            for attribute in attributes:
                data_sets[str(attribute)] = []
            # open file reader and skip record names
            with open(csv_file, newline='') as file:
                reader = csv.reader(file)
                next(reader)
                # loop through records 
                for record in reader:
                    # get record field data
                    lat = float(decimal(record[0].strip())) # gps latitude 
                    lon = float(decimal(record[1].strip())) # gps longitude 
                    id = str(record[2].strip()) # attribute id
                    # store data in "all" and other sub lists

                    if id in data_sets.keys():
                        data_sets[id].append((lat, lon))
                    if "all" in data_sets.keys():
                        data_sets['all'].append((lat, lon))
            # return results 
            return data_sets

        # look-up hash maps for gps transit stop data; data by transit type and has the lists: "all", and transit specific ones (e.g. metro: "M1", "M2", etc)
        self.bus_stops_gps = get_memoized_transit(csv_file="./cph_mobility_data/bus_gps.csv", attributes=[], all=True)
        self.metro_stops_gps = get_memoized_transit(csv_file="./cph_mobility_data/metro_gps.csv", attributes=[metros.M1.value, metros.M2.value, metros.M3.value, metros.M4.value], all=True)
        self.train_stops_gps = get_memoized_transit(csv_file="./cph_mobility_data/train_gps.csv", attributes=[trains.A.value, trains.B.value, trains.Bx.value, trains.C.value, trains.E.value, trains.H.value, trains.F.value], all=True)

        # node and connection data files 
        self.node_data_file = f"./network_mobility_data/{name}_nodes.csv"
        self.connection_data_file = f"./network_mobility_data/{name}_connections.csv"
        
        # create data files if needed
        if not os.path.exists(self.node_data_file):
            open(self.node_data_file, "x").close()
        if not os.path.exists(self.connection_data_file):
            open(self.connection_data_file, "x").close()
        # add initial records if needed
        with open(self.node_data_file, "r+") as node_gps_file:
            if len(node_gps_file.read()) == 0:
                node_gps_file.write("node_id,lat,lon,municipality,region,type\n")
        with open(self.connection_data_file, "r+") as conn_file:
            if len(conn_file.read()) == 0:
                conn_file.write("conn_id,orig_node_id,dest_node_id,orig_lat,orig_lon,dest_lat,dest_lon,orig_index,dest_index,time_min,distance_km\n")

        # network nodes and connections / edges 
        self.connections = []
        self.nodes = []

    def QUERY(self):
        """
        QUERIES DATA FROM ONLINE API SOURCES! Only import data by query if needed. Otherwise, data should already be queried and stored locally. 
        QUERYING EXITS THE PROGRAM UPON COMPLETION
        """
        for node in self.nodes: # query node positions with geocoded gps samples 
            node.query_node(file=self.node_data_file)
        for node in self.nodes: # query mobility profiles with gps samples
            node.query_profiles(file=self.connection_data_file)
        exit(0)

    def READ(self):
        """
        READS DATA FROM LOCAL PROJECT. Data that has already been queried is read. 
        """
        for node in self.nodes: # read in node positions 
            node.read_node(file=self.node_data_file)
        for node in self.nodes: # read in mobility profiles
            node.read_profiles(file=self.connection_data_file)

    def connection_bike(self, conn_id: str=None, origin_node: MNode=None, dest_node: MNode=None):
        """
        Creates a mobility connection for by bike.
        param: conn_id [str] The unique identifier for this connection 
        param: origin_node [MNode] The start node 
        param: des_node [MNode] The end or destination node
        return: The mobility profile `MProfile`
        """
        # node ID None exception handling 
        origin_node_id = origin_node.node_id if origin_node is not None else None
        dest_node_id = dest_node.node_id if dest_node is not None else None 
        # create profile / connection
        profile = MProfile(connection_id=conn_id, origin_node_id=origin_node_id, destination_node_id=dest_node_id)
        profile.set(mp.mode.BIKING)
        if origin_node is not None:
            origin_node.add_mobility(connection_id=conn_id, dest_node=dest_node, profile=profile)
        self.connections.append(profile)
        return profile 
    
    def connection_walk(self, conn_id: str=None, origin_node: MNode=None, dest_node: MNode=None):
        """
        Creates a mobility connection for by walking.
        param: conn_id [str] The unique identifier for this connection 
        param: origin_node [MNode] The start node 
        param: des_node [MNode] The end or destination node
        return: The mobility profile `MProfile`
        """
        # node ID None exception handling 
        origin_node_id = origin_node.node_id if origin_node is not None else None
        dest_node_id = dest_node.node_id if dest_node is not None else None 
        # create profile / connection 
        profile = MProfile(connection_id=conn_id, origin_node_id=origin_node_id, destination_node_id=dest_node_id)
        profile.set(mp.mode.WALKING)
        if origin_node is not None: 
            origin_node.add_mobility(connection_id=conn_id, dest_node=dest_node, profile=profile)
        self.connections.append(profile)
        return profile 
    
    def connection_automobile(self, conn_id: str=None, origin_node: MNode=None, dest_node: MNode=None):
        """
        Creates a mobility connection for by automobile (e.g. drive by car, etc).
        param: conn_id [str] The unique identifier for this connection 
        param: origin_node [MNode] The start node 
        param: des_node [MNode] The end or destination node
        return: The mobility profile `MProfile`
        """
        # node ID None exception handling 
        origin_node_id = origin_node.node_id if origin_node is not None else None
        dest_node_id = dest_node.node_id if dest_node is not None else None 
        # create profile / connection 
        profile = MProfile(connection_id=conn_id, origin_node_id=origin_node_id, destination_node_id=dest_node_id)
        profile.set(mp.mode.DRIVING)
        if origin_node is not None:
            origin_node.add_mobility(connection_id=conn_id, dest_node=dest_node, profile=profile)
        self.connections.append(profile)
        return profile
    
    def connection_transit(self, conn_id: str, origin_node: MNode, origin_mobility: MProfile, dest_node: MNode, dest_mobility: MProfile, transit_type: mp.transit_mode, transit_line, depart_time: str=None, arrival_time: str=None):
        """
        Creates a three-layer connection across an origin node, transit departure stop node, transit arrival stop node, and destination node. Mobilities  
        as connections are specified for traveling to and from transit stops and for the specific type of transit used between the transit stops.
        param: conn_id [str] The unique base identifier for the overall trip across all three mobility connections 
        param: origin_node [MNode] The origin node to begin a trip from 
        param: origin_mobility [MProfile] The mobility connection for the first leg of the trip to the departure transit stop
        param: dest_node [MNode] The destination node to end the trip at
        param: dest_mobility [MProfile] The mobility connection for the third leg of the trip from the arrival transit stop to the destination
        param: transit_type [mp.transit_mode] Specifies the type of transport between transit stops 
        param: transit_line [enum] Specifies the line, or "all" lines. Expects an enum from `buses`, `metros`, or `trains`
        param: depart_time [str] Optional arg, exclusive to arrival time, that specifies when to arrive at the departure stop 
        param: arrival_time [str] Option arg, exclusive to departure time, that specifies when to arrive at the arrival stop 
        """
        # create a shared transit id extension for both transit stop nodes 
        transit_node_id = int(random.random() * 100) 
        transit_node_name = {mp.transit_mode.BUS: "bus", mp.transit_mode.SUBWAY: "metro", mp.transit_mode.TRAIN: "train"}.get(transit_type)
        # transit nodes share id of the origin / dest node they directly connect to; then they share a common transit id combined
        depart_node_id = f"{conn_id}_{transit_node_name}_depart_{transit_node_id}"
        arrival_node_id = f"{conn_id}_{transit_node_name}_arrival_{transit_node_id}"
        
        # create nodes at transit stops 
        depart_stop_node = MNode(bus_stops_gps=self.bus_stops_gps, metro_stops_gps=self.metro_stops_gps, train_stops_gps=self.train_stops_gps, id=depart_node_id, 
                                        catchment_node=origin_node, transit_type=transit_type, transit_line=transit_line, filter_gps_zones=None)
        arrival_stop_node = MNode(bus_stops_gps=self.bus_stops_gps, metro_stops_gps=self.metro_stops_gps, train_stops_gps=self.train_stops_gps, id=arrival_node_id,
                                        catchment_node=dest_node, transit_type=transit_type, transit_line=transit_line, filter_gps_zones=None)

        # create the transit connection profile 
        transit_profile = MProfile(connection_id=conn_id, origin_node_id=depart_node_id, destination_node_id=arrival_node_id)
        transit_profile.set(mp.mode.TRANSIT) 
        transit_profile.set(transit_type) # give specified type

        # set transit profile with timing criteria 
        if depart_time is not None and arrival_time is None:
            transit_profile.set(mp.timing.SET_DEPARTURE, depart_time)
        elif depart_time is None and arrival_time is not None:
            transit_profile.set(mp.timing.SET_ARRIVAL, arrival_time)

        # attach connections to initial and final profiles for the start and end of the trip mobilities
        origin_mobility.attach(connect_id=f"{conn_id}_orig_mob", origin_node_id=origin_node.node_id, destination_node_id=depart_node_id)
        dest_mobility.attach(connect_id=f"{conn_id}_dest_mob", origin_node_id=arrival_node_id, destination_node_id=dest_node.node_id)

        # add mobility connections to nodes 
        origin_node.add_mobility(connection_id=conn_id, dest_node=depart_stop_node, profile=origin_mobility)
        depart_stop_node.add_mobility(connection_id=conn_id, dest_node=arrival_stop_node, profile=transit_profile)
        arrival_stop_node.add_mobility(connection_id=conn_id, dest_node=dest_node, profile=dest_mobility)
        # append created nodes and connections to network
        self.nodes.append(depart_stop_node)
        self.nodes.append(arrival_stop_node)
        # append the transit connection 
        self.connections.append(transit_profile) 
        # append initial and final mobilities if they have not yet been
        self.connections.append(origin_mobility)
        self.connections.append(dest_mobility)

        # return the profiles of the trip in order
        return (origin_mobility, transit_profile, dest_mobility)

    def connection_bus(self, conn_id: str, origin_node: MNode, origin_mobility: MProfile, dest_node: MNode, dest_mobility: MProfile, bus_line, depart_time:str=None, arrival_time:str=None):
        """
        Creates a mobility connection for by public transit bus. Specified times are optional but one or the other must be given. 
        Times should be passed in strings that are formatted by use of `mp.TIMING()` function.
        param: conn_id [str] The unique identifier for this connection 
        param: origin_node [MNode] The start node 
        param: des_node [MNode] The end or destination node
        param: depart_time [str] The optional departure time 
        param: arrive_time [str] The optional arrival time 
        return: The mobility profile `MProfile`
        """
        trip_profiles = self.connection_transit(conn_id, origin_node, origin_mobility, dest_node, dest_mobility, mp.transit_mode.BUS, bus_line, depart_time, arrival_time)
        return trip_profiles # return the trip mobility
    
    def connection_metro(self, conn_id: str, origin_node: MNode, origin_mobility: MProfile, dest_node: MNode, dest_mobility: MProfile, metro_line: metros, depart_time:str=None, arrival_time:str=None):
        """
        Creates a mobility connection for by public transit metro. Specified times are optional but one or the other must be given. 
        Times should be passed in strings that are formatted by use of `mp.TIMING()` function.
        param: conn_id [str] The unique identifier for this connection 
        param: origin_node [MNode] The start node 
        param: des_node [MNode] The end or destination node
        param: depart_time [str] The optional departure time 
        param: arrive_time [str] The optional arrival time 
        return: The mobility profile `MProfile`
        """
        trip_profiles = self.connection_transit(conn_id, origin_node, origin_mobility, dest_node, dest_mobility, mp.transit_mode.SUBWAY, metro_line, depart_time, arrival_time)
        return trip_profiles # return the trip mobility
    
    def connection_train(self, conn_id: str, origin_node: MNode, origin_mobility: MProfile, dest_node: MNode, dest_mobility: MProfile, train_line: trains, depart_time:str=None, arrival_time:str=None):
        """
        Creates a mobility connection for by public transit train. Specified times are optional but one or the other must be given. 
        Times should be passed in strings that are formatted by use of `mp.TIMING()` function.
        param: conn_id [str] The unique identifier for this connection 
        param: origin_node [MNode] The start node 
        param: des_node [MNode] The end or destination node
        param: depart_time [str] The optional departure time 
        param: arrive_time [str] The optional arrival time 
        return: The mobility profile `MProfile`
        """
        trip_profiles = self.connection_transit(conn_id, origin_node, origin_mobility, dest_node, dest_mobility, mp.transit_mode.TRAIN, train_line, depart_time, arrival_time)
        return trip_profiles # return the trip mobility
    
    def node_10(self, node_id: str, gps: tuple, radius: float, filter_gps_zones: list):
        """
        Creates a mobility node with a sample size of 10 gps coordinate positions. 
        param: node_id [str] The unique identifier for this node 
        param: gps [tuple] The coordinates in the form of (float=latitude, float=longitude)
        param: radius [float] The radius of the node in [km]
        param: filter_gps_zones [list] The list of 8D tuples for each element (x0,y0,x1,y1,x2,y2,x3,y3) bounds a convex shape to not sample from. 
        return: The mobility node `MNode`
        """
        node = MNode(bus_stops_gps=self.bus_stops_gps, metro_stops_gps=self.metro_stops_gps, train_stops_gps=self.train_stops_gps, 
                            id=node_id, root_lat=gps[0], root_lon=gps[1], area_radius=radius, n=10, filter_gps_zones=filter_gps_zones)
        self.nodes.append(node)
        return node
    def node_30(self, node_id: str, gps: tuple, radius: float, filter_gps_zones: list):
        """
        Creates a mobility node with a sample size of 30 gps coordinate positions. 
        param: node_id [str] The unique identifier for this node 
        param: gps [tuple] The coordinates in the form of (float=latitude, float=longitude)
        param: radius [float] The radius of the node in [km]
        param: filter_gps_zones [list] The list of 8D tuples for each element (x0,y0,x1,y1,x2,y2,x3,y3) bounds a convex shape to not sample from. 
        return: The mobility node `MNode`
        """
        node = MNode(bus_stops_gps=self.bus_stops_gps, metro_stops_gps=self.metro_stops_gps, train_stops_gps=self.train_stops_gps, 
                            id=node_id, root_lat=gps[0], root_lon=gps[1], area_radius=radius, n=30, filter_gps_zones=filter_gps_zones)
        self.nodes.append(node)
        return node
    def node_set(self, node_id: str, gps_locations: list):
        """
        Creates a mobility node with a known sample from the specified list of gps locations that take the form of 2D tuples of latitude and longitude per location. 
        param: node_id [str] The unique identifier for this node 
        param: gps_locations [list] The specified known locations as a set of GPS coord tuples 
        """
        node = MobilityNode(bus_stops_gps=self.bus_stops_gps, metro_stops_gps=self.metro_stops_gps, train_stops_gps=self.train_stops_gps, 
                            id=node_id, n=len(gps_locations), set_locations=gps_locations)
        self.nodes.append(node)
        return node