"""
Unit tests for the manage_firmware module.

This test suite validates the firmware management functionality including:
- Notehub project connection
- Firmware caching mechanisms  
- Device firmware version fetching
- Firmware update requests
- Main firmware management orchestration

Only mocks external dependencies (notehub module), tests all public methods/functions.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import time

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import manage_firmware


class TestConnectToNotehubProject(unittest.TestCase):
    """Test cases for connectToNotehubProject function."""
    
    @patch('manage_firmware.NotehubProject')
    @patch.dict(os.environ, {
        'NOTEHUB_PROJECT_UID': 'test_project_uid',
        'NOTEHUB_CLIENT_ID': 'test_client_id', 
        'NOTEHUB_CLIENT_SECRET': 'test_client_secret'
    })
    def test_connect_with_environment_variables(self, mock_notehub_project):
        """Test successful connection using environment variables."""
        mock_project = MagicMock()
        mock_notehub_project.return_value = mock_project
        
        result = manage_firmware.connectToNotehubProject()
        
        mock_notehub_project.assert_called_once_with(
            project_uid='test_project_uid',
            client_id='test_client_id',
            client_secret='test_client_secret'
        )
        self.assertEqual(result, mock_project)

    @patch('manage_firmware.NotehubProject')
    @patch.dict(os.environ, {}, clear=True)
    def test_connect_with_missing_environment_variables(self, mock_notehub_project):
        """Test connection with missing environment variables."""
        mock_project = MagicMock()
        mock_notehub_project.return_value = mock_project
        
        result = manage_firmware.connectToNotehubProject()
        
        mock_notehub_project.assert_called_once_with(
            project_uid=None,
            client_id=None,
            client_secret=None
        )
        self.assertEqual(result, mock_project)


class TestFirmwareCache(unittest.TestCase):
    """Test cases for FirmwareCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = manage_firmware.FirmwareCache()
        self.mock_project = MagicMock()
        
    def test_init(self):
        """Test FirmwareCache initialization."""
        cache = manage_firmware.FirmwareCache()
        self.assertEqual(cache.cache, {})
        self.assertEqual(cache.cache_expiry, 0)
        self.assertEqual(cache._expiration_duration_seconds, 1800)

    @patch('manage_firmware.FirmwareType')
    @patch('time.time')
    def test_update_success(self, mock_time, mock_firmware_type):
        """Test successful cache update."""
        mock_time.return_value = 1000
        mock_firmware_type.Notecard = "notecard"
        mock_firmware_type.Host = "host"
        
        # Mock firmware response
        mock_firmware_data = [
            {'type': 'notecard', 'version': '8.1.3', 'filename': 'notecard-8.1.3.bin'},
            {'type': 'host', 'version': '3.1.2', 'filename': 'host-3.1.2.bin'},
            {'type': 'notecard', 'version': '8.1.4', 'filename': 'notecard-8.1.4.bin'},
        ]
        self.mock_project.fetchAvailableFirmware.return_value = mock_firmware_data
        
        self.cache.update(self.mock_project)
        
        expected_cache = {
            'notecard': {
                '8.1.3': 'notecard-8.1.3.bin',
                '8.1.4': 'notecard-8.1.4.bin'
            },
            'host': {
                '3.1.2': 'host-3.1.2.bin'
            }
        }
        self.assertEqual(self.cache.cache, expected_cache)
        self.assertEqual(self.cache.cache_expiry, 2800)  # 1000 + 1800
        self.mock_project.fetchAvailableFirmware.assert_called_once()

    @patch('manage_firmware.FirmwareType')
    @patch('time.time')
    def test_update_with_incomplete_data(self, mock_time, mock_firmware_type):
        """Test cache update with incomplete firmware data."""
        mock_time.return_value = 1000
        mock_firmware_type.Notecard = "notecard"
        mock_firmware_type.Host = "host"
        
        # Mock firmware response with missing fields
        mock_firmware_data = [
            {'type': 'notecard', 'version': '8.1.3', 'filename': 'notecard-8.1.3.bin'},
            {'type': 'notecard', 'version': None, 'filename': 'invalid.bin'},  # Missing version
            {'type': None, 'version': '8.1.4', 'filename': 'invalid2.bin'},    # Missing type
            {'type': 'host', 'version': '3.1.2', 'filename': None},           # Missing filename
        ]
        self.mock_project.fetchAvailableFirmware.return_value = mock_firmware_data
        
        self.cache.update(self.mock_project)
        
        # Only the valid entry should be cached
        expected_cache = {
            'notecard': {'8.1.3': 'notecard-8.1.3.bin'},
            'host': {}
        }
        self.assertEqual(self.cache.cache, expected_cache)

    def test_retrieve_cache_hit(self):
        """Test successful cache retrieval."""
        # Pre-populate cache
        self.cache.cache = {
            'notecard': {'8.1.3': 'notecard-8.1.3.bin'},
            'host': {'3.1.2': 'host-3.1.2.bin'}
        }
        self.cache.cache_expiry = time.time() + 1000  # Not expired
        
        result = self.cache.retrieve(self.mock_project, 'notecard', '8.1.3')
        
        self.assertEqual(result, 'notecard-8.1.3.bin')

    def test_retrieve_cache_miss_firmware_type(self):
        """Test cache retrieval with missing firmware type."""
        self.cache.cache = {'notecard': {'8.1.3': 'notecard-8.1.3.bin'}}
        self.cache.cache_expiry = time.time() + 1000
        
        with self.assertRaises(Exception) as context:
            self.cache.retrieve(self.mock_project, 'missing_type', '8.1.3')
        
        self.assertIn("Firmware for missing_type not available", str(context.exception))

    def test_retrieve_cache_miss_version(self):
        """Test cache retrieval with missing version."""
        self.cache.cache = {
            'notecard': {'8.1.3': 'notecard-8.1.3.bin'},
            'host': {}
        }
        self.cache.cache_expiry = time.time() + 1000
        
        with self.assertRaises(Exception) as context:
            self.cache.retrieve(self.mock_project, 'notecard', '8.1.4')
        
        self.assertIn("Firmware version 8.1.4 for notecard not available", str(context.exception))

    def test_retrieve_invalid_filename(self):
        """Test cache retrieval with invalid filename."""
        self.cache.cache = {
            'notecard': {'8.1.3': ''},  # Empty filename
            'host': {'3.1.2': None}     # None filename  
        }
        self.cache.cache_expiry = time.time() + 1000
        
        with self.assertRaises(Exception) as context:
            self.cache.retrieve(self.mock_project, 'notecard', '8.1.3')
        
        self.assertIn("Invalid firmware file name for version 8.1.3 for notecard", str(context.exception))

    @patch.object(manage_firmware.FirmwareCache, 'update')
    def test_retrieve_expired_cache_triggers_update(self, mock_update):
        """Test that expired cache triggers an update."""
        self.cache.cache_expiry = time.time() - 1000  # Expired
        self.cache.cache = {
            'notecard': {'8.1.3': 'notecard-8.1.3.bin'}
        }
        
        # After mock update, set valid cache
        def side_effect(project):
            self.cache.cache = {'notecard': {'8.1.3': 'notecard-8.1.3.bin'}}
            self.cache.cache_expiry = time.time() + 1000
        
        mock_update.side_effect = side_effect
        
        result = self.cache.retrieve(self.mock_project, 'notecard', '8.1.3')
        
        mock_update.assert_called_once_with(self.mock_project)
        self.assertEqual(result, 'notecard-8.1.3.bin')



