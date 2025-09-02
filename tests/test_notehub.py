"""
Unit tests for the notehub module.

This test suite validates the Notehub API integration functionality including:
- FirmwareType utility class
- NotehubClientService authentication and requests
- NotehubProject device management and firmware operations

Uses comprehensive urllib3 mocking to avoid external dependencies.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import json
import time

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import notehub


class TestFirmwareType(unittest.TestCase):
    """Test cases for FirmwareType utility class."""
    
    def test_firmware_type_constants(self):
        """Test that firmware type constants are defined correctly."""
        self.assertEqual(notehub.FirmwareType.User, "host")
        self.assertEqual(notehub.FirmwareType.Host, "host")
        self.assertEqual(notehub.FirmwareType.Card, "notecard")
        self.assertEqual(notehub.FirmwareType.Notecard, "notecard")
    
    def test_dfu_map_host(self):
        """Test DFU mapping for host firmware."""
        result = notehub.FirmwareType.DFUMap("host")
        self.assertEqual(result, "user")
    
    def test_dfu_map_notecard(self):
        """Test DFU mapping for notecard firmware."""
        result = notehub.FirmwareType.DFUMap("notecard")
        self.assertEqual(result, "card")
    
    def test_dfu_map_unknown(self):
        """Test DFU mapping for unknown firmware type."""
        result = notehub.FirmwareType.DFUMap("unknown")
        self.assertIsNone(result)


class TestNotehubClientService(unittest.TestCase):
    """Test cases for NotehubClientService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_uid = "app:12345678-1234-1234-1234-123456789abc"
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.user_token = "test_user_token"
        
    def test_init_with_user_token(self):
        """Test initialization with user access token."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        self.assertEqual(client._project_uid, self.project_uid)
        self.assertEqual(client._user_access_token, self.user_token)
        self.assertEqual(client.getAuthHeader, client._getXSessionHeader)
    
    def test_init_with_oauth(self):
        """Test initialization with OAuth credentials."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        self.assertEqual(client._project_uid, self.project_uid)
        self.assertEqual(client._client_id, self.client_id)
        self.assertEqual(client._client_secret, self.client_secret)
        self.assertEqual(client.getAuthHeader, client._getOauthTokenHeader)
    
    def test_init_missing_auth(self):
        """Test initialization with no authentication credentials."""
        with self.assertRaises(Exception) as context:
            notehub.NotehubClientService(project_uid=self.project_uid)
        
        self.assertIn("Must provide either a user access token or a client Id", str(context.exception))
    
    def test_init_missing_client_secret(self):
        """Test initialization with client ID but no secret."""
        with self.assertRaises(Exception) as context:
            notehub.NotehubClientService(
                project_uid=self.project_uid,
                client_id=self.client_id
            )
        
        self.assertIn("Must provide a client secret", str(context.exception))
    
    def test_custom_host(self):
        """Test initialization with custom host."""
        custom_host = "https://custom.notefile.net"
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token,
            host=custom_host
        )
        
        self.assertEqual(client.host, custom_host)

    @patch('notehub.http')
    def test_v1_request_success(self, mock_http):
        """Test successful v1 API request."""
        # Setup client
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"result": "success"}'
        mock_http.request.return_value = mock_response
        
        result = client.v1Request("devices", {"key": "value"}, {"param": "test"}, "POST")
        
        # Verify request was made correctly
        expected_url = f"https://api.notefile.net/v1/projects/{self.project_uid}/devices?param=test"
        mock_http.request.assert_called_once_with(
            "POST", 
            expected_url,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'text/plain',
                'X-Session-Token': self.user_token
            },
            body='{"key": "value"}'
        )
        
        self.assertEqual(result, {"result": "success"})

    @patch('notehub.http')
    def test_v1_request_error(self, mock_http):
        """Test v1 API request with error response."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock error response
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.data = b'{"error": "Bad request"}'
        mock_http.request.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            client.v1Request("devices")
        
        self.assertIn("Notehub Request Error:", str(context.exception))
        self.assertIn("400", str(context.exception))

    @patch('notehub.http')
    def test_v1_request_empty_response(self, mock_http):
        """Test v1 API request with empty response."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b''
        mock_http.request.return_value = mock_response
        
        result = client.v1Request("devices")
        
        self.assertEqual(result, {})

    @patch('notehub.http')
    def test_v0_request_success(self, mock_http):
        """Test successful v0 API request."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"status": "ok"}'
        mock_http.request.return_value = mock_response
        
        result = client.v0Request("card.status", "device123")
        
        # Verify request was made correctly
        expected_url = f"https://api.notefile.net/req?app={self.project_uid}&device=device123"
        mock_http.request.assert_called_once_with(
            'GET',
            url=expected_url,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'text/plain',
                'X-Session-Token': self.user_token
            },
            body='{"req": "card.status"}'
        )
        
        self.assertEqual(result, {"status": "ok"})

    @patch('notehub.http')
    def test_v0_request_empty_response(self, mock_http):
        """Test v0 API request with empty response data."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b''
        mock_http.request.return_value = mock_response
        
        result = client.v0Request("card.status", "device123")
        
        # Should return empty dict when response.data is empty
        self.assertEqual(result, {})

    @patch('notehub.http')
    def test_v0_request_dict_input(self, mock_http):
        """Test v0 API request with dictionary input."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"status": "ok"}'
        mock_http.request.return_value = mock_response
        
        req_dict = {"req": "card.status", "param": "value"}
        result = client.v0Request(req_dict)
        
        # Verify the dictionary was passed through correctly
        mock_http.request.assert_called_once()
        call_args = mock_http.request.call_args
        body = call_args[1]['body']
        self.assertEqual(json.loads(body), req_dict)

    @patch('notehub.http')
    @patch('time.time')
    def test_oauth_token_retrieval(self, mock_time, mock_http):
        """Test OAuth token retrieval and caching."""
        mock_time.return_value = 1000
        
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Mock successful token response
        token_response = MagicMock()
        token_response.status = 200
        token_response.data = b'{"access_token": "test_token", "expires_in": 60}'
        
        # Mock successful API response  
        api_response = MagicMock()
        api_response.status = 200
        api_response.data = b'{"result": "success"}'
        
        mock_http.request.side_effect = [token_response, api_response]
        
        result = client.v1Request("devices")
        
        # Verify token request was made
        self.assertEqual(mock_http.request.call_count, 2)
        
        # First call should be token request
        token_call = mock_http.request.call_args_list[0]
        self.assertEqual(token_call[0][0], "POST")
        self.assertIn("oauth2/token", token_call[0][1])
        
        # Second call should be API request with Bearer token
        api_call = mock_http.request.call_args_list[1]
        headers = api_call[1]['headers']
        self.assertEqual(headers['Authorization'], 'Bearer test_token')

    @patch('notehub.http')
    @patch('time.time')
    def test_oauth_token_error(self, mock_time, mock_http):
        """Test OAuth token retrieval error."""
        mock_time.return_value = 1000
        
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Mock token error response
        token_response = MagicMock()
        token_response.status = 401
        token_response.data = b'{"error": "invalid_credentials"}'
        mock_http.request.return_value = token_response
        
        with self.assertRaises(Exception) as context:
            client.v1Request("devices")
        
        self.assertIn("Unable to get token", str(context.exception))

    @patch('notehub.http')
    def test_request_method_with_no_existing_headers(self, mock_http):
        """Test _request method with no existing headers in kwargs."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"result": "success"}'
        mock_http.request.return_value = mock_response
        
        # Call _request without headers
        result = client._request('GET', 'https://example.com', body='test body')
        
        # Verify that auth headers were added
        mock_http.request.assert_called_once_with(
            'GET', 'https://example.com', 
            body='test body',
            headers={
                'Accept': 'application/json',
                'Content-Type': 'text/plain',
                'X-Session-Token': self.user_token
            }
        )
        self.assertEqual(result, mock_response)

    @patch('notehub.http')
    def test_request_method_with_existing_headers(self, mock_http):
        """Test _request method with existing headers in kwargs."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_http.request.return_value = mock_response
        
        # Call _request with existing headers
        existing_headers = {'Custom-Header': 'custom-value', 'Content-Type': 'application/json'}
        result = client._request('POST', 'https://example.com', headers=existing_headers, body='test')
        
        # Verify that auth headers were merged (should overwrite Content-Type)
        expected_headers = {
            'Custom-Header': 'custom-value',
            'Accept': 'application/json',
            'Content-Type': 'text/plain',  # Auth header should overwrite
            'X-Session-Token': self.user_token
        }
        
        mock_http.request.assert_called_once_with(
            'POST', 'https://example.com',
            headers=expected_headers,
            body='test'
        )
        self.assertEqual(result, mock_response)

    @patch('notehub.http')
    def test_request_method_401_error(self, mock_http):
        """Test _request method with 401 authentication error."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.data = b'{"error": "Unauthorized"}'
        mock_http.request.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            client._request('GET', 'https://example.com')
        
        self.assertEqual(str(context.exception), "Notehub authentication failed. Check API token(s)")

    @patch('notehub.http')
    def test_request_method_404_error(self, mock_http):
        """Test _request method with 404 not found error."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.data = b'{"error": "Not found"}'
        mock_http.request.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            client._request('GET', 'https://example.com/nonexistent')
        
        self.assertEqual(str(context.exception), "Notehub path not found")

    @patch('notehub.http')
    def test_request_method_generic_error(self, mock_http):
        """Test _request method with generic HTTP error."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.data = b'{"error": "Internal server error"}'
        mock_http.request.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            client._request('GET', 'https://example.com')
        
        expected_msg = "Notehub Request Error: 500 - b'{\"error\": \"Internal server error\"}'"
        self.assertEqual(str(context.exception), expected_msg)

    @patch('notehub.http')
    def test_request_method_with_oauth_headers(self, mock_http):
        """Test _request method with OAuth authentication headers."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Mock token response for OAuth
        token_response = MagicMock()
        token_response.status = 200
        token_response.data = b'{"access_token": "oauth_token", "expires_in": 60}'
        
        # Mock successful API response
        api_response = MagicMock()
        api_response.status = 200
        api_response.data = b'{"result": "success"}'
        
        mock_http.request.side_effect = [token_response, api_response]
        
        # Call _request which should trigger OAuth token retrieval
        existing_headers = {'Custom-Header': 'test'}
        result = client._request('GET', 'https://example.com', headers=existing_headers)
        
        # Verify OAuth token request was made first
        self.assertEqual(mock_http.request.call_count, 2)
        
        # Check the second call (actual API request) has merged headers
        api_call = mock_http.request.call_args_list[1]
        headers = api_call[1]['headers']
        
        self.assertIn('Custom-Header', headers)
        self.assertIn('Authorization', headers)
        self.assertTrue(headers['Authorization'].startswith('Bearer '))
        self.assertEqual(result, api_response)

    @patch('notehub.http')
    def test_request_method_success_status_codes(self, mock_http):
        """Test _request method with various 2xx success status codes."""
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            user_access_token=self.user_token
        )
        
        success_codes = [200, 201, 202, 204, 299]
        
        for status_code in success_codes:
            with self.subTest(status_code=status_code):
                mock_response = MagicMock()
                mock_response.status = status_code
                mock_response.data = b'{"success": true}'
                mock_http.request.return_value = mock_response
                
                result = client._request('GET', 'https://example.com')
                self.assertEqual(result, mock_response)

    @patch('notehub.http')
    @patch('time.time')
    def test_oauth_token_caching(self, mock_time, mock_http):
        """Test that OAuth tokens are properly cached."""
        mock_time.return_value = 1000
        
        client = notehub.NotehubClientService(
            project_uid=self.project_uid,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Mock token response
        token_response = MagicMock()
        token_response.status = 200
        token_response.data = b'{"access_token": "test_token", "expires_in": 60}'
        
        # Mock API responses
        api_response = MagicMock()
        api_response.status = 200
        api_response.data = b'{"result": "success"}'
        
        mock_http.request.side_effect = [token_response, api_response, api_response]
        
        # Make two API requests
        client.v1Request("devices")
        client.v1Request("firmware")
        
        # Should only request token once (cached for second request)
        self.assertEqual(mock_http.request.call_count, 3)  # 1 token + 2 API calls


class TestNotehubProject(unittest.TestCase):
    """Test cases for NotehubProject class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_uid = "app:12345678-1234-1234-1234-123456789abc"
        self.mock_client = MagicMock()
        
    def test_init_with_client(self):
        """Test initialization with existing client."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        self.assertEqual(project._client, self.mock_client)
    
    def test_init_create_client(self):
        """Test initialization creating new client."""
        with patch('notehub.NotehubClientService') as mock_service:
            mock_service.return_value = self.mock_client
            
            project = notehub.NotehubProject(
                project_uid=self.project_uid,
                client_id="test_id",
                client_secret="test_secret"
            )
            
            mock_service.assert_called_once_with(
                project_uid=self.project_uid,
                user_access_token=None,
                client_id="test_id",
                client_secret="test_secret"
            )
            self.assertEqual(project._client, self.mock_client)

    def test_fetch_available_firmware_all(self):
        """Test fetching all available firmware."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = [
            {"type": "notecard", "version": "8.1.3", "filename": "notecard.bin"},
            {"type": "host", "version": "3.1.2", "filename": "host.bin"}
        ]
        
        result = project.fetchAvailableFirmware()
        
        self.mock_client.v1Request.assert_called_once_with("firmware")
        self.assertEqual(len(result), 2)

    def test_fetch_available_firmware_by_type(self):
        """Test fetching firmware by specific type."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = [
            {"type": "notecard", "version": "8.1.3", "filename": "notecard.bin"}
        ]
        
        result = project.fetchAvailableFirmware(firmwareType="notecard")
        
        self.mock_client.v1Request.assert_called_once_with("firmware", params={"firmwareType": "notecard"})

    def test_get_device_info_single(self):
        """Test getting device info for single device."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = {"device": "info"}
        
        result = project.getDeviceInfo("device123")
        
        self.mock_client.v1Request.assert_called_once_with("devices/device123")
        self.assertEqual(result, {"device": "info"})

    def test_get_device_info_multiple(self):
        """Test getting device info for multiple devices."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.side_effect = [
            {"device": "info1"},
            {"device": "info2"}
        ]
        
        result = project.getDeviceInfo(["device123", "device456"])
        
        self.assertEqual(self.mock_client.v1Request.call_count, 2)
        self.assertEqual(len(result), 2)

    def test_get_device_info_all_paginated(self):
        """Test getting all device info with pagination."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        # Mock paginated responses
        self.mock_client.v1Request.side_effect = [
            {"devices": [{"id": "dev1"}, {"id": "dev2"}], "has_more": True},
            {"devices": [{"id": "dev3"}], "has_more": False}
        ]
        
        result = project.getDeviceInfo()
        
        # Should make two requests for pagination
        self.assertEqual(self.mock_client.v1Request.call_count, 2)
        self.assertEqual(len(result), 3)

    def test_provision_device(self):
        """Test device provisioning."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.provisionDevice("device123", "product456")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/provision",
            payload={"product_uid": "product456"},
            method='POST'
        )

    def test_delete_device(self):
        """Test device deletion."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.deleteDevice("device123", purge=True)
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123",
            method='DELETE',
            params={'purge': 'true'}
        )

    def test_enable_device(self):
        """Test device enable."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.enableDevice("device123")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/enable",
            method='POST'
        )

    def test_disable_device(self):
        """Test device disable."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.disableDevice("device123")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/disable",
            method='POST'
        )

    def test_enable_connectivity_assurance(self):
        """Test enable connectivity assurance."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.enableDeviceConnectivityAssurance("device123")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/enable-connectivity-assurance",
            method='POST'
        )

    def test_disable_connectivity_assurance(self):
        """Test disable connectivity assurance."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.disableDeviceConnectivityAssurance("device123")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/disable-connectivity-assurance",
            method='POST'
        )

    def test_set_device_environment_vars(self):
        """Test setting device environment variables."""
        project = notehub.NotehubProject(client=self.mock_client)
        env_vars = {"VAR1": "value1", "VAR2": "value2"}
        
        project.setDeviceEnvironmentVars("device123", env_vars)
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/environment_variables",
            payload={"environment_variables": env_vars},
            method='PUT'
        )

    def test_get_device_environment_vars_all(self):
        """Test getting all device environment variables."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = {
            "environment_variables": {"VAR1": "value1", "VAR2": "value2"}
        }
        
        result = project.getDeviceEnvironmentVars("device123")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/environment_variables"
        )
        self.assertEqual(result, {"environment_variables": {"VAR1": "value1", "VAR2": "value2"}})

    def test_get_device_environment_vars_specific(self):
        """Test getting specific device environment variables."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = {
            "environment_variables": {"VAR1": "value1", "VAR2": "value2", "VAR3": "value3"}
        }
        
        result = project.getDeviceEnvironmentVars("device123", ["VAR1", "VAR3"])
        
        self.assertEqual(result, {"VAR1": "value1", "VAR3": "value3"})

    def test_get_device_environment_vars_single_string(self):
        """Test getting single environment variable as string."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = {
            "environment_variables": {"VAR1": "value1", "VAR2": "value2"}
        }
        
        result = project.getDeviceEnvironmentVars("device123", "VAR1")
        
        self.assertEqual(result, {"VAR1": "value1"})

    def test_get_device_firmware_update_history(self):
        """Test getting device firmware update history."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = {"history": "data"}
        
        result = project.getDeviceFirmwareUpdateHistory("device123", "notecard")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/dfu/notecard/history"
        )
        self.assertEqual(result, {"history": "data"})

    def test_get_device_firmware_update_history_invalid_device(self):
        """Test getting firmware history with invalid device UID."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        with self.assertRaises(Exception) as context:
            project.getDeviceFirmwareUpdateHistory(["device123"], "notecard")
        
        self.assertIn("Device UID must be a string", str(context.exception))

    def test_get_device_firmware_update_status(self):
        """Test getting device firmware update status."""
        project = notehub.NotehubProject(client=self.mock_client)
        self.mock_client.v1Request.return_value = {"status": "in_progress"}
        
        result = project.getDeviceFirmwareUpdateStatus("device123", "notecard")
        
        self.mock_client.v1Request.assert_called_once_with(
            "devices/device123/dfu/notecard/status"
        )
        self.assertEqual(result, {"status": "in_progress"})

    def test_get_device_firmware_update_status_invalid_device(self):
        """Test getting firmware status with invalid device UID."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        with self.assertRaises(Exception) as context:
            project.getDeviceFirmwareUpdateStatus(123, "notecard")
        
        self.assertIn("Device UID must be a string", str(context.exception))

    def test_request_device_firmware_update(self):
        """Test requesting device firmware update."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.requestDeviceFirmwareUpdate("device123", "firmware.bin", "notecard")
        
        self.mock_client.v1Request.assert_called_once_with(
            "dfu/notecard/update",
            params={"deviceUID": "device123"},
            payload={"filename": "firmware.bin"},
            method='POST'
        )

    def test_request_device_firmware_update_invalid_device(self):
        """Test requesting firmware update with invalid device UID."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        with self.assertRaises(Exception) as context:
            project.requestDeviceFirmwareUpdate(123, "firmware.bin", "notecard")
        
        self.assertIn("Device UID must be a string", str(context.exception))

    def test_cancel_device_firmware_update(self):
        """Test canceling device firmware update."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        project.cancelDeviceFirmwareUpdate("device123", "notecard")
        
        self.mock_client.v1Request.assert_called_once_with(
            "dfu/notecard/cancel",
            params={"deviceUID": "device123"},
            method='POST'
        )

    def test_cancel_device_firmware_update_invalid_device(self):
        """Test canceling firmware update with invalid device UID."""
        project = notehub.NotehubProject(client=self.mock_client)
        
        with self.assertRaises(Exception) as context:
            project.cancelDeviceFirmwareUpdate([], "notecard")
        
        self.assertIn("Device UID must be a string", str(context.exception))


if __name__ == '__main__':
    unittest.main()