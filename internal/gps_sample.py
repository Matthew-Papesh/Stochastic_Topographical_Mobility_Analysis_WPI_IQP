import math
import random
import matplotlib.pyplot as plt
from internal.mobility_profile import *

class GPSSample: 
    """
    Represents a sample of meaning GPS coordinates. Meaningful coordinates are those that are known locations such as shops, houses, parks, benches, hospitals, etc. 
    """
    class Location: 
        """
        Represents the location of a nearby GPS coordinate with qualitative data. 
        """
        def __init__(self, lat: float, lon: float, type: float=None, municipality: str=None, region: str=None): 
            """
            Gets data on the nearest location to the specified GPS coordinates from either query via the openstreetmap API or 
            by loading in data locally. If the optional parameters are not given, the data is queried from the API and not otherwise. 
            param: lat [float] The starting latitude to find a location near 
            param: lon [float] The starting longitude to find a location near 
            param: type [str] Optional arg for giving a category of city, town, house, etc
            param: municipality [str] Optional arg for giving a municipal area 
            param: region [str] Optional arg gor giving a region 
            """
            # type : city, town, village, primary/res highway, house/commercial building, school/house amenity
            self.type, self.municipality, self.region = "n/a", "n/a", "n/a" 
            # location gps coordinates 
            self.gps_coordinate = None 
            # query data from the api if no optional args were given
            if type is None and municipality is None and region is None:
                data = self.geocoding(lat, lon) # retrieved location data
                self.gps_coordinate = (float(data["lat"]), float(data["lon"])) # gps
                try: # handle finding qualitative info
                    self.type = str(data.get("place", "UNKNOWN")) + "_" + str(data.get("type", "UNKNOWN")) 
                    self.municipality = data["address"]["municipality"] 
                    self.region = data["address"]["state"]
                except:
                    pass
            # store the given info from optional args
            else:
                self.gps_coordinate = (lat, lon)
                self.type = type 
                self.municipality = municipality
                self.region = region

        def geocoding(self, lat: float, lon: float): 
            """
            Estimates the address and qualitative information of a nearby location to a specified GPS coordinate. 
            param: lat [float] The specified latitude to approximate from
            param: lon [float] The specified longitude to approximate from 
            return: data
            """
            # format url for reverse geocoding: get info of nearby location from GPS position via us of openstreet api
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            return requests.get(url, headers={"User-Agent": "mobility_research_project_WPI_2025"}).json() # retrieve response data in json format

    def calc_local_gps(self, lat_0: float, lon_0: float, radius: float, bearing: float):
        """
        Calculates the GPS coordinates radially from a central root position. 
        :param lat_0 [float] Central root latitude 
        :param lon_0 [float] Central root longitude 
        :param radius [float] Offset radius in [km] from central root position
        :param bearing [float] Angle of radial offset 
        :return Offset local GPS position 
        """
        R_e = 6378  # earth radius in km
        # Compute new latitude
        lat_1 = math.asin(math.sin(lat_0) * math.cos(radius / R_e) + math.cos(lat_0) * math.sin(radius / R_e) * math.cos(bearing))
        # Compute new longitude
        lon_1 = lon_0 + math.atan2(math.sin(bearing) * math.sin(radius / R_e) * math.cos(lat_0), math.cos(radius / R_e) - math.sin(lat_0) * math.sin(lat_1))
        return (math.degrees(lat_1), math.degrees(lon_1))

    def fetch_radial_location_sample(self, lat_0: float, lon_0: float, radius: float, n: int, filter_zones: list) -> list:
        """
        Samples locations within a radius given a central root position `(lat_0, lon_0)`. Returned data takes the form of a vector 
        (municipality_sampling_dict, region_sampling_dict, location_type_sampling_dict, locations)
        :param lat_0 [float] Central root latitude 
        :param lon_0 [float] Central root longitude 
        :param radius [float] Radius to sample within
        :param n [int] Sample size
        :param filter_zones [list] List of 8D tuples. Each element (x0,y0,x1,y1,x2,y2,x3,y3) is a bounded region to not sample from
        :return list of location(s) with qualitative data. 
        """
        lat_0 = math.radians(lat_0)
        lon_0 = math.radians(lon_0)
        locations = [] # list of locations 
        # categorical statistics on sampled locations
        municipality_statistics = {} 
        region_statistics = {}
        type_statistics = {}

        def count_location(dictionary, key):
            """
            Counts the number of a given attribute as a dictionary mapping between attribute key and its count. 
            The mapped dictionary count is incremented for each time a familiar key is given; new keys are mapped to zero. 
            param: dictionary [any] The specified dictionary for statistics
            param: key [any] A specified key for the dictionary.  
            """
            if key in dictionary:
                dictionary[key] += 1
            else:
                dictionary[key] = 1

        Ts, Rs, = [], [] 
        # step through random sample of coordinates 
        for i in range(0, n):
            # find radial position (R, theta) within sample zone
            theta, R = None, None
            run_filter = True 
            while run_filter:
                run_filter = False # get position (theta,R) and assume its outside of filtered regions 
                theta = random.random() * 2.0 * math.pi # Assuming outside filtered regions, turn filter off 
                R = math.pow(random.random(), 0.5) * radius
                # check all filter regions 
                for filter in filter_zones:
                    # coords bounding a convex shape
                    a0, b0, a1, b1 = filter[0], filter[1], filter[2], filter[3]
                    a2, b2, a3, b3 = filter[4], filter[5], filter[6], filter[7]
                    # get position in cartesian coords 
                    pos_x, pos_y = R * math.cos(theta), R * math.sin(theta)

                    # linear functions, and inverses, of bounded convex shape
                    def inv_left_bound(y: float):
                        return (((y-b2) * (a3-a2)) / (b3-b2)) + a2
                    def inv_right_bound(y: float):
                        return (((y-b0) * (a1-a0)) / (b1-b0)) + a0
                    def up_bound(x: float):
                        return (((b2-b1) / (a2-a1)) * (x-a1)) + b1
                    def down_bound(x: float):
                        return (((b0-b3) / (a0-a3)) * (x-a3)) + b3

                    # get points where, a cross "+" projects from the position, intersects the bounds 
                    horizontal_bound_intersections = (up_bound(x=pos_x), down_bound(x=pos_x))
                    vertical_bound_intersections = (inv_left_bound(y=pos_y), inv_right_bound(y=pos_y))
                    # get bounding min/max x/y from where there are intersections 
                    up_y = max(horizontal_bound_intersections[0], horizontal_bound_intersections[1])
                    down_y = min(horizontal_bound_intersections[0], horizontal_bound_intersections[1])
                    right_x = max(vertical_bound_intersections[0], vertical_bound_intersections[1])
                    left_x = min(vertical_bound_intersections[0], vertical_bound_intersections[1])

                    # check if position is inside regions 
                    if pos_x >= left_x and pos_x <= right_x and pos_y >= down_y and pos_y <= up_y:
                        run_filter = True # inside region, flag to continue the filter
                        break # we know this is an out-of-bounds position; end check with filter still running
                # if check loop completes and filter is False, the position is within bounds 

            # find corresponding GPS coordinate
            lat_1, lon_1 = self.calc_local_gps(lat_0, lon_0, R, theta)
            # only give gps coordinates; geocode to get location
            location = self.Location(lat_1, lon_1)
            locations.append(location) # record location
            # sum attribute data for the whole sample 
            count_location(municipality_statistics, location.municipality) 
            count_location(region_statistics, location.region)
            count_location(type_statistics, location.type)
            print(f"{i}/{n}")

            Ts.append(theta)
            Rs.append(R)

        # Set up polar plot
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
        # Plot the points
        ax.plot(Ts, Rs, 'o', label='Polar Points')
        # Show the plot
        plt.show()

        return (municipality_statistics, region_statistics, type_statistics, locations) # return sample