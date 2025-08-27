from internal.mobility_network_base import *
import matplotlib.pyplot as plt
import numpy as np

class TingbjergNetwork(MobilityNetworkBase):
    def __init__(self):
        super().__init__(name="tingbjerg")
        # create nodes 
        self.inner_node = self.node_30(node_id="inner", gps=(55.72001065185823,12.485834564015878), radius=0.75, filter_gps_zones=[])
        self.frontier_node = self.node_30(node_id="frontier", gps=(55.72001065185823,12.485834564015878), radius=1.5, filter_gps_zones=[])
        self.cph_central_node = self.node_30(node_id="cph_central", gps=(55.67157021678844, 12.564402972197449), radius=0.75, filter_gps_zones=self.copenhagen_central_avoid_gps_filter)
        self.local_train_stop_node = self.node_set(node_id="local_train_stop", gps_locations=[(55.70956274448479, 12.46383995872404)])

        # create connections 
        self.walkability = self.connection_walk(conn_id="walk", origin_node=self.inner_node, dest_node=self.frontier_node)
        self.bikeability = self.connection_bike(conn_id="bike", origin_node=self.inner_node, dest_node=self.frontier_node)
        self.local_transit = self.connection_bus(conn_id="local", origin_node=self.inner_node, origin_mobility=self.connection_walk(), 
                                            dest_node=self.frontier_node, dest_mobility=self.connection_walk(), bus_line=buses.all.value, 
                                            depart_time=mp.TIMING(year=2025, month=4, day=1, hour=9, minute=0))
        self.city_commute = self.connection_bus(conn_id="commute", origin_node=self.inner_node, origin_mobility=self.connection_walk(), 
                                             dest_node=self.cph_central_node, dest_mobility=self.connection_walk(), bus_line=buses.all.value, 
                                             depart_time=mp.TIMING(year=2025, month=4, day=1, hour=9, minute=0))
        self.alt_city_commute_bus = self.connection_bus(conn_id="alt_commute", origin_node=self.inner_node, origin_mobility=self.connection_walk(), 
                                            dest_node=self.local_train_stop_node, dest_mobility=self.connection_walk(), bus_line=buses.all.value,
                                            depart_time=mp.TIMING(year=2025, month=4, day=1, hour=9, minute=0))
        self.alt_city_commute_train = self.connection_train(conn_id="alt_commute", origin_node=self.local_train_stop_node, origin_mobility=self.connection_walk(),
                                            dest_node=self.cph_central_node, dest_mobility=self.connection_walk(), train_line=trains.all.value,
                                            depart_time=mp.TIMING(year=2025, month=4, day=1, hour=9, minute=0))

        # QUERY / READ
        self.READ()
        #self.visualize_trips(sample_id="walk", res=3, type='time', gps_0=(55.70419549513111, 12.455375738098168), gps_1=(55.73130208924672, 12.515764291808315), heatmap_id="tingbjerg_walk_time", aggregate_type="mean", on_cph_land=False)
        #self.visualize_trips(sample_id="bike", res=3, type='time', gps_0=(55.70419549513111, 12.455375738098168), gps_1=(55.73130208924672, 12.515764291808315), heatmap_id="tingbjerg_bike_time", aggregate_type="mean", on_cph_land=False)

        # compute STMA
        #self.walkability_trips = self.sample_trip(sample_id="walk", n=2000, connections=[self.walkability])
        #self.bikeability_trips = self.sample_trip(sample_id="bike", n=2000, connections=[self.bikeability])
        #self.local_transit_trips = self.sample_trip(sample_id="local", n=2000, connections=[self.local_transit[0], self.local_transit[1], self.local_transit[2]])
        #self.city_commute_trips = self.sample_trip(sample_id="commute", n=2000, connections=[self.city_commute[0], self.city_commute[1], self.city_commute[2]])
        
        #self.atl_city_commute_trips = self.sample_trip(sample_id="alt_commute", n=2000, connections=[self.alt_city_commute_bus[0], self.alt_city_commute_bus[1], self.alt_city_commute_bus[2],
        #                                                                                             self.alt_city_commute_train[0], self.alt_city_commute_train[1], self.alt_city_commute_train[2]])

        # WRITE STMA results 
        #self.WRITE_STMA()

if __name__ == "__main__":
    network = TingbjergNetwork()