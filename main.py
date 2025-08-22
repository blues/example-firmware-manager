import json
import os
from auth import authenticate_request
from manage_firmware import manageFirmware
from notehub import NotehubProject
from rules import DevicesInUpdateFleet

def retrieveAuthToken():
    return os.getenv("FIRMWARE_CHECK_AUTH_TOKEN")

def connectToNotehubProject():
    PROJECT_UID = os.getenv("NOTEHUB_PROJECT_UID")
    NOTEHUB_CLIENT_ID = os.getenv("NOTEHUB_CLIENT_ID")
    NOTEHUB_CLIENT_SECRET = os.getenv("NOTEHUB_CLIENT_SECRET")

    return NotehubProject(project_uid=PROJECT_UID, client_id=NOTEHUB_CLIENT_ID, client_secret=NOTEHUB_CLIENT_SECRET)

project = None

def processRoutedSession(deviceUID, payload):

    

    notecardFirmwareVersion = payload.get("notecard_firmware")
    hostFirmwareVersion = payload.get("host_firmware")
    fleets = payload.get("fleets", [])

    # for now, assume only a single fleet if any
    fleet = None if len(fleets) == 0 else fleets[0]

    global project

    if project is None:
        project = connectToNotehubProject()

    return manageFirmware(project, deviceUID, fleet, notecardFirmwareVersion, hostFirmwareVersion, rules=DevicesInUpdateFleet)

def lambda_handler(event, context):
    result = authenticate_request(event, retrieveAuthToken())
    if not result.get('success', False):
        return {
            'statusCode': 401,
            'body': result.get('error', 'authentication failure reason not provided')
        }
    
    try:
        payload = event["body"]
        if not isinstance(payload, dict):
            payload = json.loads(payload)

        deviceUID = payload.get("device")
        if not deviceUID or not isinstance(deviceUID, str):
            return {
                'statusCode': 400,
                'body': "bad request. missing valid device UID from the request"
            }
        
        r = processRoutedSession(deviceUID, payload)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"error":str(e),"request_payload":event["body"]})
        }
    return {
        'statusCode': 200,
        'body': json.dumps({"response":r,"request_payload":payload})
    }

if __name__ == "__main__":
    e = {
        "body": {
            "device": "dev:868050040074169",
            "fleets": [
            "fleet:563ed441-263c-4d67-a13c-0e5b9becf3bf"
            ]
        }
        }
    print(lambda_handler(e, None))

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
