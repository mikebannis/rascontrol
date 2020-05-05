"""
rascontroller.py

Provides API to control HEC-RAS through the win32com interface. Primary object is RasController.

Mike Bannister 2018
"""
from pathlib import Path
from typing import Tuple, Union

import win32com.client
import psutil
import sys
import os
import time
from collections import namedtuple

from rascontrol.exceptions.rascontroller import RASOpenError, NoProjectError, RCException, CrossSectionNotFoundError, \
    CulvertNotFoundError, BridgeNotFoundError, MultipleOpeningNotFoundError, InlineStructureNotFoundError, \
    LateralStructureNotFoundError, LockedPlanError
from rascontrol.node import Node
from rascontrol.plan import Plan

SimpleXS = namedtuple('SimpleXS', ['xs_id', 'river', 'reach'])
SimpleCulvert = namedtuple('SimpleCulvert', ['culvert_id', 'river', 'reach'])
SimpleBridge = namedtuple('SimpleBridge', ['bridge_id', 'river', 'reach'])
SimpleMO = namedtuple('SimpleMO', ['mo_id', 'river', 'reach'])
SimpleIS = namedtuple('SimpleIS', ['is_id', 'river', 'reach'])
SimpleLS = namedtuple('SimpleLS', ['ls_id', 'river', 'reach'])

# Codes for RAS output types, used in Node.value()
WSEL = 2
MIN_CH_EL = 5
STA_WS_LFT = 36
STA_WS_RGT = 37
FROUDE_CHL = 48  # Froude number for channel
FROUDE_XS = 49  # Froude number for entire XS
Q_WEIR = 94
Q_CULVERT_GROUP = 73
Q_CULVERT_TOT = 242 
WSUS = 75
WSDS = 213

# Stations for below codes should probably be pulled from geometry, not from the RAS controller
RIGHT_STA = 264  # right station of a XS
LEFT_STA = 263  # left station of a XS
CH_STA_L = 158  # left station of channel
CH_STA_R = 159  # right station of channel

DEBUG = False


