import json
import os
from auth import authenticate_request
from manage_firmware import manageFirmware
from notehub import NotehubProject
from rules import DevicesInUpdateFleet

def str_to_bool(value):
      """
      Convert a string representation of a boolean to its boolean equivalent.
      Returns False for None input.
      
      Args:
          value: String or None
          
      Returns:
          bool: True for 'true', '1', 'yes', 'on' (case-insensitive), False 
  otherwise
      """
      if value is None:
          return False
      return str(value).lower() in ('true', '1', 'yes', 'on')

def parse_firmware_json(firmware_data):
    """
    Parse firmware data that might be a JSON string.
    
    If the firmware data is a string that looks like JSON, attempt to parse it.
    Otherwise, return the data as-is.
    
    Args:
        firmware_data: Could be a dict, JSON string, or other data type
        
    Returns:
        dict or original data: Parsed JSON object if successful, otherwise original data
    """
    if not isinstance(firmware_data, str):
        return firmware_data
    
    # Check if string looks like JSON (starts with { and ends with })
    stripped = firmware_data.strip()
    if not (stripped.startswith('{') and stripped.endswith('}')):
        return firmware_data
    
    try:
        parsed = json.loads(firmware_data)
        return parsed
    except (json.JSONDecodeError, ValueError):
        # If parsing fails, return the original string
        return firmware_data

def parse_firmware_fields(payload):
    """
    Parse firmware_notecard and firmware_host fields if they are JSON strings.
    
    Args:
        payload (dict): Request payload that may contain firmware fields
        
    Returns:
        dict: Payload with parsed firmware fields
    """
    # Create a copy to avoid modifying the original
    parsed_payload = payload.copy()
    
    # Parse firmware_notecard if present
    if 'firmware_notecard' in parsed_payload:
        parsed_payload['firmware_notecard'] = parse_firmware_json(parsed_payload['firmware_notecard'])
    
    # Parse firmware_host if present  
    if 'firmware_host' in parsed_payload:
        parsed_payload['firmware_host'] = parse_firmware_json(parsed_payload['firmware_host'])
    
    return parsed_payload

def retrieveAuthToken():
    return os.getenv("FIRMWARE_CHECK_AUTH_TOKEN")

def connectToNotehubProject():
    PROJECT_UID = os.getenv("NOTEHUB_PROJECT_UID")
    NOTEHUB_CLIENT_ID = os.getenv("NOTEHUB_CLIENT_ID")
    NOTEHUB_CLIENT_SECRET = os.getenv("NOTEHUB_CLIENT_SECRET")

    return NotehubProject(project_uid=PROJECT_UID, client_id=NOTEHUB_CLIENT_ID, client_secret=NOTEHUB_CLIENT_SECRET)

project = None

def processRoutedSession(deviceUID, payload, is_dry_run):


    global project

    if project is None:
        project = connectToNotehubProject()

    return manageFirmware(project, deviceUID, payload, rules=DevicesInUpdateFleet, is_dry_run=is_dry_run)

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
        
        is_dry_run = bool( str_to_bool(payload.get('is_dry_run')) 
                        or str_to_bool(event.get("headers",{}).get('x-dry-run'))
                        or str_to_bool(event.get("queryStringParameters",{}).get('is_dry_run'))
                    )
        
        # Parse firmware fields if they are JSON strings
        parsed_payload = parse_firmware_fields(payload)
        
        r = processRoutedSession(deviceUID, parsed_payload, is_dry_run)
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
