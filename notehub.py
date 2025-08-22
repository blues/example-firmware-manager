
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

import urllib3
from urllib.parse import urlencode
import json
import time



http = urllib3.PoolManager()


class FirmwareType:
    User="host"
    Host="host"
    Card="notecard"
    Notecard="notecard"

    @staticmethod
    def DFUMap(firmware_type: str) -> str:
        mapping = {
            "host": "user",
            "notecard": "card"
        }
        return mapping.get(firmware_type, None)

class NotehubClientService:
    
    def __init__(self, project_uid, user_access_token=None, client_id=None, client_secret=None, host='https://api.notefile.net') -> None:
        if user_access_token is None and client_id is None:
            raise(Exception("Must provide either a user access token or a client Id for authentication"))
        
        if client_id is not None and client_secret is None:
            raise(Exception("Must provide a client secret along with the client ID to enable authentication"))
        
        self._shared_header = {
                'Accept': 'application/json',
                'Content-Type': 'text/plain',
                }
        
        isUserToken = user_access_token is not None
        
        self._project_uid = project_uid
        self.host = host
        self._bearer_token = None
        
        if isUserToken:
            self.getAuthHeader = self._getXSessionHeader
            self._user_access_token = user_access_token
            return
        
        self._client_id = client_id
        self._client_secret = client_secret
        self.getAuthHeader = self._getOauthTokenHeader

    def _bearer_token_is_expired(self):
        return time.time() >= self._bearer_token["expires_at"]
    
    def _query_oauth_for_token(self):
        url = 'https://notehub.io/oauth2/token'
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self._client_id,
            'client_secret': self._client_secret
        }

        s = urlencode(data)

        response = http.request("POST", url, headers=headers, body=s)

        responseJSON = json.loads(response.data)

        if response.status == 200:
            return responseJSON
            
        else:
            raise(Exception(f"Unable to get token: {responseJSON}"))


    def _getBearerToken(self):
        if self._bearer_token is None or self._bearer_token_is_expired():
            token_info = self._query_oauth_for_token()
            token_info["expires_at"] = time.time() + token_info["expires_in"]*60

            self._bearer_token = token_info

        return self._bearer_token["access_token"]

            



    def _getOauthTokenHeader(self):
        headers = self._shared_header
        headers["Authorization"] = "Bearer " + self._getBearerToken()

        return headers

    def _getXSessionHeader(self):
        headers = self._shared_header
        headers["X-Session-Token"] = self._user_access_token

        return headers
    
    def _request(self, *args, **kwargs):
        """
        Execute an HTTP request with automatic authentication and error handling.
        
        This method automatically injects authentication credentials and handles common
        HTTP status codes (401, 404, 500, etc.) with appropriate error messages.
        
        Args:
            *args: Positional arguments passed to http.request()
            **kwargs: Keyword arguments passed to http.request()
            
        Returns:
            http.Response: The HTTP response object for successful requests (2xx status)
            
        Raises:
            Exception: For authentication failures (401), not found errors (404),
                      or other HTTP errors with descriptive messages
        """
        # Apply authentication headers
        auth_headers = self.getAuthHeader()
        
        # Merge authentication headers with existing headers (if any)
        if 'headers' in kwargs:
            kwargs['headers'].update(auth_headers)
        else:
            kwargs['headers'] = auth_headers
        
        
        # Use requests.request to handle any HTTP method and arguments
        response = http.request(*args, **kwargs)

        if response.status >=200 and response.status < 300:
            return response
        
        if response.status == 401:
            raise Exception("Notehub authentication failed. Check API token(s)")
        
        if response.status == 404:
            raise Exception("Notehub path not found")
        
        msg = f"Notehub Request Error: {response.status} - {response.data}"
        raise Exception(msg)

    
    def v1Request(self, path, payload = {}, params = {}, method = 'GET'):

        p = urlencode(params)
        url = f"{self.host}/v1/projects/{self._project_uid}/{path}?{p}"

        jsonPayload = json.dumps(payload)

        response = self._request(method, url, body=jsonPayload)

        if not response.data:
            return {}
        
        return json.loads(response.data)
    
    def v0Request(self, req, deviceUID = None):
        url = f"{self.host}/req?app={self._project_uid}&device={deviceUID if not deviceUID==None else ''}"

        if isinstance(req, str):
            req = {"req":req}

        body = json.dumps(req)

        response = self._request('GET', url=url, body = body)

        if not response.data:
            return {}
        
        return json.loads(response.data)


