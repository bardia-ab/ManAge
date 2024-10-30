import networkx as nx
from xil_res.node import Node as nd
from xil_res.path import Path
import utility.config as cfg

class CUT:
    __slots__ = ('origin', 'index', 'main_path', 'paths', 'FFs', 'subLUTs', 'G')
    def __init__(self, origin=None, cut_index=None):
        self.origin     = origin
        self.index      = cut_index
        self.main_path  = Path()
        self.paths      = []
        self.FFs        = set()
        self.subLUTs    = set()
        self.G          = nx.DiGraph()

    def __repr__(self):
        return f'CUT{self.index}'

    def __eq__(self, other):
        return type(self) == type(other) and self.origin == other.origin and self.index == other.index and self.G == other.G

    def __hash__(self):
        return hash((self.origin, self.index))

    def get_x_coord(self) -> int:
        """This function returns the X coordinate of the CUT's origin

        :return: X coordinate
        :rtype: int
        """
        return nd.get_x_coord(self.origin)

    def get_y_coord(self) -> int:
        """This function returns the Y coordinate of the CUT's origin

        :return: Y coordinate
        :rtype: int
        """
        return nd.get_y_coord(self.origin)

    def add_path(self, path):
        """This function adds the specified path to the list of the CUT's path and graph(G)

        :param path: The path which must be added to the CUT
        :type path: Path
        """
        self.paths.append(path)
        self.G.add_edges_from(path.get_edges())

    def get_covered_pips(self):
        """This function extracts the PIPs in the main path of the CUT

        :return: A set of PIPs
        :rtype: Set[Tuple[str]]
        """
        tile = f'{cfg.INT_label}_{self.origin}'
        return set(filter(lambda edge: nd.get_tile(edge[0]) == tile, self.main_path.get_pips()))

    def create_CUT_G_from_paths(self, *paths):
        """This function populates the CUT's graph with a collection of specified paths
        """
        for path in paths:
            edges = zip(path, path[1:])
            self.G.add_edges_from(edges)

    def create_CUT_G_from_edges(self, *edges):
        """This function populates the CUT's graph with a collection of specified edges
        """
        self.G.add_edges_from(edges)

    def create_CUT_subLUTs(self, TC):
        """This function creates subLUTs from the the CUT's grpah and adds them to the associated configuration's LUTs

        :param TC: Minimal test configuration or Configuration
        :type TC: MinConfig|Config
        """
        for LUT_in in filter(lambda x: nd.get_primitive(x) == 'LUT', self.G):
            LUT_in_type = 'end_node' if self.G.out_degree(LUT_in) == 0 else 'mid_node'
            LUT_output = None if LUT_in_type == 'end_node' else next(self.G.neighbors(LUT_in))
            LUT_func = 'buffer' if LUT_in_type == 'mid_node' else 'not'

            sublut_name = f'{nd.get_tile(LUT_in)}/{nd.get_label(LUT_in)}{TC.get_subLUT_bel(LUT_output, LUT_in)}'
            subLUT = TC.subLUTs[sublut_name]
            subLUT.fill(LUT_output, LUT_func, LUT_in)
            subLUT.add_to_LUT(TC)
            self.subLUTs.add(subLUT)

    def create_CUT_FFs(self, TC):
        """This function creates FFs from the the CUT's grpah

        :param TC: Minimal test configuration or Configuration
        :type TC: MinConfig|Config
        """
        for ff_node in (node for node in self.G if nd.get_primitive(node) == 'FF'):
            FF_primitive = TC.FFs[nd.get_bel(ff_node)]
            FF_primitive.set_usage(ff_node)
            self.FFs.add(FF_primitive)

    def set_main_path(self):
        """This function finds the main path of the CUT and assigns it to the main_path attribute of the class
        """
        try:
            src = next(node for node in self.G if cfg.Source_pattern.match(node))
            sink = next(node for node in self.G if cfg.Sink_pattern.match(node))
        except StopIteration:
            self.main_path = Path()
            return

        self.main_path = Path()
        self.main_path.nodes = nx.shortest_path(self.G, src, sink)

    def get_DLOC_G(self, tiles_map, target_origin):
        """This function relocates the CUT's graph to the specified target origin

        :param tiles_map: Tile map of the device under test
        :type tiles_map: dict
        :param target_origin: Target origin the graph must be relocated to
        :type target_origin: str
        :return: Relocated graph
        :rtype: nx.DiGraph
        """
        DLOC_G = nx.DiGraph()
        for edge in self.G.edges:
            DLOC_edge = tuple(map(lambda node: nd.dislocate_node(tiles_map, node, target_origin, origin=self.origin), edge))
            DLOC_G.add_edge(*DLOC_edge)

        return DLOC_G

    @staticmethod
    def conv_paths2CUT(TC, index, origin, *paths):
        """This function creates a CUT from the specified paths

        :param TC: Minimal test configuration or Configuration
        :type TC: MinConfig|Config
        :param index: Index of the CUT
        :type index: int
        :param origin: Origin of the CUT
        :type origin: str
        :return: Created CUT
        :rtype: CUT
        """
        cut = CUT(cut_index=index, origin=origin)

        # create graph
        cut.create_CUT_G_from_paths(*paths)

        # create FFs
        cut.create_CUT_FFs(TC)

        # create subLUTs
        cut.create_CUT_subLUTs(TC)

        return cut

    @staticmethod
    def conv_graph2CUT(TC, index, origin, *edges):
        """This function creates a CUT from the specified edges

        :param TC: Minimal test configuration or Configuration
        :type TC: MinConfig|Config
        :param index: Index of the CUT
        :type index: int
        :param origin: Origin of the CUT
        :type origin: str
        :return: Created CUT
        :rtype: CUT
        """
        cut = CUT(cut_index=index, origin=origin)

        # create graph
        cut.create_CUT_G_from_edges(*edges)

        # create FFs
        cut.create_CUT_FFs(TC)

        # create subLUTs
        cut.create_CUT_subLUTs(TC)

        return cut
