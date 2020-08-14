from win32com.universal import com_error

from rascontrol.rascontrol import RasController

HEC_RAS_VERSIONS = ["400", "41", "500", "501", "503", "504", "505", "506", "507"]


def detect_hec_ras_version():
    for hec_ras_version in HEC_RAS_VERSIONS:
        try:
            rc = RasController(hec_ras_version)
            rc.close()
            return hec_ras_version
        except com_error:
            pass

    raise ValueError("no HEC-RAS version found.")
