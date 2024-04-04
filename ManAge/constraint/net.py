import re
import networkx as nx
from itertools import product
from xil_res.node import Node as nd
import utility.config as cfg

class Net:

    def __init__(self, name, G):
        self.name       = name
        self.constraint = self.get_constraint(G)

    def __repr__(self):
        return f'Net(name={self.name})'

    @staticmethod
    def RRG(G):
        RRG = nx.DiGraph()
        RRG.add_edges_from(G.edges())
        wires_end = {edge[1] for edge in G.edges if nd.get_tile(edge[0]) != nd.get_tile(edge[1])}
        for node in wires_end:
            new_edges = product(G.predecessors(node), G.neighbors(node))
            RRG.remove_node(node)
            RRG.add_edges_from(new_edges)

        return RRG

    def get_constraint(self, G):
        G = Net.RRG(G)
        constraint = f'set_property FIXED_ROUTE {{{self.get_netlist_routing_const(G)}}} [get_nets {self.name}]\n'

        return constraint

    @staticmethod
    def get_netlist_routing_const(G):
        route = []
        trunk = Net.get_trunk(G)
        for node in trunk:
            if G.out_degree(node) > 1:
                port = nd.get_port(node)
                other_neighs = set(G.neighbors(node)) - set(trunk)
                for neigh in other_neighs:
                    G_neigh = nx.dfs_tree(G, neigh)
                    port = f'{port} {{{Net.get_netlist_routing_const(G_neigh)}}}'

                route.append(port)
            else:
                route.append(nd.get_port(node))

        return ' '.join(route)

    @staticmethod
    def get_trunk(G: nx.DiGraph):
        source = [node for node in G if G.in_degree(node) == 0].pop()
        sinks = [node for node in G if G.out_degree(node) == 0]
        for sink in sinks:
            G.add_edge(sink, 't')

        trunk = nx.all_simple_paths(G, source, 't')
        trunk = [path[:-1] for path in trunk]
        trunk.sort(key=len)
        G.remove_node('t')

        return trunk[-1]

    @staticmethod
    def get_g_buffer(G):
        #buffer_in = list(filter(lambda node: cfg.LUT_in_pattern.match(node) and G.out_degree(node) != 0, G))
        if any(filter(lambda node: cfg.MUXED_CLB_out_pattern.match(node), G)):
            g_buffer = "00"

        elif any(filter(lambda node: cfg.LUT_in_pattern.match(node) and G.out_degree(node) != 0, G)):
            buffer_in = next(filter(lambda node: cfg.LUT_in_pattern.match(node) and G.out_degree(node) != 0, G))
            not_in = next(filter(lambda node: cfg.LUT_in_pattern.match(node) and G.out_degree(node) == 0, G))
            neigh = next(G.neighbors(buffer_in))
            src = next(node for node in G if G.in_degree(node) == 0)
            sink = next(node for node in G if G.out_degree(node) == 0 and re.match(cfg.FF_in_pattern, node))
            brnch_node = [node for node in G if G.out_degree(node) > 1]
            if brnch_node:
                brnch_node = brnch_node[0]
            elif not_in == buffer_in:
                brnch_node = not_in
            else:
                breakpoint()

            src_sink_path = nx.shortest_path(G, src, sink)
            branch_sink_path = nx.shortest_path(G, brnch_node, sink)

            if buffer_in not in src_sink_path:
                g_buffer = "01"     #not_path belongs to Q_launch and route_thru is between brnc_node and not_in
            elif neigh in branch_sink_path:
                g_buffer = "10"     # not_path belongs to Q_launch
            else:
                g_buffer = "11"     #not_path belongs to route_thru
        else:
            g_buffer = "00"

        return g_buffer
    
    @staticmethod
    def get_subgraphs(G, g_buffer):
        buffer_in = next(filter(lambda node: cfg.LUT_in_pattern.match(node) and G.out_degree(node) != 0, G))
        not_in = next(filter(lambda node: cfg.LUT_in_pattern.match(node) and G.out_degree(node) == 0, G))
        neigh = next(G.neighbors(buffer_in))
        src = next(node for node in G if G.in_degree(node) == 0)
        sink = next(node for node in G if G.out_degree(node) == 0 and re.match(cfg.FF_in_pattern, node))

        G_net = nx.DiGraph()
        G_route_thru = nx.DiGraph()

        if g_buffer == "10":  # not_path belongs to Q_launch
            path1 = nx.shortest_path(G, src, buffer_in)
            path2 = nx.shortest_path(G, src, not_in)
            G_net.add_edges_from(zip(path1, path1[1:]))
            G_net.add_edges_from(zip(path2, path2[1:]))

            path3 = nx.shortest_path(G, neigh, sink)
            G_route_thru.add_edges_from(zip(path3, path3[1:]))

        elif g_buffer == "01":
            path1 = nx.shortest_path(G, src, sink)
            path2 = nx.shortest_path(G, src, buffer_in)
            G_net.add_edges_from(zip(path1, path1[1:]))
            G_net.add_edges_from(zip(path2, path2[1:]))

            path3 = nx.shortest_path(G, neigh, not_in)
            G_route_thru.add_edges_from(zip(path3, path3[1:]))

        elif g_buffer == "11":  # not_path belongs to route_thru
            path1 = nx.shortest_path(G, src, buffer_in)
            G_net.add_edges_from(zip(path1, path1[1:]))

            path2 = nx.shortest_path(G, neigh, sink)
            path3 = nx.shortest_path(G, neigh, not_in)
            G_route_thru.add_edges_from(zip(path2, path2[1:]))
            G_route_thru.add_edges_from(zip(path3, path3[1:]))
        else:
            G_net, G_route_thru = G, None


        return G_net, G_route_thru
        
        
