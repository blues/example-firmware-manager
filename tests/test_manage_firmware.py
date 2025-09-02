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

    def test_firmware_cache_retrieve_invalid_filename_empty_string(self):
        """Test FirmwareCache.retrieve raises exception for empty filename string."""
        self.cache.cache = {manage_firmware.FirmwareType.Notecard: {"1.0.0": ""}}  
        self.cache.cache_expiry = time.time() + 1000
        
        with self.assertRaises(Exception) as context:
            self.cache.retrieve(self.mock_project, manage_firmware.FirmwareType.Notecard, "1.0.0")
        
        self.assertIn("Invalid firmware file name", str(context.exception))

    def test_firmware_cache_retrieve_invalid_filename_non_string(self):
        """Test FirmwareCache.retrieve raises exception for non-string filename."""
        self.cache.cache = {manage_firmware.FirmwareType.Notecard: {"1.0.0": None}}  
        self.cache.cache_expiry = time.time() + 1000
        
        with self.assertRaises(Exception) as context:
            self.cache.retrieve(self.mock_project, manage_firmware.FirmwareType.Notecard, "1.0.0")
        
        self.assertIn("Invalid firmware file name", str(context.exception))

    def test_firmware_cache_retrieve_empty_versions_list(self):
        """Test FirmwareCache.retrieve raises exception when firmware type exists but has no versions."""
        # Set up cache with firmware type present but empty versions dict
        self.cache.cache = {manage_firmware.FirmwareType.Notecard: {}}  # Empty versions
        self.cache.cache_expiry = time.time() + 1000  # Don't expire
        
        with self.assertRaises(Exception) as context:
            self.cache.retrieve(self.mock_project, manage_firmware.FirmwareType.Notecard, "8.1.3")
        
        # Verify the specific error message for empty versions list
        error_message = str(context.exception)
        self.assertIn("Firmware version 8.1.3 for notecard not available in local firmware cache", error_message)
        self.assertIn("No firmware versions found for notecard", error_message) 
        self.assertIn("Please upload firmware to your Notehub project", error_message)
        
        # Verify it's the "no versions found" message, not the "available versions" message
        self.assertNotIn("Available versions:", error_message)



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


