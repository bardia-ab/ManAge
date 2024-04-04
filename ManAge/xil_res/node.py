import re, sys, os
from typing import Set
#sys.path.insert(0, r'..\utility')
import networkx as nx
import utility.config as cfg

class Node:

    ######### Tile Methods ##########
    @staticmethod
    def get_tile(node: str, delimiter='/') -> str:
        return node.split(delimiter)[0]

    @staticmethod
    def get_tile_type(node: str, exact=False) -> str:
        if exact:
            end_idx = re.search('_X-*\d+Y-*\d+', node).regs[0][0]
            tile_type = Node.get_tile(node)[: end_idx]
        elif node.startswith('INT'):
            tile_type = 'INT'
        elif node.startswith('CLE'):
            tile_type = 'CLB'
        else:
            tile_type = None

        return tile_type

    @staticmethod
    def get_site_type(node: str) -> str | None:
        if Node.get_tile_type(node) == 'INT':
            return None
        elif Node.get_tile_type(node) == 'CLB':
            if node.startswith('CLEM'):
                return 'M'
            else:
                return 'L'
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_direction(node: str) -> str:
        if Node.get_tile_type(node) == 'INT':
            direction = 'C'
        elif Node.get_tile_type(node) == 'CLB':
            if re.match(cfg.East_CLB, node):
                direction = 'E'
            else:
                direction = 'W'
        else:
            raise ValueError(f'Node: {node} is Invaild!')


        return direction

    @staticmethod
    def get_top_bottom(node: str) -> str | None:
        if Node.get_label(node) in {'A', 'B', 'C', 'D'}:
            top_bottom = 'B'
        elif Node.get_label(node) in {'E', 'F', 'G', 'H'}:
            top_bottom = 'T'
        else:
            top_bottom = None

        return top_bottom

    @staticmethod
    def get_clock_group(node: str) -> str | None:
        if Node.get_clb_node_type(node):
            return f'{Node.get_direction(node)}_{Node.get_top_bottom(node)}'
        else:
            return None

    @staticmethod
    def get_coordinate(node: str) -> str:
        return re.findall('X-*\d+Y-*\d+', node)[0]

    @staticmethod
    def get_x_coord(node: str) -> int:
        return int(re.findall('-*\d+', Node.get_coordinate(node))[0])

    @staticmethod
    def get_y_coord(node: str) -> int:
        return int(re.findall('-*\d+', Node.get_coordinate(node))[1])

    ######### Port Methods ##########
    @staticmethod
    def get_port(node: str, delimiter='/') -> str:
        return node.split(delimiter)[1]

    @staticmethod
    def get_label(node: str) -> str | None:
        if Node.get_tile_type(node) == 'INT':
            return None
        elif Node.get_tile_type(node) == 'CLB':
            return node.split('_SITE_0_')[-1][0]
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_port_suffix(node: str) -> str | None:
        if Node.get_tile_type(node) == 'INT':
            return None
        elif Node.get_tile_type(node) == 'CLB':
            return node.split('_SITE_0_')[-1]
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_port_prefix(node: str) -> str | None:
        if Node.get_tile_type(node) == 'INT':
            return None
        elif Node.get_tile_type(node) == 'CLB':
            return f'CLE_CLE_{Node.get_site_type(node)}_SITE_0'
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_clb_node_type(node: str) -> str | None:
        if re.match(cfg.LUT_in_pattern, node):
            return 'LUT_in'
        elif re.match(cfg.FF_in_pattern, node):
            return 'FF_in'
        elif re.match(cfg.FF_out_pattern, node):
            return 'FF_out'
        elif re.match(cfg.CLB_out_pattern, node):
            return 'CLB_out'
        elif re.match(cfg.MUXED_CLB_out_pattern, node):
            return 'CLB_muxed'
        else:
            return None

    @staticmethod
    def get_primitive(node: str) -> str | None:
        if Node.get_tile_type(node) == 'INT':
            return None
        elif Node.get_clb_node_type(node) == 'LUT_in':
            return 'LUT'
        elif Node.get_clb_node_type(node) in {'FF_out', 'FF_in'}:
            return 'FF'
        else:
            return None

    @staticmethod
    def get_bel(node: str) -> str | None:
        if re.match(cfg.LUT_in_pattern, node) or re.match(cfg.Unregistered_CLB_out_pattern, node):
            key = Node.get_tile(node) + '/' + Node.get_label(node) + 'LUT'

        elif re.match(cfg.FF_in_pattern, node):
            suffix = ['', '2']
            key = Node.get_tile(node) + '/' + Node.get_label(node) + 'FF' + suffix[Node.get_bel_index(node) - 1]

        elif re.match(cfg.FF_out_pattern, node):
            suffix = ['', '2']
            key = Node.get_tile(node) + '/' + Node.get_label(node) + 'FF' + suffix[Node.get_bel_index(node) - 1]

        else:
            key = None

        return key

    @staticmethod
    def get_bel_index(node: str) -> int:
        if Node.get_clb_node_type(node) in ['FF_in', 'FF_out']:
            if node[-1] in ['I', '2']:
                return 2

            if node[-1] in ['X', 'Q']:
                return 1

        if Node.get_clb_node_type(node) == 'LUT_in':
            return int(node[-1])

    @staticmethod
    def is_i6(node: str) -> bool:
        return bool(re.match(cfg.LUT_in6_pattern, node))

    @staticmethod
    def get_INT_node_mode(G: nx.DiGraph, node: str) -> str:
        # Modes: 1- in 2- out 3- mid
        pred_tiles = {Node.get_tile(pred) for pred in G.predecessors(node)}
        neigh_tiles = {Node.get_tile(neigh) for neigh in G.neighbors(node)}
        if pred_tiles == neigh_tiles:
            mode = 'mid'
        elif Node.get_tile(node) not in pred_tiles and (neigh_tiles == {Node.get_tile(node)} or neigh_tiles == set()):
            mode = 'in'
        else:
            mode = 'out'

        return mode


    ######### CLB Nodes ################
    @staticmethod
    def get_LUT_input(tile: str, label: str, index: int) -> str:
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}{index}'

    @staticmethod
    def get_MUXED_CLB_out(tile: str, label: str) -> str:
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}MUX'

    @staticmethod
    def get_CLB_out(tile: str, label: str) -> str:
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}_O'

    @staticmethod
    def get_FF_input(tile: str, label: str, index: int) -> str:
        suffix = 'X' if index == 1 else '_I'
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}{suffix}'

    @staticmethod
    def get_FF_output(tile: str, label: str, index: int) -> str:
        suffix = 'Q' if index == 1 else 'Q2'
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}{suffix}'

    @staticmethod
    def get_group_mates(node: str) -> Set:
        group_mates = set()
        tile = Node.get_tile(node)
        clb_node_type = Node.get_clb_node_type(node)
        top_bottom = Node.get_top_bottom(node)
        label_index = range(65, 69) if top_bottom == 'B' else range(69, 73)
        labels = {chr(idx) for idx in label_index}
        index = Node.get_bel_index(node)
        if clb_node_type == 'LUT_in':
            group_mates = {Node.get_LUT_input(tile, label, index) for label in labels}
        elif clb_node_type == 'FF_in':
            group_mates = {Node.get_FF_input(tile, label, index) for label in labels}
        elif clb_node_type == 'FF_out':
            group_mates = {Node.get_FF_output(tile, label, index) for label in labels}
        elif clb_node_type == 'CLB_out':
            group_mates = {Node.get_CLB_out(tile, label) for label in labels}
        elif clb_node_type == 'CLB_muxed':
            group_mates = {Node.get_MUXED_CLB_out(tile, label) for label in labels}

        return group_mates

    @staticmethod
    def get_global_group_mates(G: nx.DiGraph, clb_node: str, clock_group: str):
        return (node for node in G if Node.get_clock_group(node) == clock_group and
                Node.get_clb_node_type(node) == Node.get_clb_node_type(clb_node))


    @staticmethod
    def get_global_pattern(node: str) -> str:
        if Node.get_tile_type(node) == 'INT':
            pattern = f'INT_X.*{Node.get_port(node)}'
        else:
            tile = cfg.East_CLB.pattern if Node.get_direction(node) == 'E' else cfg.West_CLB.pattern
            port_suffix = Node.get_port_suffix(node)
            pattern = f'{tile}{port_suffix}'

        return pattern

    ####################### RLOC Node ###########################
    @staticmethod
    def get_RLOC_coord(tile, origin):
        rx = Node.get_x_coord(tile) - Node.get_x_coord(origin)
        ry = Node.get_y_coord(tile) - Node.get_y_coord(origin)
        RLOC_coord = f'X{rx}Y{ry}'

        return RLOC_coord

    @staticmethod
    def get_DLOC_coord(tile: str, D_coord: str):
        dx = Node.get_x_coord(tile) + Node.get_x_coord(D_coord)
        dy = Node.get_y_coord(tile) + Node.get_y_coord(D_coord)
        DLOC_coord = f'X{dx}Y{dy}'

        return DLOC_coord

    @staticmethod
    def get_RLOC_node(node: str, origin: str) -> str:
        if Node.get_tile_type(node) == 'INT':
            tile = f'INT_{Node.get_RLOC_coord(Node.get_tile(node), origin)}'
            port = Node.get_port(node)
        else:
            tile = f'CLB_{Node.get_direction(node)}_{Node.get_RLOC_coord(Node.get_tile(node), origin)}'
            port = Node.get_port_suffix(node)

        return f'{tile}/{port}'

    @staticmethod
    def get_DLOC_node(tiles_map, RLOC_node: str, D_origin: str) -> str|None:
        tile = Node.get_tile(RLOC_node)
        D_coord = Node.get_DLOC_coord(tile, D_origin)
        if D_coord not in tiles_map:
            return None

        if Node.get_tile_type(RLOC_node) == 'INT':
            tile = f'INT_{D_coord}'
            port = Node.get_port(RLOC_node)
        else:
            direction = RLOC_node.split('_')[1]
            tile = tiles_map[D_coord][f'CLB_{direction}']
            if tile is None:
                return None

            port = f'CLE_CLE_{Node.get_site_type(tile)}_SITE_0_{Node.get_port(RLOC_node)}'

        return f'{tile}/{port}'

    @staticmethod
    def dislocate_node(tiles_map, node: str|None, D_origin: str, origin=None):
        if node is None:
            return node

        if origin is None:
            origin = Node.get_coordinate(node)

        RLOC_node = Node.get_RLOC_node(node, origin)
        return Node.get_DLOC_node(tiles_map, RLOC_node, D_origin)


if __name__ == '__main__':
    nodes = ['CLEM_X46Y90/CLE_CLE_M_SITE_0_A2', 'CLEM_X46Y90/CLE_CLE_M_SITE_0_AX', 'CLEM_X46Y90/CLE_CLE_M_SITE_0_AQ2', 'CLEM_X46Y90/CLE_CLE_M_SITE_0_AMUX', 'CLEM_X46Y90/CLE_CLE_M_SITE_0_A_O']
    for node in nodes:
        print(Node.get_group_mates(node))
