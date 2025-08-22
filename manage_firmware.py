import os
import time
from notehub import NotehubProject, FirmwareType
from rules_engine import getFirmwareUpdateTargets, DEFAULT_RULES

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
        if self._cacheIsExpired():
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




def fetchDeviceFirmwareInfo(project, deviceUID, firmwareType):
    d = project.getDeviceFirmwareUpdateHistory(deviceUID, firmwareType)
    return d.get("current",{})
    

def requestUpdateToTargetVersion(project, deviceUID, currentVersion, target_versions, firmwareType):
    #global firmwareCache

    fw = target_versions.get(firmwareType)
    
    if (fw is None):
        return f"No firmware update request for {firmwareType}"

    if (fw == currentVersion):
        return F"Skipping update request for {firmwareType}. Already at target version of {fw}."
    
    file = firmwareCache.retrieve(project, firmwareType, fw)

    if file is None:
        raise(Exception(f"Unable to locate {firmwareType} firmware image for requested version {fw}"))
    
    project.requestDeviceFirmwareUpdate(deviceUID, file, firmwareType)

    return f"Requested {firmwareType} firmware update from {currentVersion} to {fw}."

    




def manageFirmware(project, deviceUID, device_data, rules={}):

    if device_data.get("firmware_notecard") is None:
        device_data["firmware_notecard"] = fetchDeviceFirmwareInfo(project, deviceUID, FirmwareType.Notecard)

    if device_data.get("firmware_host") is None:
        device_data["firmware_host"] = fetchDeviceFirmwareInfo(project, deviceUID, FirmwareType.Host)

    
    (ruleID, target_versions) = getFirmwareUpdateTargets(device_data, rules)

    if ruleID is None:
        return "No rule conditions met. No updates required"
    
    ruleMessage = f"According to rule id {ruleID},"
    updateNotRequired = target_versions is None
    if updateNotRequired:
        return f"{ruleMessage} firmware requirements met, no updates required"
    
    
    updateStatus = project.getDeviceFirmwareUpdateStatus(deviceUID, FirmwareType.Notecard)

    if updateStatus.get("dfu_in_progress", False):
        return f"{ruleMessage} firmware requirements NOT met.  Update not requested because Notecard update is in progress"
    
    updateStatus = project.getDeviceFirmwareUpdateStatus(deviceUID, FirmwareType.Host)

    if updateStatus.get("dfu_in_progress", False):
        return f"{ruleMessage} firmware requirements NOT met.  Update not requested because Host update is in progress"
    

    # Extract current versions from device_data for update requests
    notecardFirmwareVersion = device_data.get("firmware_notecard", {}).get("version")
    hostFirmwareVersion = device_data.get("firmware_host", {}).get("version")
    
    
    ncMessage   = requestUpdateToTargetVersion(project, deviceUID, notecardFirmwareVersion, target_versions, FirmwareType.Notecard)
    hostMessage = requestUpdateToTargetVersion(project, deviceUID, hostFirmwareVersion, target_versions, FirmwareType.Host)

    m = " ".join([ruleMessage, ncMessage, hostMessage])
    
    return m

#MIT License

#Copyright (c) 2025 Blues Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
