import re
import networkx as nx
from xil_res.cut import CUT
from xil_res.node import Node as nd
from xil_res.primitive import FF, SubLUT
from xil_res.path import Path
import utility.config as cfg

class D_CUT(CUT):
    __slots__ = ('origin', 'index', 'main_path', 'paths', 'FFs', 'subLUTs', 'G', 'nodes_dict')
    def __init__(self, origin: str, tiles_map, cut: CUT, iteration=None, index=None):
        index = (iteration - 1) * cfg.max_capacity + cut.index if (iteration is not None) else index
        super().__init__(origin, index)
        del self.paths
        self.nodes_dict = self.get_nodes_dict(tiles_map, cut)
        self.FFs        = self.get_relocated_FFs(tiles_map, cut)
        self.subLUTs    = self.get_relocated_subLUTs(tiles_map, cut)
        self.set_graph(cut)
        self.set_main_path()

    def __repr__(self):
        return f'D_CUT(index={self.index}, origin={self.origin})'

    def get_x_coord(self):
        return nd.get_x_coord(self.origin)

    def get_y_coord(self):
        return nd.get_y_coord(self.origin)

    def get_nodes_dict(self, tiles_map, cut):
        tiles_map = tiles_map
        nodes_dict = {node: nd.dislocate_node(tiles_map, node, self.origin, origin=cut.origin) for node in cut.G}
        if None in nodes_dict.values():
            print(nodes_dict)
            raise ValueError(f'{next(k for k,v in nodes_dict.items() if v is None)}: invalid node in D_CUT!')

        return nodes_dict

    def get_relocated_FFs(self, tiles_map, cut):
        #TC = rloc_collection.TC
        tiles_map = tiles_map
        FFs = set()
        for FF_primitive in cut.FFs:
            FF_node = FF_primitive.node
            D_FF_node = self.nodes_dict[FF_node]
            D_FF_primitive = FF(nd.get_bel(D_FF_node))
            D_FF_primitive.global_set(tiles_map, FF_primitive)
            FFs.add(D_FF_primitive)

        return FFs

    def get_relocated_subLUTs(self, tiles_map, cut):
        #TC = rloc_collection.TC
        tiles_map = tiles_map
        subLUTs = set()
        for subLUT in cut.subLUTs:
            D_LUT_input = next(self.nodes_dict[LUT_input] for LUT_input in subLUT.inputs if LUT_input in self.nodes_dict)
            subLUT_name = f'{nd.get_tile(D_LUT_input)}/{subLUT.port}'
            D_subLUT = SubLUT(subLUT_name)
            D_subLUT.global_set(tiles_map, subLUT)
            subLUTs.add(D_subLUT)

        return subLUTs

    def set_graph(self, cut):
        edges = map(lambda e: (self.nodes_dict[e[0]], self.nodes_dict[e[1]]), cut.G.edges)
        self.G.add_edges_from(edges)

    def set_main_path(self):
        try:
            src = next(node for node in self.G if cfg.Source_pattern.match(node))
            sink = next(node for node in self.G if cfg.Sink_pattern.match(node))
        except StopIteration:
            self.main_path = Path()
            return

        self.main_path = Path()
        self.main_path. nodes = nx.shortest_path(self.G, src, sink)

    def get_g_buffer(self):
        if list(filter(lambda x: re.match(cfg.MUXED_CLB_out_pattern, x), self.G)):
            g_buffer = "00"

        elif any(map(lambda x: x.func == 'buffer', self.subLUTs)):
            route_thru_subLUT = next(subLUT for subLUT in self.subLUTs if subLUT.func == 'buffer')
            not_subLUT = next(subLUT for subLUT in self.subLUTs if subLUT.func == 'not')
            buffer_in = next(route_thru_subLUT.inputs)
            not_in = next(not_subLUT.inputs)
            neigh = next(self.G.neighbors(buffer_in))
            src = next(node for node in self.G if self.G.in_degree(node) == 0)
            sink = next(node for node in self.G if self.G.out_degree(node) == 0 and re.match(cfg.FF_in_pattern, node))
            brnch_node = [node for node in self.G if self.G.out_degree(node) > 1]
            if brnch_node:
                brnch_node = brnch_node[0]
            elif not_in == buffer_in:
                brnch_node = not_in
            else:
                breakpoint()

            src_sink_path = nx.shortest_path(self.G, src, sink)
            branch_sink_path = nx.shortest_path(self.G, brnch_node, sink)

            if buffer_in not in src_sink_path:
                g_buffer = "01"     #not_path belongs to Q_launch and route_thru is between brnc_node and not_in
            elif neigh in branch_sink_path:
                g_buffer = "10"     # not_path belongs to Q_launch
            else:
                g_buffer = "11"     #not_path belongs to route_thru
        else:
            g_buffer = "00"

        return g_buffer
