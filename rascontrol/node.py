from rascontrol.reach import Reach


class Node(object):
    """
    Holds information for RAS Node (XS, hydraulic structure, etc)
    """

    def __init__(self, node_id: str, node_type: str, code: int, reach: Reach) -> None:
        self.node_id = node_id  # Node name, string
        self.node_type = node_type  # node type: '' (XS), 'BR', 'Culv', 'IS', ... etc
        self.code = code  # Node code, int - these start at 1, not 0
        # The line below is how the code should really be gotten
        # self.code = self.rc.com_rc.Geometry_GetNode(self.river.code, self.reach.code, self.node_id)[0]
        self.reach = reach
        self.river = self.reach.river
        self.rc = self.river.rc  # RasController object

    def value(self, profile, value_type):
        """
        Returns HEC-RAS node output value (WSEL, MIN_CH_EL, etc) for profile

        :param profile: Profile object for desired profile
        :param value_type: desired output value, these are defined at the top of this file
        """
        # TODO - this should likely check if this is a bridge due to the 0 in output_nodeoutput
        return self.rc.output_nodeoutput(self.river.code, self.reach.code, self.code, profile.code, value_type)

    def __repr__(self):
        if self.node_type == '':
            node_type = 'XS'
        else:
            node_type = self.node_type
        return 'Node name ="' + self.node_id + '", Node type ="' + node_type + '", Node code = "' + str(self.code) + \
               '"'