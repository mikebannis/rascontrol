from rascontrol.rascontrol import RasController


class River(object):
    def __init__(self,
                 name: str,
                 code: int,
                 rc: RasController):
        self.name = name  # River name, string
        self.code = code  # River code, int - these start at 1, not 0
        self.rc = rc  # RasController object
        self.reaches = self._get_reaches()  # list of Reach objects
        self._update_reach_codes()

    # TODO -  the reach code should probably be pulled from the rascontller, although i+1 seems to work
    def _get_reaches(self):
        """
        Gets list of reaches for river represented by self
        :return: list of Reach objects
        """
        reaches = []
        reach_names = self.rc.geometry_getreaches(self.code)
        for i, name in enumerate(reach_names):
            new_reach = Reach(name, i + 1, self)
            reaches.append(new_reach)
        return reaches

    def _update_reach_codes(self):
        """
        Sometimes the reach codes switch between the geometry and output files.
        This switches the codes after assigning each reach their respective nodes
        """

        if self.rc.output_getreaches(self.code) == self.rc.geometry_getreaches(self.code):
            pass
        else:
            new_reach_codes = {}
            new_reach_names = self.rc.output_getreaches(self.code)
            for code, reach in enumerate(new_reach_names):
                new_reach_codes[reach] = code + 1

            for reach in self.reaches:
                updated_code = new_reach_codes[reach.name]
                reach.code = updated_code

    def __repr__(self):
        return 'River name = "' + self.name + '", River code = "' + str(self.code) + '"'
