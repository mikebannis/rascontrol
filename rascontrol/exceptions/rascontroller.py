class RCException(Exception):
    """ Base class for all rascontrol exceptions """
    pass


class RASOpenError(RCException):
    """
    rascontrol won't currently run if RAS is already open and raise RASOpen if
    it is.  I'm not sure why I did this. In HydrologyManager I blocked HM from
    starting if excel was already running to prevent accidently closing all
    excel spreadsheets on the computer. It may be a carry over habit from that
    project. There may also be a HEC-RAS controller specific reason for it as
    well that I can't remember.
    """
    pass


class NoProjectError(RCException):
    """ Indicates a project has not yet been opened """
    pass


class LockedPlanError(RCException):
    pass


class CurrentPlanNotRunError(RCException):
    """Indicates that the current plan has not yet been run"""
    pass


class CrossSectionNotFoundError(RCException):
    pass


class CulvertNotFoundError(RCException):
    pass


class BridgeNotFoundError(RCException):
    pass


class MultipleOpeningNotFoundError(RCException):
    pass


class InlineStructureNotFoundError(RCException):
    pass


class LateralStructureNotFoundError(RCException):
    pass
