import copy
from xil_res.cut import CUT
from xil_res.node import Node as nd
from xil_res.primitive import FF, SubLUT
import scripts.config as cfg
class D_CUT(CUT):
    __slots__ = ('origin', 'index', 'main_path', 'paths', 'FFs', 'subLUTs', 'G', 'nodes_dict')
    def __init__(self, rloc_collection, cut: CUT, origin: str):
        index = rloc_collection.iteration * cfg.max_capacity + cut.index
        super().__init__(origin, index)
        del self.main_path
        del self.paths
        self.nodes_dict = self.get_nodes_dict(rloc_collection, cut)
        self.FFs        = self.get_relocated_FFs(rloc_collection, cut)
        self.subLUTs    = self.get_relocated_subLUTs(rloc_collection, cut)
        self.set_graph(cut)

    def __repr__(self):
        return f'D_CUT(index={self.index}, origin={self.origin})'

    def get_x_coord(self):
        return nd.get_x_coord(self.origin)

    def get_y_coord(self):
        return nd.get_y_coord(self.origin)

    def get_nodes_dict(self, rloc_collection, cut):
        tiles_map = rloc_collection.device.tiles_map
        nodes_dict = {node: nd.dislocate_node(tiles_map, node, self.origin, origin=cut.origin) for node in cut.G}
        if None in nodes_dict.values():
            raise ValueError(f'{next(k for k,v in nodes_dict.items() if v is None)}: invalid node in D_CUT!')

        return nodes_dict

    def get_relocated_FFs(self, rloc_collection, cut):
        TC = rloc_collection.TC
        tiles_map = rloc_collection.device.tiles_map
        FFs = set()
        for FF_primitive in cut.FFs:
            FF_node = FF_primitive.node
            D_FF_node = self.nodes_dict[FF_node]
            D_FF_primitive = FF(nd.get_bel(D_FF_node))
            D_FF_primitive.global_set(tiles_map, FF_primitive)
            FFs.add(D_FF_primitive)

        return FFs

    def get_relocated_subLUTs(self, rloc_collection, cut):
        TC = rloc_collection.TC
        tiles_map = rloc_collection.device.tiles_map
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
