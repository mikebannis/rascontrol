class NoOutputFile(Exception):
    pass


class FileNotFound(Exception):
    pass


class RCException(Exception):
    """ Base class for all rascontrol exceptions """
    pass


class RASOpen(RCException):
    """
    rascontrol won't currently run if RAS is already open and raise RASOpen if
    it is.  I'm not sure why I did this. In HydrologyManager I blocked HM from
    starting if excel was already running to prevent accidently closing all
    excel spreadsheets on the computer. It may be a carry over habit from that
    project. There may also be a HEC-RAS controller specific reason for it as
    well that I can't remember.
    """
    pass


class NoProject(RCException):
    """ Indicates a project has not yet been opened """
    pass


class LockedPlan(RCException):
    pass


class CurrentPlanNotRun(RCException):
    """Indicates that the current plan has not yet been run"""
    pass


class CrossSectionNotFound(RCException):
    pass


class CulvertNotFound(RCException):
    pass


class BridgeNotFound(RCException):
    pass


class MultipleOpeningNotFound(RCException):
    pass


class InlineStructureNotFound(RCException):
    pass


class LateralStructureNotFound(RCException):
    pass
