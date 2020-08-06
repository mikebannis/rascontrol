from __future__ import print_function

import os

from rascontrol.rascontroller import RasController
from tests.util import detect_hec_ras_version

WSEL = 2
MIN_CH_EL = 5


def test_ras_controller():
    hec_ras_version = detect_hec_ras_version()

    print("Detected HEC-RAS-Version:", hec_ras_version)

    tests_folder = os.path.abspath(os.path.join(os.path.abspath(__file__), ".."))

    bald_eagle_project = os.path.join(
        tests_folder, "models/507/1D Unsteady Flow Hydraulics/Balde Eagle Creek/BaldEagle.prj")

    rc = RasController(version=hec_ras_version)

    rc.open_project(bald_eagle_project)

    plans = rc.get_plans()
    print('Plans', plans)  # returns plan names

    fname, name = rc.com_rc.Plan_GetFilename(plans[0].name)
    print('fname, name', fname, name)

    print('current plan file', rc._current_plan_file())

    # rc.run_current_plan()  # takes too long on Github Actions

    # profs = rc.get_profiles()
    # print(profs)

    # print(rc.get_xs(138154.4))
    #
    # for cross_section in rc.simple_xs_list():
    #     print(cross_section)

    # with open(os.path.join(tests_folder, 'out.txt'), 'wt') as outfile:
    #     rivers = rc.get_rivers()
    #     for riv in rivers:
    #         for reach in riv.reaches:
    #             print('river/reach', riv, reach)
    #             for node in reach.nodes:
    #                 if node.node_type == '':
    #                     # print node, node.value(profs[0], MIN_CH_EL)
    #                     min_el = node.value(profs[0], MIN_CH_EL)
    #                     outfile.write(','.join([str(riv), str(reach), str(node), node.node_id, str(min_el)]))
    #                     for prof in profs:
    #                         outfile.write(',' + str(node.value(prof, WSEL)))
    #                     outfile.write('\n')

    rc.close()

    assert True
