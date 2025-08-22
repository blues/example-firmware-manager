"""
Unit tests for the firmware update targets functionality.

This test suite validates the getFirmwareUpdateTargets function from manage_firmware module,
testing rule matching, precedence, and target version handling.

Converted from pytest format to unittest format for compatibility with run_tests.py.
"""

import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the parent directory to the path so we can import rules_engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules_engine import getFirmwareUpdateTargets


class TestFirmwareUpdateTargets(unittest.TestCase):
    """Test cases for the getFirmwareUpdateTargets function."""

    def test_rule_ids(self):
        """Test that rule IDs are properly handled and auto-generated when missing."""
        rules = [
            {"id": "my-id", "conditions": {"fleet": "my-fleet-1"}}, 
            {"conditions": {"fleet": "my-fleet-2"}}
        ]

        r, _ = getFirmwareUpdateTargets("my-fleet-1", None, None, rules=rules)
        self.assertEqual(r, "my-id")

        r, _ = getFirmwareUpdateTargets("my-fleet-2", None, None, rules=rules)
        self.assertEqual(r, "rule-2")

    def test_rules_all_none(self):
        """Test behavior when all conditions and target versions are None."""
        rules = {"id": "my-rule", "conditions": None, "targetVersions": None}

        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=None, rules=rules)
        
        self.assertIsNone(v)

    def test_rules_notecard_rule_string(self):
        """Test notecard rules with string conditions and various target version formats."""
        currentVersion = "notecard_version_info"
        targetVersion = "new_notecard_version"
        rules = {"conditions": {"notecard": currentVersion}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)
        self.assertEqual(v, targetVersion)

        # Test with None target version
        targetVersion = None
        rules = {"conditions": {"notecard": currentVersion}, "targetVersions": targetVersion}
        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)
        self.assertIsNone(v)

        # Test with dict target version - notecard
        targetVersion = "new_notecard_version"
        rules = {"conditions": {"notecard": currentVersion}, "targetVersions": {"notecard": targetVersion}}
        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)
        self.assertEqual(v.get("notecard"), targetVersion)

        # Test with dict target version - host
        targetVersion = "new_host_version"
        rules = {"conditions": {"notecard": currentVersion}, "targetVersions": {"host": targetVersion}}
        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)
        self.assertEqual(v.get("host"), targetVersion)
        self.assertIsNone(v.get("notecard"))

    def test_rules_host_rule_string(self):
        """Test host rules with string conditions and various target version formats."""
        currentVersion = "host_version_info"
        targetVersion = "new_host_version"
        rules = {"conditions": {"host": currentVersion}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)
        self.assertEqual(v, targetVersion)

        # Test with None target version
        targetVersion = None
        rules = {"conditions": {"host": currentVersion}, "targetVersions": targetVersion}
        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)
        self.assertIsNone(v)

        # Test with dict target version - host
        targetVersion = "new_host_version"
        rules = {"conditions": {"host": currentVersion}, "targetVersions": {"host": targetVersion}}
        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)
        self.assertEqual(v.get("host"), targetVersion)

        # Test with dict target version - notecard
        targetVersion = "new_notecard_version"
        rules = {"conditions": {"host": currentVersion}, "targetVersions": {"notecard": targetVersion}}
        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)
        self.assertEqual(v.get("notecard"), targetVersion)
        self.assertIsNone(v.get("host"))

    def test_rules_notecard_host_fleet_rule_string(self):
        """Test complex rules with notecard, host, and fleet conditions."""
        currentHostVersion = "host_version_info"
        currentNotecardVersion = "notecard_version_info"
        fleetUID = "my-fleet-uid"
        targetVersion = "test-target-version"
        rules = {
            "conditions": {
                "host": currentHostVersion,
                "notecard": currentNotecardVersion,
                "fleet": fleetUID
            }, 
            "targetVersions": targetVersion
        }

        # All conditions match
        _, v = getFirmwareUpdateTargets(
            fleetUID=fleetUID, 
            notecardVersion=currentNotecardVersion, 
            hostVersion=currentHostVersion, 
            rules=rules
        )
        self.assertEqual(v, targetVersion)

        # Fleet UID different
        _, v = getFirmwareUpdateTargets(
            fleetUID=fleetUID + "-is-different", 
            notecardVersion=currentNotecardVersion, 
            hostVersion=currentHostVersion, 
            rules=rules
        )
        self.assertIsNone(v)

        # Notecard version different
        _, v = getFirmwareUpdateTargets(
            fleetUID=fleetUID, 
            notecardVersion=currentNotecardVersion + "-is-different", 
            hostVersion=currentHostVersion, 
            rules=rules
        )
        self.assertIsNone(v)

        # Host version different
        _, v = getFirmwareUpdateTargets(
            fleetUID=fleetUID, 
            notecardVersion=currentNotecardVersion, 
            hostVersion=currentHostVersion + "-is-different", 
            rules=rules
        )
        self.assertIsNone(v)

    def test_rules_notecard_rule_is_function_returning_true(self):
        """Test notecard rule with function condition that returns True."""
        c = MagicMock()
        c.return_value = True

        currentVersion = "notecard_version_info"
        targetVersion = "test-target-version"
        rules = {"conditions": {"notecard": c}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)
        
        self.assertEqual(v, targetVersion)
        c.assert_called_once_with(currentVersion)

    def test_rules_notecard_rule_is_function_returning_false(self):
        """Test notecard rule with function condition that returns False."""
        c = MagicMock()
        c.return_value = False

        currentVersion = "notecard_version_info"
        targetVersion = "test-target-version"
        rules = {"conditions": {"notecard": c}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=currentVersion, hostVersion=None, rules=rules)
        
        self.assertIsNone(v)
        c.assert_called_once_with(currentVersion)

    def test_rules_host_rule_is_function_returning_true(self):
        """Test host rule with function condition that returns True."""
        c = MagicMock()
        c.return_value = True

        currentVersion = "host_version_info"
        targetVersion = "test-target-version"
        rules = {"conditions": {"host": c}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)
        
        self.assertEqual(v, targetVersion)
        c.assert_called_once_with(currentVersion)

    def test_rules_host_rule_is_function_returning_false(self):
        """Test host rule with function condition that returns False."""
        c = MagicMock()
        c.return_value = False

        currentVersion = "host_version_info"
        targetVersion = "test-target-version"
        rules = {"conditions": {"host": c}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=None, notecardVersion=None, hostVersion=currentVersion, rules=rules)
        
        self.assertIsNone(v)
        c.assert_called_once_with(currentVersion)

    def test_rules_fleet_rule_is_function_returning_true(self):
        """Test fleet rule with function condition that returns True."""
        c = MagicMock()
        c.return_value = True

        fleetUID = "my-fleet-uid"
        targetVersion = "test-target-version"
        rules = {"conditions": {"fleet": c}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=None, hostVersion=None, rules=rules)
        
        self.assertEqual(v, targetVersion)
        c.assert_called_once_with(fleetUID)

    def test_rules_fleet_rule_is_function_returning_false(self):
        """Test fleet rule with function condition that returns False."""
        c = MagicMock()
        c.return_value = False

        fleetUID = "my-fleet-uid"
        targetVersion = "test-target-version"
        rules = {"conditions": {"fleet": c}, "targetVersions": targetVersion}

        _, v = getFirmwareUpdateTargets(fleetUID=fleetUID, notecardVersion=None, hostVersion=None, rules=rules)
        
        self.assertIsNone(v)
        c.assert_called_once_with(fleetUID)

    def test_rules_precedence(self):
        """Test that rules are processed in order of precedence (first match wins)."""
        ncTarget = "notecard-target-version"
        hostTarget = "host-target-version"

        fleetUID = "my-fleet-uid"
        desiredNotecardVersion = "desired-notecard-version"
        desiredHostVersion = "desired-host-version"
        
        rules = [
            {
                "conditions": {
                    "fleet": fleetUID, 
                    "notecard": desiredNotecardVersion, 
                    "host": desiredHostVersion
                },
                "targetVersions": None,
                "id": "have-desired-versions"
            },
            {
                "conditions": {
                    "fleet": fleetUID, 
                    "notecard": "un" + desiredNotecardVersion, 
                    "host": desiredHostVersion
                },
                "targetVersions": ncTarget,
                "id": "correct-host-incorrect-notecard"
            },
            {
                "conditions": {
                    "fleet": fleetUID
                },
                "targetVersions": hostTarget,
                "id": "all-remaining-options"
            }
        ]

        # Test fallback to third rule
        r, v = getFirmwareUpdateTargets(
            fleetUID=fleetUID, 
            notecardVersion="un" + desiredNotecardVersion, 
            hostVersion="un" + desiredHostVersion, 
            rules=rules
        )
        self.assertEqual(v, hostTarget)
        self.assertEqual(r, "all-remaining-options")

        # Test second rule match
        r, v = getFirmwareUpdateTargets(
            fleetUID=fleetUID, 
            notecardVersion="un" + desiredNotecardVersion, 
            hostVersion=desiredHostVersion, 
            rules=rules
        )
        self.assertEqual(v, ncTarget)
        self.assertEqual(r, "correct-host-incorrect-notecard")

        # Test first rule match (highest precedence)
        r, v = getFirmwareUpdateTargets(
            fleetUID=fleetUID, 
            notecardVersion=desiredNotecardVersion, 
            hostVersion=desiredHostVersion, 
            rules=rules
        )
        self.assertIsNone(v)
        self.assertEqual(r, "have-desired-versions")


if __name__ == '__main__':
    unittest.main()