class NotehubProject:

    def __init__(self, client=None,project_uid=None, user_access_token=None, client_id=None, client_secret=None) -> None:
        self._client = client
        if client is None:
            self._client = NotehubClientService(project_uid=project_uid, user_access_token=user_access_token, client_id=client_id, client_secret=client_secret)
        

    def fetchAvailableFirmware(self, firmwareType=None):
        
        if firmwareType is None:
            return self._client.v1Request("firmware")
        
        return self._client.v1Request("firmware", params={"firmwareType":firmwareType})
        
    def getDeviceInfo(self, deviceUID=None):

        if deviceUID != None:
            if isinstance(deviceUID, str):
                return self._client.v1Request(f"devices/{deviceUID}")
            
            return [self._client.v1Request(f"devices/{d}") for d in deviceUID]
        

        hasMore = True
        devices = []
        pageSize = 500
        pageNumber = 1
        while hasMore:
            r = self._client.v1Request("devices", params={"pageNum": pageNumber, "pageSize": pageSize})
            devices += r["devices"]
            hasMore = r.get("has_more", False)
            pageNumber += 1

        return devices   
        

    
    def provisionDevice(self, deviceUID, productUID):

        self._client.v1Request(f"devices/{deviceUID}/provision", payload={"product_uid":productUID}, method='POST')

    def deleteDevice(self, deviceUID, purge=False):
        purgeStr = str(purge).lower()
        self._client.v1Request(f"devices/{deviceUID}", method='DELETE', params={'purge':purgeStr})
    
    def enableDevice(self, deviceUID):
        return self._client.v1Request(f"devices/{deviceUID}/enable", method='POST')
    
    def disableDevice(self, deviceUID):
        return self._client.v1Request(f"devices/{deviceUID}/disable", method='POST')
    
    def enableDeviceConnectivityAssurance(self, deviceUID):
        self._client.v1Request(f"devices/{deviceUID}/enable-connectivity-assurance", method='POST')

    def disableDeviceConnectivityAssurance(self, deviceUID):
        self._client.v1Request(f"devices/{deviceUID}/disable-connectivity-assurance", method='POST')

    def setDeviceEnvironmentVars(self, deviceUID, environmentVars):
        return self._client.v1Request(f"devices/{deviceUID}/environment_variables", payload={"environment_variables":environmentVars}, method='PUT')
    
    def getDeviceEnvironmentVars(self, deviceUID, environmentVars=None):
        v = self._client.v1Request(f"devices/{deviceUID}/environment_variables")
        if environmentVars is None:
            return v
        
        if isinstance(environmentVars, str):
            environmentVars = [environmentVars]

        a = {key: v["environment_variables"][key] for key in environmentVars if key in v["environment_variables"]}
        return a

    def getDeviceFirmwareUpdateHistory(self, deviceUID, firmwareType):
        if isinstance(deviceUID, str):
            return self._client.v1Request(f"devices/{deviceUID}/dfu/{firmwareType}/history")
        
        raise(Exception("Device UID must be a string. Only accepts a single device UID. Arrays are not supported"))

    def getDeviceFirmwareUpdateStatus(self, deviceUID, firmwareType):

        if isinstance(deviceUID, str):
            return self._client.v1Request(f"devices/{deviceUID}/dfu/{firmwareType}/status")
        
        raise(Exception("Device UID must be a string. Only accepts a single device UID. Arrays are not supported"))

    def requestDeviceFirmwareUpdate(self, deviceUID, fileName, firmwareType):
        
        if isinstance(deviceUID, str):
            return self._client.v1Request(f"dfu/{firmwareType}/update", params={"deviceUID":deviceUID}, payload={"filename":fileName}, method='POST')

        raise(Exception("Device UID must be a string. Only accepts a single device UID. Arrays are not supported"))
    
    def cancelDeviceFirmwareUpdate(self, deviceUID, firmwareType):
        
        if isinstance(deviceUID, str):
            return self._client.v1Request(f"dfu/{firmwareType}/cancel", params={"deviceUID":deviceUID}, method='POST')

        raise(Exception("Device UID must be a string. Only accepts a single device UID. Arrays are not supported"))

