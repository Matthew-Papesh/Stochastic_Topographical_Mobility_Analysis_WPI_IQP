from internal.gps_sample import *
from internal.mobility_node import *
from decimal import Decimal as decimal
from internal.handler import *
import os.path
import random
import shapefile 
from shapely.geometry import Point
from shapely.geometry import shape
import pandas as pd
import geopandas as gpd
import fiona
import numpy as np

class MobilityTripSampler:
    """
    Represents the mechanism that samples time and distance mobility data from a set of connections that belong to a `MobilityNetworkBase` instance. 
    To sum time and distance estimations for many connections on a mobility graph allows for larger trips' time and distance to be estimated. The
    individual connections can be considered as sub trips in a list of otherwise longer trips that are made up of these sub trips. 
    """
    def __init__(self, network_name: str):
        """
        Creates a `MobilityTripSampler` instance. 
        param: network_name [str] The specified network name
        """
        # dict of all trip samples collected
        self.sampled_trips = {}
        # name of the network
        self.network_name = network_name
        # the file to export samples to
        self.results_data_file = f"./stma_results/{network_name}_results.csv"
        # base directory for visualizing mobility heatmap data
        self.HEATMAP_DATA_FILE_BASE = f"./heatmap_results/"
        # create data files if needed
        if not os.path.exists(self.results_data_file):
            open(self.results_data_file, "w").close()
        
    def WRITE_STMA(self):
        """
        Writes `MobilityTripSampler` results and exports them to a file corresponding to the associated mobility 
        network. Data is exported to the `stma_results` folder. 
        """
        with open(self.results_data_file, "w+") as results_file:
            if len(results_file.read()) == 0:
                results_file.write("sample_id,time_min,distance_km,location_gps_list\n")
            for sample in self.sampled_trips.values():
                for trip in sample:
                    results_file.write(f"{trip[0]},{trip[1]},{trip[2]},\"{trip[3]}\"\n")

    def READ_STMA(self): 
        """
        Reads `MobilityTripSampler` results and imports them into the program at runtime. The contents are returned in the form of 
        a dictionary of lists. Lists are sorted by sample identifier and each contain trip data on time (min) and distance (km) per trip. 
        return: The STMA results.
        """
        stma_results = {}
        with open(self.results_data_file, "r+") as results_file:
            for record in csv.reader(results_file):
                if str(record[0]) == "sample_id":
                    continue
                sample_id, time_min, distance_km = str(record[0]), float(record[1]), float(record[2])
                str_gps_locations = str(record[3]).replace('[','').replace(']','').replace('(','').replace(')','').replace(',','').split()
                gps_locations = []
                for i in range(0, len(str_gps_locations)):
                    if i % 2 == 0:
                        gps_locations.append((float(decimal(str_gps_locations[i])), 0))
                    else: 
                        index = max(0, len(gps_locations) - 1)
                        gps_locations[index] = (gps_locations[index][0], float(decimal(str_gps_locations[i])))

                for i in range(1, len(gps_locations)):
                    lat_0, lon_0 = gps_locations[i - 1][0], gps_locations[i - 1][1]
                    lat_1, lon_1 = gps_locations[i][0], gps_locations[i][1]
                    if sample_id not in stma_results.keys():
                        stma_results[sample_id] = []
                    stma_results[sample_id].append((time_min, distance_km, lat_0, lon_0, lat_1, lon_1))
        return stma_results

    def visualize_trips(self, sample_id: str, res: int, type: str, gps_0: tuple, gps_1: tuple, heatmap_id: str, aggregate_type: str, on_cph_land: bool): 
        """
        Visualizes trips with Matplotlib. Shows a trip as lines connecting the trip's locations and colors them based on speed weights. 
        param: sample_id [str] The specified STMA results to visualize 
        param: type [str] The type of data to show; can be `time`, `distance`, or `speed`
        param: heatmap_id [str] The unique identifier for the visualization
        param: aggregate_type [str] How to aggregate weights by either `mean` or `median`
        param: on_cph_land [bool] Whether or not to filter out heatmap points outside of the physical land of the greater Copenhagen area
        """
        if type != 'speed' and type != 'distance' and type != 'time':
            return None
        # get trips based on sample id from STMA results 
        trips = self.READ_STMA()[sample_id]
        # init matplotlib
        fig = plt.figure()
        ax = fig.add_subplot()
        data_x, data_y, data_z = [], [], []
        data_tile = []
        
        # step through trips 
        for trip_i in range(0, len(trips)):
            # get trip data
            time_min, distance_km, lat_0, lon_0, lat_1, lon_1 = trips[trip_i]
            weight = 0 # get weight for heatmap
            if type == 'time':
                weight = time_min
            elif type == 'distance':
                weight = distance_km
            elif type == 'speed':
                weight = distance_km / time_min

            lats, lons = interpolate(lat_0, lon_0, lat_1, lon_1, res)
            n = min(len(lats), len(lons)) 
            # iterpolate points to create line path between 
            # origin and dest points of a trip
            for i in range(0, n):
                # add interpolated points and the associated trip speed 
                data_x.append(lats[i])
                data_y.append(lons[i])
                data_z.append(weight)
                data_tile.append((None, 0, 0))
        
        h, w = 100, 100 # number of tiles for grid heatmap
        lat_res = abs(gps_1[0] - gps_0[0]) / w
        lon_res = abs(gps_1[1] - gps_0[1]) / h 
       
        map = None
        # 2D matrix of (lat, lon, avg weight, and weight count) per element
        if aggregate_type == "mean":
            map = [[(x*lat_res + gps_0[0], y*lon_res + gps_0[1], 0, 0) for x in range(0, w)] for y in range(0, h)]
        # 2D matrix of (lat, lon, list of weights, None) per element
        elif aggregate_type == "median":
            map = [[(x*lat_res + gps_0[0], y*lon_res + gps_0[1], [], None) for x in range(0, w)] for y in range(0, h)]
        # no type; do nothing
        else:
            return

        n = min(min(min(len(data_x), len(data_y)), len(data_z)), len(data_tile))
        # step through map
        for y in range(0, len(map)):
            for x in range(0, len(map[y])):
                # get tile gps coords
                tile_lat, tile_lon = map[y][x][0], map[y][x][1]
                # update list of data to be put on tiles, `data_tiles`, to update that datas' closest tile 
                # we want to update the tile that is closest to each raw coordinate interpolated from the section above
                # we upate as we go through the map and look at new tiles until the whole map has been looked at
                for i in range(0, n):
                    # get current raw data point gps coords 
                    lat_i, lon_i = data_x[i], data_y[i]
                    # determine distance to current tile 
                    distance_i = pow(pow(lat_i - tile_lat, 2.0) + pow(lon_i - tile_lon, 2.0), 0.5)
                    # update this data point's closest tile (indices) if this is the closest so far
                    if data_tile[i][0] is None or distance_i < data_tile[i][0]:
                        # update the closest tile and the distance found
                        data_tile[i] = (distance_i, x, y)

        # data to plot and export # 2D matrix of (lat, lon, avg weight, and weight count) per element
        plot_data_x = [] # list of lat
        plot_data_y = [] # list of lon
        plot_data_z = [] # list of weights

        # geopgraphical shape data for copenhagen
        cph_polygon_data = None
        with fiona.open("./kvarter_data/kvarterPolygon.shp", "r") as land_shapes:
            cph_polygon_data = [shape(feature["geometry"]) for feature in land_shapes]

        for i in range(0, n):
            x = data_tile[i][1]
            y = data_tile[i][2]
            weight = data_z[i] 
            # aggregate onto map by averaging
            if aggregate_type == "mean":
                map[y][x] = (map[y][x][0], map[y][x][1], map[y][x][2] + weight, map[y][x][3] + 1)
            # aggregate onto map by medians
            elif aggregate_type == "median":
                weights = map[y][x][2]
                weights.append(weight)
                map[y][x] = (map[y][x][0], map[y][x][1], weights, None)
                
        for y in range(0, len(map)):
            for x in range(0, len(map[0])):
                gps_point = Point(map[y][x][1], map[y][x][0])
                if not on_cph_land or any(poly.contains(gps_point) for poly in cph_polygon_data):
                    # aggregate onto map by averaging
                    if aggregate_type == "mean" and map[y][x][3] > 0:
                        map[y][x] = (map[y][x][0], map[y][x][1], map[y][x][2] / map[y][x][3], map[y][x][3])
                        plot_data_x.append(map[y][x][0])
                        plot_data_y.append(map[y][x][1])
                        plot_data_z.append(map[y][x][2])
                    # aggregate onto map by medians
                    elif aggregate_type == "median" and map[y][x][2]:
                        map[y][x] = (map[y][x][0], map[y][x][1], np.median(map[y][x][2]), None)
                        plot_data_x.append(map[y][x][0])
                        plot_data_y.append(map[y][x][1])
                        plot_data_z.append(map[y][x][2])

        # visualize with matplotlib
        sc = ax.scatter(plot_data_x, plot_data_y, c=plot_data_z, cmap='viridis')
        plt.colorbar(sc, ax=ax).set_label(f"Trip {type}")
        plt.show()

        # create data files if needed
        if not os.path.exists(self.HEATMAP_DATA_FILE_BASE + heatmap_id + ".csv"):
            open(self.HEATMAP_DATA_FILE_BASE + heatmap_id + ".csv", "x").close()
        # write results to heatmap file
        with open(self.HEATMAP_DATA_FILE_BASE + heatmap_id + ".csv", "r+") as results_file:
            # write col names
            if len(results_file.read()) == 0:
                results_file.write(f"lat,lon,{type}\n")
            N = min(min(len(plot_data_x), len(plot_data_y)), len(plot_data_z))
            # write heatmap results
            for i in range(0, N):
                results_file.write(f"{plot_data_x[i]},{plot_data_y[i]},{plot_data_z[i]}\n")


    def sample_trip(self, sample_id: str, n: int, connections: list):
        """
        Samples a number of trips that sequentially travel across the list of connections given. Results are saved 
        and can be written to a file by calling `WRITE()`
        param: sample_id [str] The unique identifier for this sample
        param: n [int] The number of trips to sample 
        param: connections [list] The list of `MProfile` connections to estimate trips from
        return: The sample data as a list of 2D tuples of (time_min, distance_km) of each trip
        """
        
        # ~~~ CONCEPT EXPLANATION (How to think of possible paths to sample) ~~~ 
        # think of each trip sampled as a path down a tree of all possible trips. 
        # each node in the tree is a location belonging to a mobility node.
        # each layer in the tree is the next mobility node's locations 
        # the first mobility node locations do not connect/come from anywhere, but each other moblity nodes' locations do; 
        # this means all nodes in the tree connect to all child nodes in the next following layer, where the first layer is the set of
        # starting locations of the first node that are not connected to each other; this creates a tree for each location in the first mobility node, 
        # where each said location is the root of their tree. 
        # ~~~ WHAT TO DO BELOW (The proceeding algorithm below) ~~~
        # (1) create a running list of trips to sample, and sample random sub trips that are connected across tree levels to create each trip
        # (2) for each trip: choose a random root tree location; for each level, randomly choose a location so that a direct connection between two locations is a sub trip
        # (3) for each trip: select a random  location for each level that have a direct connection to the last node/location selected in the previous level; this creates a connected path from 
        #     the root to a leaf location in a tree.
        # ~~~ HOW TO DO BELOW (How to implement the algorithm) ~~~
        # (1) each connection's list of sub trips represent all allowed connections between a starting and next tree location => randomly choose a sub trip from the first connection
        # (2) put each initial sub trip of the first connection (from the function arg `connections: list`) in a running list of overall trips in order. 
        # (3) loop through remaining connections of arg `connections: list` for finding a random sub trip from each one to add to sum in each overall trip in that list. Sub trips to sample from are
        #     rooted at the location of the previous layer so that an overall connected path from the root location to a leaf location in the tree can be found and summed across its set of sub trips.   
        
        # ~~~ Implementation below ~~~
        
        # sampled list of overall trips; each data pair (min, km) represents the total time and distance for one trip
        # a trip is recorded as: sample_id, time_min, distance_km, and a list of visited locations
        trip_data = [("",0,0,list()) for i in range(0, n)]
        prev_gps_points = [(None,None) for i in range(0, n)]
    
        # loop through all connections; going from the first to the next until done 
        for conn_index in range(0, len(connections)):
            conn = connections[conn_index]
            # local trips for over just this connection
            all_sub_trips = conn.get()

            # loop through all trips being estimated; continue "building" each trip at each connection 
            # along the list of given connections 
            for i in range(0, n):
                # local sub trips for this connection, for the i-th overall trip
                # overall trips are formed by growing all (n) of them, one sub trips each at a time, while stepping through each connection (conn_index)
                sub_trips = [] # tailor filter to find all sub trips directly connected to where the growing i-th overall trip left of in the previous connection (conn_index)
                # filter sub trips that are not from the first connections  
                if conn_index > 0: 
                    for sub_trip in all_sub_trips:
                        prev_sub_trip_location_lat, prev_sub_trip_location_lon = prev_gps_points[i][0], prev_gps_points[i][1]
                        if sub_trip[2] == prev_sub_trip_location_lat and sub_trip[3] == prev_sub_trip_location_lon:
                            sub_trips.append(sub_trip)
                else:
                    # do not filter the first connection
                    sub_trips = all_sub_trips

                # randomly choose from filtered set of sub trips 
                sub_trip_index = max(0, int(len(sub_trips) * random.random() - 1))
                sub_trip = sub_trips[sub_trip_index] # time (min), distance (km)
                # add time and distance for sub trip
                time_min_sum = trip_data[i][1] + sub_trip[0]
                distance_km_sum = trip_data[i][2] + sub_trip[1]
                # next "destination" node gps for this current connection sub trip
                dest_lat, dest_lon = sub_trip[4], sub_trip[5]
                orig_lat, orig_lon = sub_trip[2], sub_trip[3]
                # update time, distance, and locations list data
                trip_locations = trip_data[i][3]
                # append origin for first node on first connection; assume this if list is empty
                if len(trip_locations) == 0: 
                    trip_locations.append((orig_lat, orig_lon))
                # append all destinations proceeding after the first node origin location was added once
                trip_locations.append((dest_lat, dest_lon))
                trip_data[i] = (sample_id, time_min_sum, distance_km_sum, trip_locations)
                # update previous gps points for each trip
                prev_gps_points[i] = (dest_lat, dest_lon)
        # store and return results 
        self.sampled_trips[sample_id] = trip_data
        return trip_data
# short-hand alias 
MTSample = MobilityTripSampler