class TestFetchDeviceFirmwareInfo(unittest.TestCase):
    """Test cases for fetchDeviceFirmwareInfo function."""
    
    def test_fetch_success(self):
        """Test successful firmware info fetch."""
        mock_project = MagicMock()
        mock_project.getDeviceFirmwareUpdateHistory.return_value = {
            'current': {'version': '8.1.3.17074', 'built': '2024-01-15'}
        }
        
        result = manage_firmware.fetchDeviceFirmwareInfo(
            mock_project, 'device123', 'notecard'
        )
        
        self.assertEqual(result, {'version': '8.1.3.17074', 'built': '2024-01-15'})
        mock_project.getDeviceFirmwareUpdateHistory.assert_called_once_with('device123', 'notecard')

    def test_fetch_missing_current(self):
        """Test fetch with missing current firmware info."""
        mock_project = MagicMock()
        mock_project.getDeviceFirmwareUpdateHistory.return_value = {}
        
        result = manage_firmware.fetchDeviceFirmwareInfo(
            mock_project, 'device123', 'notecard'
        )
        
        self.assertEqual(result, {})

    def test_fetch_empty_current(self):
        """Test fetch with empty current firmware info."""
        mock_project = MagicMock()
        mock_project.getDeviceFirmwareUpdateHistory.return_value = {
            'current': {}
        }
        
        result = manage_firmware.fetchDeviceFirmwareInfo(
            mock_project, 'device123', 'notecard'
        )
        
        self.assertEqual(result, {})


