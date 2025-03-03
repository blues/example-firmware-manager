import json
import os
from manage_firmware import manageFirmware
from notehub import NotehubProject
from rules import DevicesInUpdateFleet

def connectToNotehubProject():
    PROJECT_UID = os.getenv("NOTEHUB_PROJECT_UID")
    NOTEHUB_CLIENT_ID = os.getenv("NOTEHUB_CLIENT_ID")
    NOTEHUB_CLIENT_SECRET = os.getenv("NOTEHUB_CLIENT_SECRET")

    return NotehubProject(project_uid=PROJECT_UID, client_id=NOTEHUB_CLIENT_ID, client_secret=NOTEHUB_CLIENT_SECRET)

project = None

def processRoutedSession(payload):

    deviceUID = payload.get("device")
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
    try:
        payload = event["body"]
        if not isinstance(payload, dict):
            payload = json.loads(payload)
        r = processRoutedSession(payload)
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