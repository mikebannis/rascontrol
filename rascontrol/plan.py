from rascontrol.rascontrol import RasController


class Plan(object):
    """ Holds information for a plan """
    def __init__(self,
                 name: str,
                 rc: RasController) -> None:
        self.name = name  # Plan name, string
        self.rc = rc   # RasController object
        self.filename = self._get_filename(self.name)  # filename with full path

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'Plan name = "' + self.name + '"/Filename = "' + self.filename + '"'

    def _get_filename(self,
                      name: str) -> str:
        filename, _ = self.rc.com_rc.Plan_GetFilename(name)
        # _ is the plan name, as we already have this it's ignored
        return filename