class TestRequestUpdateToTargetVersion(unittest.TestCase):
    """Test cases for requestUpdateToTargetVersion function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_project = MagicMock()
        # Mock the global firmwareCache
        self.patcher = patch.object(manage_firmware, 'firmwareCache')
        self.mock_cache = self.patcher.start()
        
    def tearDown(self):
        """Clean up patches."""
        self.patcher.stop()

    def test_no_firmware_update_needed(self):
        """Test when no firmware update is specified."""
        target_versions = {}  # No firmware type specified
        
        result = manage_firmware.requestUpdateToTargetVersion(
            self.mock_project, 'device123', '8.1.3', target_versions, 'notecard'
        )
        
        self.assertEqual(result, "No firmware update request for notecard")
        self.mock_project.requestDeviceFirmwareUpdate.assert_not_called()

    def test_already_at_target_version(self):
        """Test when device is already at target version."""
        target_versions = {'notecard': '8.1.3'}
        current_version = '8.1.3'
        
        result = manage_firmware.requestUpdateToTargetVersion(
            self.mock_project, 'device123', current_version, target_versions, 'notecard'
        )
        
        self.assertEqual(result, "Skipping update request for notecard. Already at target version of 8.1.3.")
        self.mock_project.requestDeviceFirmwareUpdate.assert_not_called()

    def test_successful_update_request(self):
        """Test successful firmware update request."""
        target_versions = {'notecard': '8.1.4'}
        current_version = '8.1.3'
        
        # Mock cache retrieval
        self.mock_cache.retrieve.return_value = 'notecard-8.1.4.bin'
        
        result = manage_firmware.requestUpdateToTargetVersion(
            self.mock_project, 'device123', current_version, target_versions, 'notecard'
        )
        
        self.assertEqual(result, "Requested notecard firmware update from 8.1.3 to 8.1.4.")
        self.mock_cache.retrieve.assert_called_once_with(self.mock_project, 'notecard', '8.1.4')
        self.mock_project.requestDeviceFirmwareUpdate.assert_called_once_with(
            'device123', 'notecard-8.1.4.bin', 'notecard'
        )

    def test_cache_retrieval_failure(self):
        """Test when cache retrieval fails."""
        target_versions = {'notecard': '8.1.4'}
        current_version = '8.1.3'
        
        # Mock cache retrieval to raise exception
        self.mock_cache.retrieve.side_effect = Exception("Version not found")
        
        with self.assertRaises(Exception):
            manage_firmware.requestUpdateToTargetVersion(
                self.mock_project, 'device123', current_version, target_versions, 'notecard'
            )

    def test_invalid_cache_file(self):
        """Test when cache returns None for file."""
        target_versions = {'notecard': '8.1.4'}
        current_version = '8.1.3'
        
        # Mock cache to return None
        self.mock_cache.retrieve.return_value = None
        
        with self.assertRaises(Exception) as context:
            manage_firmware.requestUpdateToTargetVersion(
                self.mock_project, 'device123', current_version, target_versions, 'notecard'
            )
        
        self.assertIn("Unable to locate notecard firmware image", str(context.exception))


class TestManageFirmware(unittest.TestCase):
    """Test cases for manageFirmware function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_project = MagicMock()
        
    def test_no_rule_conditions_met(self):
        """Test when no rule conditions are met."""
        # Use empty rules which will result in no conditions met
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, []
        )
        
        self.assertEqual(result, "No rule conditions met. No updates required")

    def test_rule_met_no_updates_required(self):
        """Test when rule is met but no updates required."""
        # Create a rule that matches but has no target versions
        rules = [{"id": "rule-1", "conditions": None, "target_versions": None}]
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules
        )
        
        self.assertEqual(result, "According to rule id rule-1, firmware requirements met, no updates required")

    def test_fetch_missing_firmware_versions(self):
        """Test fetching missing firmware versions."""
        # Mock the project methods that will be called
        self.mock_project.getDeviceFirmwareUpdateHistory.side_effect = [
            {'current': {'version': '8.1.3'}},  # notecard version
            {'current': {'version': '3.1.2'}}   # host version  
        ]
        
        # Call manageFirmware with device_data missing firmware info to trigger fetching
        device_data = {'fleets': ['fleet123']}  # Missing firmware info
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, {}
        )
        
        # Should have called getDeviceFirmwareUpdateHistory twice
        self.assertEqual(self.mock_project.getDeviceFirmwareUpdateHistory.call_count, 2)
        
        # Verify it was called with correct parameters
        expected_calls = [
            call('device123', 'notecard'),
            call('device123', 'host')
        ]
        self.mock_project.getDeviceFirmwareUpdateHistory.assert_has_calls(expected_calls, any_order=True)

    def test_notecard_update_in_progress(self):
        """Test when notecard update is already in progress."""
        # Create a rule that would trigger updates
        rules = [{"id": "rule-1", "conditions": None, "target_versions": {"notecard": "8.1.4"}}]
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        
        # Mock notecard update in progress
        self.mock_project.getDeviceFirmwareUpdateStatus.return_value = {
            'dfu_in_progress': True
        }
        
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules
        )
        
        self.assertEqual(
            result, 
            "According to rule id rule-1, firmware requirements NOT met.  Update not requested because Notecard update is in progress"
        )
        self.mock_project.getDeviceFirmwareUpdateStatus.assert_called_once_with('device123', 'notecard')

    def test_host_update_in_progress(self):
        """Test when host update is already in progress."""
        # Create a rule that would trigger host updates
        rules = [{"id": "rule-1", "conditions": None, "target_versions": {"host": "3.1.3"}}]
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        
        # Mock no notecard update in progress, but host update in progress
        self.mock_project.getDeviceFirmwareUpdateStatus.side_effect = [
            {'dfu_in_progress': False},  # Notecard not in progress
            {'dfu_in_progress': True}    # Host in progress
        ]
        
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules
        )
        
        self.assertEqual(
            result,
            "According to rule id rule-1, firmware requirements NOT met.  Update not requested because Host update is in progress"
        )
        self.assertEqual(self.mock_project.getDeviceFirmwareUpdateStatus.call_count, 2)

    def test_successful_firmware_updates(self):
        """Test successful firmware update requests."""
        # Create a rule that would trigger both updates
        rules = [{"id": "rule-1", "conditions": None, "target_versions": {"notecard": "8.1.4", "host": "3.1.3"}}]
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        
        # Mock no updates in progress
        self.mock_project.getDeviceFirmwareUpdateStatus.return_value = {'dfu_in_progress': False}
        
        # Mock the cache retrieval to return valid firmware files
        manage_firmware.firmwareCache.cache = {
            'notecard': {'8.1.4': 'notecard-8.1.4.bin'},
            'host': {'3.1.3': 'host-3.1.3.bin'}
        }
        manage_firmware.firmwareCache.cache_expiry = time.time() + 1000
        
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules
        )
        
        expected_result = ("According to rule id rule-1, "
                          "Requested notecard firmware update from 8.1.3 to 8.1.4. "
                          "Requested host firmware update from 3.1.2 to 3.1.3.")
        self.assertEqual(result, expected_result)
        
        # Verify requestDeviceFirmwareUpdate was called for both firmware types
        self.assertEqual(self.mock_project.requestDeviceFirmwareUpdate.call_count, 2)


if __name__ == '__main__':
    unittest.main()