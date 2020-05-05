from typing import List

from rascontrol.node import Node
from rascontrol.river import River


class Reach(object):
    def __init__(self,
                 name: str,
                 code: int,
                 river: River) -> None:
        self.name = name  # Reach name, string
        self.code = code  # Reach code, int - these start at 1, not 0
        self.river = river  # parent River object
        self.rc = self.river.rc   # RasController object
        self.nodes = self._get_nodes()  # list of Reach objects

    # TODO -  the reach code should probably be pullled from the rascontller, although i+1 seems to work
    def _get_nodes(self) -> List[Node]:
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        reach_id = self.code
        river_id = self.river.code
        nodes = []
        node_ids, node_types = self.rc.geometry_getnodes(river_id, reach_id)
        for i, node_stuff in enumerate(zip(node_ids, node_types)):
            node_id, node_type = node_stuff
            new_node = Node(node_id, node_type, i+1, self)
            nodes.append(new_node)
        return nodes

    def __repr__(self):
        return 'Reach name = "'+self.name + '", Reach code = "' + str(self.code)+'"'
