from internal.mobility_network_base import *
import matplotlib.pyplot as plt
import numpy as np

class OsterportNetwork(MobilityNetworkBase):
    def __init__(self):
        super().__init__(name="PILOT_osterport")

        self.hotel_9_node = self.node_30(node_id="hotel_9", gps=(55.69719963723292, 12.584430781731745), radius=1.5, filter_gps_zones=self.copenhagen_central_avoid_gps_filter)
        self.osterport_node =self.node_30(node_id="osterport", gps=(55.69403577472335, 12.586553673755699), radius=1.0, filter_gps_zones=self.nordhavn_avoid_gps_filters)
        self.indre_by_node = self.node_30(node_id="indre_by", gps=(55.68154580802538, 12.584904309902273), radius=1.0, filter_gps_zones=[])

        # network connections  
        self.metro_conn = self.connection_metro(conn_id="ost_transit", origin_node=self.hotel_9_node, origin_mobility=self.connection_walk(), dest_node=self.indre_by_node, dest_mobility=self.connection_walk(), metro_line=metros.all.value)
        self.bus_conn = self.connection_bus(conn_id="ost", origin_node=self.hotel_9_node, origin_mobility=self.connection_walk(), dest_node=self.indre_by_node, dest_mobility=self.connection_walk(), bus_line=buses.all.value)
        
        # READ / QUERY Trip Data from DistanceMatrixAI API
        #self.READ()

        

if __name__ == "__main__":
    network = OsterportNetwork()