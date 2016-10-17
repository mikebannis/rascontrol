import win32com.client
import psutil
import sys

# Codes for RAS output types
WSEL = 2
MIN_CH_EL = 5

class Profile(object):
    def __init__(self, name, code, rc):
        self.name = name  # Profile name, string
        self.code = code  # Profile code, int - these start at 1, not 0
        self.rc = rc   # RasController object

    def __repr__(self):
        return self.name + '/' +str(self.code)


class River(object):
    def __init__(self, name, code, rc):
        self.name = name  # River name, string
        self.code = code  # River code, int - these start at 1, not 0
        self.rc = rc   # RasController object
        self.reaches = self._get_reaches()  # list of Reach objects

    def _get_reaches(self):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        reaches = []
        reach_names = self.rc.output_getreaches(self.code)
        for i, name in enumerate(reach_names):
            new_reach = Reach(name, i+1, self)
            reaches.append(new_reach)
        return reaches

    def __repr__(self):
        return 'River name = "'+self.name + '", River code = "' + str(self.code)+'"'


class Reach(object):
    def __init__(self, name, code, river):
        self.name = name  # Reach name, string
        self.code = code  # Reach code, int - these start at 1, not 0
        self.river = river  # parent River object
        self.rc = self.river.rc   # RasController object
        self.nodes = self._get_nodes()  # list of Reach objects

    def _get_nodes(self):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        reach_id = self.code
        river_id = self.river.code
        nodes = []
        node_ids, node_types = self.rc.output_getnodes(river_id, reach_id)
        for i, node_stuff in enumerate(zip(node_ids, node_types)):
            node_id, node_type = node_stuff
            new_node = Node(node_id, node_type, i+1, self)
            nodes.append(new_node)
        return nodes

    def __repr__(self):
        return 'Reach name = "'+self.name + '", Reach code = "' + str(self.code)+'"'


class Node(object):
    def __init__(self, node_id, node_type, code, reach):
        self.node_id = node_id  # Node name, string
        self.node_type = node_type  # node type: '' (XS), 'BR', 'Culv', 'IS', ... etc
        self.code = code  # Node code, int - these start at 1, not 0
        self.reach = reach
        self.river = self.reach.river
        self.rc = self.river.rc   # RasController object
        self.special_code = self.rc.com_rc.Geometry_GetNode(self.river.code, self.reach.code, self.node_id)[0]

    def value(self, value_type):
        # TODO - this should likely check if this is a bridge due to the 0 in output_nodeoutput
        return self.rc.output_nodeoutput(self.river.code, self.reach.code, self.code, value_type)

    def __repr__(self):
        return self.node_id + '/' + self.node_type + '/' + str(self.code)


class RasController(object):
    def __init__(self):
        # See if RAS is open and abort if so
        if not True:
            for p in psutil.process_iter():
                try:
                    if p.name() == 'ras.exe':
                        sys.exit('HEC-RAS appears to be open. Please close HEC-RAS. Exiting.')
                except psutil.Error:
                    pass
        # RAS is not open yet, open it
        self.com_rc = win32com.client.DispatchEx('RAS41.HECRASController')
        # self.com_rc = win32com.client.DispatchEx('RAS500.HECRASController')

    def get_profiles(self):
        """
        Returns list of all profiles as Profile objects
        :return: list of Profile objects
        """
        profile_names = self._output_getprofiles()
        profiles = []
        for i, name in enumerate(profile_names):
            new_prof = Profile(name, i+1, self)
            profiles.append(new_prof)
        return profiles

    def get_rivers(self):
        """
        Returns list of all rivers as River objects
        :return: list of River objects
        """
        river_names = self._output_getrivers()
        rivers = []
        for i, name in enumerate(river_names):
            new_prof = River(name, i+1, self)
            rivers.append(new_prof)
        return rivers

    # TODO - remove once obsolete
    def _current_plan_file(self):
        """
        Returns path and file name of current plan file
        :return: string
        """
        return self.com_rc.CurrentPlanFile()

    def open_project(self, project):
        """
        Opens project in RAS
        :param project: string - full path to RAS project file (*.prj)
        """
        self.com_rc.Project_Open(project)

    def _plan_names(self, basedir=True):
        """
        returns list of plan names
        :param basedir: ???? unknown
        :return: list of strings
        """
        _, names, _ = self.com_rc.Plan_Names(None, None, basedir)
        return names

    def output_getnodes(self, river_id, reach_id):
        """
        Return node names (stationing) and node types
        Node types may belong to the following non inclusive list: '' (cross section), 'BR', 'Culv', 'IS', ...
        :return: nodes_ids, node_types - two lists of strings
        """
        _, _, _, node_ids, node_types = self.com_rc.Geometry_GetNodes(river_id, reach_id, None, None, None)
        return node_ids, node_types

    def output_getreaches(self, river_num):
        """
        Returns reach names in river numbered river_num
        :param river_num: int
        :return: list of reach names
        """
        _, _, reaches = self.com_rc.Output_GetReaches(river_num, None, None)
        return reaches

    def output_nodeoutput(self, river_id, reach_id, node_id, value_type):
        profile_id = 1 # TODO - fix this
        # TODO - the 0 in the next line should be a lot smarter
        value = self.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, profile_id, value_type)[0]
        return value

    def run_current_plan(self):
        """
        Run current plan in RAS
        :return: status, messages - ??, ??
        """
        status, _, messages = self.com_rc.Compute_CurrentPlan(None, None)
        return status, messages

    def set_plan(self, plan):
        self.com_rc.Plan_SetCurrent(plan)

    def show(self):
        """
        Makes RAS window visible
        """
        self.com_rc.ShowRas()

    def _output_getprofiles(self):
        """
        Returns names of profiles in current project
        :return: list of strings
        """
        _, profiles = self.com_rc.Output_GetProfiles(0, None)
        return profiles

    def _output_getrivers(self):
        """
        Returns list of names of rivers in current project
        :return: list of strings
        """
        _, rivers = self.com_rc.Output_GetRivers(0, None)
        return rivers

    def _nodes(self, river_id, reach_id):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        node_ids, node_types = self.output_getnodes(river_id, reach_id)
        return node_ids, node_types


def main():
    rc = RasController()
    rc.open_project('x:/python/rascontroller/ras_model/HG.prj')
    print rc._current_plan_file()
    print rc._plan_names()
    #rc.show()
    #print rc.run_current_plan()
    print 'done'
    # print rc.run_current_plan()
    river_id = 2
    reach_id = 1
    profile_id = 1
    node_ids, node_types = rc._nodes(river_id, reach_id)
    # print node_ids, node_types
    if not True:
        for x, y in zip(node_ids, node_types):
            # Get numeric node code
            temp = rc.com_rc.Geometry_GetNode(river_id, reach_id, x)
            print temp
            node_id = temp[0]
            # 0 below is for BR up/down, 2 is code for wsel
            wsel1 = rc.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, profile_id, 2)[0]
            #wsel2 = rc.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, 2, 2)[0]
            print x,'/', y,'/', node_id,'/', wsel1
            #kkprint x,'/', y,'/', node_id,'/', wsel1, wsel2, wsel1-wsel2
            #sys.exit()


    profs = rc.get_profiles()
    print profs

    rivers = rc.get_rivers()
    for riv in rivers:
        for reach in riv.reaches:
            print riv
            print reach
            for node in reach.nodes:
                #print node, 'special=', node.special_code
                print node, node.value(WSEL), node.value(MIN_CH_EL)

if __name__ == '__main__':
    main()