class RasController(object):
    """
    Opens, runs, and retrieves information from HEC-RAS. Checks if RAS is open during __init__(). If open, raises 
    RASOpen.

    Primary methods -
        open_project(self, project): Opens project in RAS
           :param project: string - full path to RAS project file (*.prj)

        get_xs(self, xs_id, river = None, reach = None): return cross section Node object
        
        get_culvert(self, culv_id, river = None, reach = None): return culvert Node object


    Other methods -
        close(self): Closes RAS, only works in RAS 5.x.y

        get_current_plan(self): Returns current plan as Plan object

        get_plans(self, basedir = None): Returns plans in current project as list of Plan objects

        get_profiles(self): Returns list of all profiles as Profile objects

        get_rivers(self): Returns list of all rivers as River objects
        
        simple_xs_list(self): returns list of SimpleXS objects
         
        simple_culvert_list(self): returns list of SimpleCulvert objects
 
        is_output_current(self, plan, show=False): Returns True if output is up to date for plan (Plan object)

        run_current_plan(self): Runs current plan in RAS

        set_plan(self, plan): Sets plan in RAS, plan is Plan object from get_plans()
            :param plan: Plan object

        show(self): Makes RAS window visible
    """

    def __init__(self, version: str = '506') -> None:
        """
        version selects the RAS version, options include
            '41' - 4.1
            '501' - 5.0.1
            '503' - 5.0.3
            '505' - 5.0.5
            '506' - 5.0.6
        """
        self.version = version
        
        self.xs_list = None
        self.culvert_list = None
        self.bridge_list = None
        self.mult_open_list = None
        self.inline_struct_list = None
        self.lateral_struct_list = None
        
        self.project_is_open = False  # has a project been opened? set by self.open_project()

        # See if RAS is open and abort if so
        if True:
            for p in psutil.process_iter():
                try:
                    if p.name() == 'ras.exe':
                    # TODO: As of 4/1/2019, the line above should be the line below. 'ras.exe' is not currently working,
                    # So this test completely fails.
                    #if p.name() == 'ras.exe' or p.name() == 'Ras.exe':
                        raise RASOpenError('HEC-RAS appears to be open. Please close HEC-RAS. Exiting.')
                except psutil.Error:
                    # TODO: This should be handled better. 
                    pass

        # RAS is not open yet, open it
        self.com_rc = win32com.client.DispatchEx('RAS' + version + '.HECRASController')
        self._plan_lock = False  # get_profiles() seems to lock the current plan in place. Not sure why
        
        # flag to determine if the model has been run
        self. _model_ran = False

    # todo make it a property?
    def simple_xs_list(self) -> Tuple[SimpleXS]:
        """
        Returns list of XS as SimpleXS objects
        This is primarily for interacting with parserasgeo
        
        :return: list of XS as SimpleXS objects, all names are strip()ed
        """
        simple_list = self._simple_node_list('xs')
        return simple_list

    def get_xs(self, xs_id: str, river: str = None, reach: str = None) -> Node:
        """
        Returns requested cross section, ignores river and reach if not specified
        Raises CrossSectionNotFound if cross section is not in model
        
        :param xs_id: id of cross section node (cast to string automatically)
        :param river: river name (string)
        :param reach: reach name (string)
        :return: Node object for given cross section id
        """
        node = self._get_node('xs', xs_id, river, reach)
        return node

    def simple_culvert_list(self) -> Tuple[SimpleCulvert]:  # todo change to Union of Simple objects
        """
        Returns list of culverts as SimpleCulvert objects
        This is primarily for interacting with parserasgeo
        
        :return: list of culverts as SimpleCulvert objects, all names are strip()ed
        """
        simple_list = self._simple_node_list('culvert')
        return simple_list 

    def get_culvert(self, culvert_id: str, river: str = None, reach: str = None) -> Node:
        """
        Returns requested culvert, ignores river and reach if not specified
        Raises CulvertNotFound if culvert is not in model
        
        :param culvert_id: id of station (cast to string automatically)
        :param river: river name (string)
        :param reach: reach name (string)
        :return: Node object for given culvert id
        """
        node = self._get_node('culvert', culvert_id, river, reach)
        return node        
    
    # - - - - - - - - - - - - -
    # semi-private methods for get_<node> and simple_<node>_list
    # - - - - - - - - - - - - -

    def _simple_node_list(
            self, node_type: str) -> Tuple[Union[SimpleXS, SimpleCulvert, SimpleBridge, SimpleMO, SimpleIS, SimpleLS]]:
        """
        Returns list of station as Simple<node> objects
        <node> can be a cross section, bridge, culvert, multiple opening, inline structure, or lateral structure
        all names are strip()ed

        This is primarily for interacting with parserasgeo
        
        :param node_type: the type of node whose list should be pulled. Possible options are 'xs', 'culvert', 'bridge', 'mult_open', 'inline_struct', and 'lateral_struct'
        :return: a list of all Simple<node>s of node_type in the model (i.e. SimpleXS, SimpleCulvert, SimpleBridge, SimpleMO, SimpleIS, SimpleLS)
        """
        if not self.project_is_open:
            raise NoProjectError('Project must be opened before calling RasController._simple_node_list()')

        # populate self.node_list if it is None
        # use self.node_list to create the simple_list
        simple_list = []
        if node_type == 'xs':
            if self.xs_list is None:
                self.xs_list = self._load_node_list(node_type)
            for node in self.xs_list:
                temp = SimpleXS(xs_id=node.node_id.strip(), river=node.river.name.strip(), reach=node.reach.name.strip())
                simple_list.append(temp)
        elif node_type == 'culvert':
            if self.culvert_list is None:
                self.culvert_list = self._load_node_list(node_type)
            for node in self.culvert_list:
                temp = SimpleCulvert(culvert_id=node.node_id.strip(), river=node.river.name.strip(), reach=node.reach.name.strip())
                simple_list.append(temp)
        elif node_type == 'bridge':
            if self.bridge_list is None:
                self.bridge_list = self._load_node_list(node_type)
            for node in self.bridge_list:
                temp = SimpleBridge(bridge_id=node.node_id.strip(), river=node.river.name.strip(), reach=node.reach.name.strip())
                simple_list.append(temp)
        elif node_type == 'mult_open':
            if self.mult_open_list is None:
                self.mult_open_list = self._load_node_list(node_type)
            for node in self.mult_open_list:
                temp = SimpleMO(mo_id=node.node_id.strip(), river=node.river.name.strip(), reach=node.reach.name.strip())
                simple_list.append(temp)
        elif node_type == 'inline_struct':
            if self.inline_struct_list is None:
                self.inline_struct_list = self._load_node_list(node_type)
            for node in self.inline_struct_list:
                temp = SimpleIS(is_id=node.node_id.strip(), river=node.river.name.strip(), reach=node.reach.name.strip())
                simple_list.append(temp)
        elif node_type == 'lateral_struct':
            if self.lateral_struct_list is None:
                self.lateral_struct_list = self._load_node_list(node_type)
            for node in self.lateral_struct_list:
                temp = SimpleLS(ls_id=node.node_id.strip(), river=node.river.name.strip(), reach=node.reach.name.strip())
                simple_list.append(temp)
        return tuple(simple_list)
    
    def _get_node(self, node_type: str, node_id: str, river: str = None, reach: str = None) -> Node:
        """
        Returns requested node, ignores river and reach if not specified
        Raises <node>NotFound if station is not in model where <node> depends on node_type

        :param node_type: 
        :param node_id: id of station (cast to string automatically)
        :param river: river name (string)
        :param reach: reach name (string)
        :return: Node object for given node id
        :raise: <node>NotFound if node is not in the model (<node> depends on the node type)
        """
        # Either river and reach is specified or not, no half way allowed
        if river is None and reach is not None or river is not None and reach is None:
            raise RCException('Both river and reach must be specified or not specified')
        
        # strip white space
        node_id = str(node_id).strip()
        if river is not None:
            river = river.strip()
            reach = reach.strip()
            
        # Check for node list, create if necessary for appropriate node_type
        if node_type == 'xs':
            if self.xs_list is None:
                self.xs_list = self._load_node_list(node_type)
            node_list = self.xs_list
        elif node_type == 'culvert':
            if self.culvert_list is None:
                self.culvert_list = self._load_node_list(node_type)
            node_list = self.culvert_list
        elif node_type == 'bridge':
            if self.bridge_list is None:
                self.bridge_list = self._load_node_list(node_type)
            node_list = self.bridge_list
        elif node_type == 'mult_open':
            if self.mult_open_list is None:
                self.mult_open_list = self._load_node_list(node_type)
            node_list = self.mult_open_list
        elif node_type == 'inline_struct':
            if self.inline_struct_list is None:
                self.inline_struct_list = self._load_node_list(node_type)
            node_list = self.inline_struct_list
        elif node_type == 'lateral_struct':
            if self.lateral_struct_list is None:
                self.lateral_struct_list = self._load_node_list(node_type)
            node_list = self.lateral_struct_list

        # Search for node
        for node in node_list:
            if river is None and reach is None:
                if node.node_id.strip() == node_id:
                    return node
            else:
                if node.node_id.strip() == node_id and node.river.name.strip() == river and node.reach.name.strip() == reach:
                    return node
                
        if node_type == 'xs':
            raise CrossSectionNotFoundError('Cross section ' + str(node_id) + ' not found')
        elif node_type == 'culvert':
            raise CulvertNotFoundError('Culvert ' + str(node_id) + ' not found')
        elif node_type == 'bridge':
            raise BridgeNotFoundError('Bridge ' + str(node_id) + ' not found')
        elif node_type == 'mult_open':
            raise MultipleOpeningNotFoundError('Multiple opening ' + str(node_id) + ' not found')
        elif node_type == 'inline_struct':
            raise InlineStructureNotFoundError('Inline structure ' + str(node_id) + ' not found')
        elif node_type == 'lateral_struct':
            raise LateralStructureNotFoundError('Lateral structure ' + str(node_id) + ' not found')
        
    def _load_node_list(self, node_type: str) -> Tuple[Node]:
        """ 
        Returns list of all nodes of node_type (Node objects)
        
        :param node_type: type of node to list. Possible options are 'xs', 'culvert', 'bridge', 'mult_open', 'inline_struct', and 'lateral_struct'
        :return: all nodes of node_type as Node objects
        """
        if node_type == 'xs':
            node_type = ''
        elif node_type == 'culvert':
            node_type = 'Culv'
        elif node_type == 'bridge':
            node_type = 'BR'
        elif node_type == 'mult_open':
            node_type = 'MO'
        elif node_type == 'inline_struct':
            node_type = 'IS'
        elif node_type == 'lateral_struct':
            node_type = 'LS'
        
        node_list = []
        rivers = self.get_rivers()
        for riv in rivers:
            for reach in riv.reaches:
                for node in reach.nodes:
                    # blank node type indicates XS
                    if node.node_type == node_type:
                        node_list.append(node)
        return tuple(node_list)

    def open_project(self, project: Union[str, Path]):
        """
        Opens project in RAS
        :param project: string - full path to RAS project file (*.prj)
        """
        self.com_rc.Project_Open(project)
        self.project_is_open = True

    def show(self):
        """
        Makes RAS window visible
        """
        self.com_rc.ShowRas()

    def close(self):
        """
        closes RAS, this is only available in RAS5

        ******** This function does not appear to work!
        """
        if int(self.version[0]) >= 5:
            self.com_rc.QuitRAS()
        else:
            raise NotImplementedError('close() is only availble in RAS 5')

    def get_current_plan(self):
        """
        Returns name of current plan
        :return: string
        """
        pass
 
    # TODO - Add plan filename to plan objects
    def get_plans(self, basedir=None):
        """
        returns list of Plan objects
        :param basedir: ???? unknown
        :return: list of strings
        """
        a, names, b = self.com_rc.Plan_Names(None, None, basedir)
        # a appears to be number of plans
        # names is a list of plan names (NOT filenames)
        # b is a boolean, typically false, not sure what it represents
        # print '>>>', a, names, b
        plans = []
        for name in names:
            temp_plan = Plan(name, self)
            plans.append(temp_plan)
        return plans

    def set_plan(self, plan):
        """
        Sets current plan in RAS
        :param plan: Plan object of plan to use
        """
        # Check if get_profiles() has already been run
        if self._plan_lock:
            raise LockedPlanError('The plan can not be changed after running get_profiles(). I don\'t know why')
        self.com_rc.Plan_SetCurrent(plan.name)
        self.com_rc.PlanOutput_SetCurrent(plan.name)

    def run_current_plan(self):
        """
        Run current plan in RAS
        :return: status, messages
        """
        # RAS 5 appears to return and extra boolean, this should be tested more extensively
        if self.version[0] == 4:
            status, _, messages = self.com_rc.Compute_CurrentPlan(None, None)
        else:
            status, _, messages, _ = self.com_rc.Compute_CurrentPlan(None, None)
        self._model_ran = True
        return status, messages

    def hide_compute_window(self):
        """ Hides computation windows """
        self.com_rc.Compute_HideComputationWindow()
    
    def read_compute_msg(self, plan):
        """
        Read the ComputeMsgs.txt file
        This will enable the user to scan it for errors
        
        e.g.
        if "FLOW OPTIMIZATION FAILED TO CONVERGE, PROFILE    <n>" is in the file
        then the user will that the flow was not optimized for profile n
        
        :param plan: plan file used to run the current plan (.p**)
        :return: computation messages as a list of string
        """
        compute_msg_file = '{}.computeMsgs.txt'.format(plan)
        
        if self._model_ran is False:
            raise CurrentPlanNotRun('Run the current plan before reading the compute message.')
        if not os.path.isfile(compute_msg_file):
            raise FileNotFound('{} does not exist. The model needs to run for this file to be created'.format(compute_msg_file))
        
        return_strings = []
        with open(compute_msg_file, 'r') as compute_msg:
            for line in compute_msg:
                temp = line.strip()
                return_strings.append(temp)
        return return_strings
    
    def get_profiles(self):
        """
        Returns list of all profiles as Profile objects
        FYI - Output_GetProfiles (used in get_profiles()) appears to somehow prevent the current plan from being
        changed. self._plan_lock is used to keep track of get_profiles being used.
        :return: list of Profile objects
        """
        self._plan_lock = True  # Prevent plan from changing see above
        river_code = 2  # The value of this term appears to do nothing
        _, profile_names = self.com_rc.Output_GetProfiles(river_code, None)
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

    #----------------------   
    # There was a note from before that is_output_current() wasn't working
    # It appears to be working now (3/30/17 MJB)
    #----------------------
    def is_output_current(self, plan, show=False):
        """
        Returns True if output matches plan
        :param plan: Plan object of plan to check
        :param show: boolean - whether or not to show the window
        :return: boolean, string (error messages)
        """
        result, plan_name, unknown_bool, message = self.com_rc.PlanOutput_IsCurrent(plan.name, show, None)
        if DEBUG:
            print('>>> In is_output_current')
            print('>>>', (result, unknown_bool, message))
        return result, message

    # Methods below here are semi-private and are intended to be called from the River, Reach, and Node classes
    def geometry_getreaches(self, river_num):
        """
        Returns reach names in river numbered river_num using Geometry_GetReaches
        :param river_num: int
        :return: list of reach names
        """
        _, _, reaches = self.com_rc.Geometry_GetReaches(river_num, None, None)
        return reaches
    
    def output_getreaches(self, river_num):
        """
        Returns reach names in river numbered river_num using Output_GetReaches
        :param river_num: int
        :return: list of reach names
        """
        _, _, reaches = self.com_rc.Output_GetReaches(river_num, None, None)
        return reaches
    
    def geometry_getnodes(self, river_id, reach_id):
        """
        Return node names (stationing) and node types
        Node types may belong to the following non inclusive list: '' (cross section), 'BR', 'Culv', 'IS', ...
        :return: nodes_ids, node_types - two lists of strings
        """
        _, _, _, node_ids, node_types = self.com_rc.Geometry_GetNodes(river_id, reach_id, None, None, None)
        return node_ids, node_types

    def output_nodeoutput(self, river_id, reach_id, node_id, profile, value_type):
        """
        Return RAS node value
        :param river_id: river code for node
        :param reach_id: reach code for node
        :param node_id: code for node
        :param profile: code for desired profile
        :param value_type: RAS value type (see constants at top of this file)
        :return: float (probably)
        """
        # TODO - the 0 in the next line should be a lot smarter
        value = self.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, profile, value_type)[0]
        return value


    # TODO - remove once obsolete - change this to work with Plan objects
    def _current_plan_file(self):
        """
        Returns path and file name of current plan file
        :return: string
        """
        return self.com_rc.CurrentPlanFile()

    # TODO - move into get_rivers()
    def _output_getrivers(self):
        """
        Returns list of names of rivers in current project
        :return: list of strings
        """
        _, rivers = self.com_rc.Output_GetRivers(0, None)
        if rivers is None:
            raise NoOutputFile('Output file does not appear to exist. Model may not have run successfully.')
        return rivers

    # TODO - remove this, only in for testing
    def _nodes(self, river_id, reach_id):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        node_ids, node_types = self.output_getnodes(river_id, reach_id)
        return node_ids, node_types


