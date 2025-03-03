import os
import time
from notehub import NotehubProject, FirmwareType


DEFAULT_RULES = [{"id":"default",
                  "conditions":None,
                  "targetVersions": None}]

def connectToNotehubProject():
    PROJECT_UID = os.getenv("NOTEHUB_PROJECT_UID")
    NOTEHUB_CLIENT_ID = os.getenv("NOTEHUB_CLIENT_ID")
    NOTEHUB_CLIENT_SECRET = os.getenv("NOTEHUB_CLIENT_SECRET")

    return NotehubProject(project_uid=PROJECT_UID, client_id=NOTEHUB_CLIENT_ID, client_secret=NOTEHUB_CLIENT_SECRET)

class FirmwareCache:

    def __init__(self) -> None:
        self.cache = {}
        self.cache_expiry = 0
        self._expiration_duration_seconds = 1800

    def update(self, project):
        ts = time.time()
        response = project.fetchAvailableFirmware()

        c = {FirmwareType.Notecard:{}, FirmwareType.Host:{}}
        for i in response:
            t = i.get('type')
            v = i.get('version')
            f = i.get('filename')
            if t is None or v is None or f is None:
                continue
            c[t][v] = f

        self.cache = c
        self.cache_expiry = ts + self._expiration_duration_seconds


            

    def retrieve(self, project, firmwareType, version):
        if self._cacheIsExpired:
            self.update(project)

        if firmwareType not in self.cache:
            raise(Exception(f"Firmware for {firmwareType} not available in local firmware cache"))
        
        if version not in self.cache[firmwareType]:
            raise(Exception(f"Firmware version {version} for {firmwareType} not available in local firmware cache"))
        
        f = self.cache[firmwareType][version]
        if not isinstance(f, str) or f == "":
            raise(Exception(f"Invalid firmware file name for version {version} for {firmwareType} not available in local firmware cache"))
        
        return f

    def _cacheIsExpired(self):
        return time.time() >= self.cache_expiry

firmwareCache = FirmwareCache()

def getFirmwareUpdateTargets(fleetUID, notecardVersion, hostVersion, rules = DEFAULT_RULES):
    # !!!!IMPORTANT!!!
    # If both Notecard and Host firmware updates are requested, Notecard firmware updates
    # will _always_ preempt Host firmware updates.  Even if the host firmware update is already in progress
    #
    # If the order of firmware updates matters. That is, the host firmware update needs to
    # occur before the Notecard firmware update, then a more complex rule scheme will be required.

    # "notecard" a string or a function that accepts a Notecard version string.  If None or the field is excluded, it won't check the Notecard firmware version
    # "host" a string or a function that accepts a host version string. If None or the field is excluded, it won't check the host firmware version
    # "targetVersions" a dictionary with "notecard" and "host" fields where the value is the respective firmware version. If the value is None or the field is excluded, then no action will be taken
    #                  if the targetVersions is excluded or None, then no update requests will be made
    # "conditions" a dictionary of "notecard", "host", "fleet" fields that describe the conditions under which to perform a firmware update.  If field is excluded or set to None, then it's assumed no conditions guard the update to the target versions (used as a fallback if no previous rules have been met)
    

    # IF _all_ conditions are met, then perform update to target versions. Rules are executed top to bottom of the array.  Lower indexes in the array take precedence
    # rules = [{"conditions":{"notecard": "at-my-desired-firmware",
    #                         "host": "at host desired firmware",
    #                         "fleet": 'my-fleet-uid'},
    #           "targetVersions":None #don't update if we have the desired conditions
    #         },
    #         {"conditions":{"notecard":'abc',   # if these conditions are met
    #                          "host":'def',
    #                          "fleet": 'my-fleet-uid'
    #                         },
    #            "targetVersions": defaultTargetVersions  #update to these versions
    #         },
    #         {"conditions":{"notecard": lambda v: v.startsWith("8."), 
    #                        "host": 'uio',
    #                        "fleet": 'my-fleet-uid'
    #                        },
    #          "targetVersions":defaultTargetVersions
    #         }
    #         ]


    def match_condition(value, condition):
        if condition is None:
            # if there's no condition, then it should always return the condition was matched
            return True
        
        if callable(condition):
            return condition(value)
        
        return value == condition
    
    if not isinstance(rules, list):
        rules = [rules]

    for i, r in enumerate(rules):
        c = r.get("conditions", None)
        id = r.get("id", f"rule-{i + 1}")
        targetVersions  = r.get("targetVersions", None)
        if c is None:
            return (id, targetVersions)
        
        notecardUpdateStatus = match_condition(notecardVersion, c.get("notecard"))
        hostUpdateStatus     = match_condition(hostVersion, c.get("host"))
        fleetMatches         = match_condition(fleetUID, c.get("fleet"))
        if notecardUpdateStatus and hostUpdateStatus and fleetMatches:
            return (id, targetVersions)

    return (None, None)



def fetchDeviceFirmwareVersion(project, deviceUID, firmwareType):
    d = project.getDeviceFirmwareUpdateHistory(deviceUID, firmwareType)
    return d.get("current",{}).get("version")
    

def requestUpdateToTargetVersion(project, deviceUID, currentVersion, targetVersions, firmwareType):
    #global firmwareCache

    fw = targetVersions.get(firmwareType)
    
    if (fw is None):
        return f"No firmware update request for {firmwareType}"

    if (fw == currentVersion):
        return F"Skipping update request for {firmwareType}. Already at target version of {fw}."
    
    file = firmwareCache.retrieve(project, firmwareType, fw)

    if file is None:
        raise(Exception(f"Unable to locate {firmwareType} firmware image for requested version {fw}"))
    
    project.requestDeviceFirmwareUpdate(deviceUID, file, firmwareType)

    return f"Requested {firmwareType} firmware update from {currentVersion} to {fw}."

    




def manageFirmware(project, deviceUID,fleetUID=None,notecardFirmwareVersion=None, hostFirmwareVersion=None, rules={}):

    if notecardFirmwareVersion is None:
        notecardFirmwareVersion = fetchDeviceFirmwareVersion(project, deviceUID, FirmwareType.Notecard)

    if hostFirmwareVersion is None:
        hostFirmwareVersion = fetchDeviceFirmwareVersion(project, deviceUID, FirmwareType.Host)

    (ruleID, targetVersions) = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=notecardFirmwareVersion, hostVersion=hostFirmwareVersion, rules=rules)

    if ruleID is None:
        return "No rule conditions met. No updates required"
    
    ruleMessage = f"According to rule id {ruleID},"
    updateNotRequired = targetVersions is None
    if updateNotRequired:
        return f"{ruleMessage} firmware requirements met, no updates required"
    
    
    updateStatus = project.getDeviceFirmwareUpdateStatus(deviceUID, FirmwareType.Notecard)

    if updateStatus.get("dfu_in_progress", False):
        return f"{ruleMessage} firmware requirements NOT met.  Update not requested because Notecard update is in progress"
    
    updateStatus = project.getDeviceFirmwareUpdateStatus(deviceUID, FirmwareType.Host)

    if updateStatus.get("dfu_in_progress", False):
        return f"{ruleMessage} firmware requirements NOT met.  Update not requested because Host update is in progress"
    

    ncMessage   = requestUpdateToTargetVersion(project, deviceUID, notecardFirmwareVersion, targetVersions, FirmwareType.Notecard)
    hostMessage = requestUpdateToTargetVersion(project, deviceUID, hostFirmwareVersion, targetVersions, FirmwareType.Host)

    m = " ".join([ruleMessage, ncMessage, hostMessage])
    
    return m