class TestCheckUpdateToTargetVersion(unittest.TestCase):
    """Test cases for checkUpdateToTargetVersion function."""
    
    def setUp(self):
        self.mock_project = MagicMock()
    
    def test_check_update_firmware_cache_exception(self):
        """Test checkUpdateToTargetVersion handles firmwareCache.retrieve exceptions."""
        with patch.object(manage_firmware.firmwareCache, 'retrieve') as mock_retrieve:
            mock_retrieve.side_effect = Exception("Cache retrieval failed")
            
            target_versions = {manage_firmware.FirmwareType.Notecard: "2.0.0"}
            
            should_update, message, target_version, filename = manage_firmware.checkUpdateToTargetVersion(
                self.mock_project, 
                'device123', 
                '1.0.0',  # current version
                target_versions, 
                manage_firmware.FirmwareType.Notecard
            )
            
            self.assertFalse(should_update)
            self.assertIn("Cannot update", message)
            self.assertIn("Cache retrieval failed", message)
            self.assertEqual(target_version, "2.0.0")
            self.assertIsNone(filename)
    
    def test_check_update_firmware_cache_returns_none(self):
        """Test checkUpdateToTargetVersion handles when firmwareCache.retrieve returns None."""
        with patch.object(manage_firmware.firmwareCache, 'retrieve') as mock_retrieve:
            mock_retrieve.return_value = None  # Return None instead of filename
            
            target_versions = {manage_firmware.FirmwareType.Notecard: "2.0.0"}
            
            should_update, message, target_version, filename = manage_firmware.checkUpdateToTargetVersion(
                self.mock_project, 
                'device123', 
                '1.0.0',  # current version
                target_versions, 
                manage_firmware.FirmwareType.Notecard
            )
            
            self.assertFalse(should_update)
            self.assertIn("Cannot update", message)
            self.assertIn("Unable to locate", message)
            self.assertEqual(target_version, "2.0.0")
            self.assertIsNone(filename)


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
    
    def test_dry_run_no_rule_conditions_met(self):
        """Test dry-run mode when no rule conditions are met."""
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, [], is_dry_run=True
        )
        
        self.assertEqual(result, "Dry-Run: No rule conditions met. No updates required")
        
    def test_dry_run_rule_met_no_updates_required(self):
        """Test dry-run mode when rule is met but no updates required."""
        rules = [{"id": "rule-1", "conditions": None, "target_versions": None}]
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules, is_dry_run=True
        )
        
        self.assertEqual(result, "Dry-Run: According to rule id rule-1, firmware requirements met, no updates required")
    
    def test_dry_run_notecard_update_in_progress(self):
        """Test dry-run mode when notecard update is already in progress."""
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
            self.mock_project, 'device123', device_data, rules, is_dry_run=True
        )
        
        self.assertEqual(
            result, 
            "Dry-Run: According to rule id rule-1, firmware requirements NOT met.  Update not requested because Notecard update is in progress"
        )
        self.mock_project.getDeviceFirmwareUpdateStatus.assert_called_once_with('device123', 'notecard')
    
    def test_dry_run_successful_firmware_updates(self):
        """Test dry-run mode for successful firmware update checks."""
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
            self.mock_project, 'device123', device_data, rules, is_dry_run=True
        )
        
        expected_result = ("Dry-Run: According to rule id rule-1, "
                          "Would request notecard firmware update from 8.1.3 to 8.1.4. "
                          "Would request host firmware update from 3.1.2 to 3.1.3.")
        self.assertEqual(result, expected_result)
        
        # Verify requestDeviceFirmwareUpdate was NOT called in dry-run mode
        self.mock_project.requestDeviceFirmwareUpdate.assert_not_called()
    
    def test_dry_run_already_at_target_version(self):
        """Test dry-run mode when device is already at target version."""
        rules = [{"id": "rule-1", "conditions": None, "target_versions": {"notecard": "8.1.3", "host": "3.1.2"}}]
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},  # Already at target
            'firmware_host': {'version': '3.1.2'}       # Already at target
        }
        
        # Mock no updates in progress
        self.mock_project.getDeviceFirmwareUpdateStatus.return_value = {'dfu_in_progress': False}
        
        result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules, is_dry_run=True
        )
        
        expected_result = ("Dry-Run: According to rule id rule-1, "
                          "Skipping update request for notecard. Already at target version of 8.1.3. "
                          "Skipping update request for host. Already at target version of 3.1.2.")
        self.assertEqual(result, expected_result)
        
        # Verify requestDeviceFirmwareUpdate was NOT called
        self.mock_project.requestDeviceFirmwareUpdate.assert_not_called()
    
    def test_normal_vs_dry_run_comparison(self):
        """Test that normal and dry-run modes behave differently for the same scenario."""
        rules = [{"id": "rule-1", "conditions": None, "target_versions": {"notecard": "8.1.4"}}]
        device_data = {
            'fleets': ['fleet123'],
            'firmware_notecard': {'version': '8.1.3'},
            'firmware_host': {'version': '3.1.2'}
        }
        
        # Mock no updates in progress
        self.mock_project.getDeviceFirmwareUpdateStatus.return_value = {'dfu_in_progress': False}
        
        # Mock the cache retrieval
        manage_firmware.firmwareCache.cache = {
            'notecard': {'8.1.4': 'notecard-8.1.4.bin'},
            'host': {}
        }
        manage_firmware.firmwareCache.cache_expiry = time.time() + 1000
        
        # Test dry-run mode
        dry_run_result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules, is_dry_run=True
        )
        
        # Reset the mock
        self.mock_project.reset_mock()
        self.mock_project.getDeviceFirmwareUpdateStatus.return_value = {'dfu_in_progress': False}
        
        # Test normal mode  
        normal_result = manage_firmware.manageFirmware(
            self.mock_project, 'device123', device_data, rules, is_dry_run=False
        )
        
        # Check that dry-run has prefix and "Would request"
        self.assertTrue(dry_run_result.startswith("Dry-Run:"))
        self.assertIn("Would request", dry_run_result)
        
        # Check that normal mode doesn't have prefix and has "Requested"
        self.assertFalse(normal_result.startswith("Dry-Run:"))
        self.assertIn("Requested", normal_result)
        
        # Verify that in normal mode, requestDeviceFirmwareUpdate was called
        self.mock_project.requestDeviceFirmwareUpdate.assert_called_once()


if __name__ == '__main__':
    unittest.main()