def main_old():
    rc = RasController(version='503')
    #rc = RasController(version='41')
    # rc.open_project('x:/python/rascontrol/rascontrol/models/HG.prj')
    # rc.open_project("c:/Users/mike.bannister/Downloads/ras5/HEC-RAS_5.0_Beta_2015-08-21/RAS_50 Test Data/BaldEagleCrkMulti2D/BaldEagleDamBrk.prj")
    rc.open_project("x:/python/rascontrol/rascontrol/models/GHC.prj")

    plans = rc.get_plans()
    print('***************Plans', plans)  # returns plan names
    fname, name = rc.com_rc.Plan_GetFilename(plans[0].name)
    print(fname, name)
    x = rc.com_rc.Plan_GetFilename(plans[1].name)
    print(x)
    # rc.show()
    time.sleep(2)
    print('running...')
    #rc.run_current_plan()

    if not True:
        #rc.close()

        #sys.exit()
        print('current plan at start', rc._current_plan_file(), '\n')
        plan = plans[0]
        print('setting plan to',plan)
        rc.set_plan(plan)
        
        result, message = rc.is_output_current(plan, show=True)
        print('is output current?', result)
        
        print('\nrunning current plan...')
        print(rc.run_current_plan())
        result, message = rc.is_output_current(plan, show=True)
        print('Ran. is output current?', result)
        
        plan = plans[1]
        print('\nsetting plan to', plan)
        rc.set_plan(plan)
        
        print('current plan after set_plan()', rc._current_plan_file())
        result, message = rc.is_output_current(plan, show=True)
        print('is output current?', result)
        
        print('\nrunning current plan...')
        print(rc.run_current_plan())
        result, message = rc.is_output_current(plan, show=True)
        print('Ran. is output current?', result)
        rc.close()
        sys.exit()

        otherterm = rc.get_profiles()
        print('profiles in current plan', otherterm)
        print(
            """
            the call to rc.get_profiles() seems to be locking the plan in place. But is it? next step is to check if I can get WSELs
            or similar even after the get_profiles() for right profiles after swapping plans. or bail and just stop the damn
            user from changing the profile =P
            """
        )
        plans = rc.get_plans()
        print('***************Plans', plans)
        print('current plan before set_plan()', rc._current_plan_file())
        plan = plans[0]
        print(plan)
        rc.set_plan(plan)

        print('current plan after set_plan()', rc._current_plan_file())
        result, message = rc.is_output_current(plan, show=True)
        print(result)
        profs = rc.get_profiles()
        print(profs)
        sys.exit()  # ------------------------------------------------------------------------

    print(rc._current_plan_file())
    #rc.show()
    #print rc.run_current_plan()
    print('done')
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
            print(temp)
            node_id = temp[0]
            # 0 below is for BR up/down, 2 is code for wsel
            wsel1 = rc.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, profile_id, 2)[0]
            #wsel2 = rc.com_rc.Output_NodeOutput(river_id, reach_id, node_id, 0, 2, 2)[0]
            print(x, '/', y, '/', node_id, '/', wsel1)
            #kkprint x,'/', y,'/', node_id,'/', wsel1, wsel2, wsel1-wsel2
            #sys.exit()

    profs = rc.get_profiles()
    print(profs)
    with open('out.txt', 'wt') as outfile:
        rivers = rc.get_rivers()
        for riv in rivers:
            for reach in riv.reaches:
                print(riv)
                print(reach)
                for node in reach.nodes:
                    if node.node_type == '':
                        #print node, node.value(profs[0], MIN_CH_EL)
                        min_el = node.value(profs[0], MIN_CH_EL)
                        outfile.write(','.join([str(riv), str(reach), str(node), str(min_el)]))
                        for prof in profs:
                            outfile.write(','+str(node.value(prof, WSEL)))
                        outfile.write('\n')
    rc.close()


def main():
    rc = RasController(version='503')
    rc.open_project("x:/python/rascontrol/rascontrol/models/GHC.prj")

    plans = rc.get_plans()
    print('***************Plans', plans)  # returns plan names
    fname, name = rc.com_rc.Plan_GetFilename(plans[0].name)
    print('fname, name', fname, name)

    print('current plan file', rc._current_plan_file())

    profs = rc.get_profiles()
    print(profs)
    print(rc.get_xs(300138))

    #import pdb; pdb.set_trace()

    x= rc.simple_xs_list()
    for y in x:
        print(y)

    if not True:
        with open('out.txt', 'wt') as outfile:
            rivers = rc.get_rivers()
            for riv in rivers:
                for reach in riv.reaches:
                    print('river/reach', riv, reach)
                    for node in reach.nodes:
                        if node.node_type == '':
                            #print node, node.value(profs[0], MIN_CH_EL)
                            min_el = node.value(profs[0], MIN_CH_EL)
                            outfile.write(','.join([str(riv), str(reach), str(node), node.node_id, str(min_el)]))
                            for prof in profs:
                                outfile.write(','+str(node.value(prof, WSEL)))
                            outfile.write('\n')
    rc.close()


if __name__ == '__main__':
    main()