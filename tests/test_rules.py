"""
Unit tests for the default rules defined in rules.py.

This test suite validates that the default rule sets (DEFAULT_RULES and DevicesInUpdateFleet)
function correctly with the rules_engine, testing various device scenarios and expected
firmware update behaviors.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules_engine import getFirmwareUpdateTargets
import rules


def create_firmware_data_with_version(version_string):
    """
    Create firmware data with both version string and parsed version fields.
    
    Args:
        version_string (str): Version string like "7.5.1.12345"
        
    Returns:
        dict: Firmware data with version fields
    """
    parts = version_string.split(".")
    firmware_data = {"version": version_string}
    
    if len(parts) >= 1:
        firmware_data["ver_major"] = int(parts[0])
    if len(parts) >= 2:
        firmware_data["ver_minor"] = int(parts[1])
    if len(parts) >= 3:
        firmware_data["ver_patch"] = int(parts[2])
    if len(parts) >= 4:
        firmware_data["ver_build"] = int(parts[3])
        
    return firmware_data


class TestDefaultRules(unittest.TestCase):
    """Test cases for DEFAULT_RULES from rules.py."""
    
    def test_default_rules_always_match(self):
        """Test that DEFAULT_RULES always match and return no updates."""
        # Test with various device data configurations
        test_cases = [
            {},  # Empty device data
            {"firmware_notecard": create_firmware_data_with_version("8.1.3")},  # Only notecard
            {"firmware_host": create_firmware_data_with_version("3.1.2")},  # Only host
            {"fleets": ["fleet:production"]},  # Only fleet
            {  # Complete device data
                "firmware_notecard": create_firmware_data_with_version("8.1.3"),
                "firmware_host": create_firmware_data_with_version("3.1.2"), 
                "fleets": ["fleet:production"]
            }
        ]
        
        for device_data in test_cases:
            with self.subTest(device_data=device_data):
                rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DEFAULT_RULES)
                
                self.assertEqual(rule_id, "default")
                self.assertIsNone(target_versions)


class TestDevicesInUpdateFleetRules(unittest.TestCase):
    """Test cases for DevicesInUpdateFleet rules from rules.py."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_fleet = "fleet:50b4f0ee-b8e4-4c9c-b321-243ff1f9e487"
    
    def test_rule_1_7_5_1_version_match(self):
        """Test Rule 1: Updates firmware version starting with '7.5.1.' to '7.5.2.17004'."""
        test_versions = [
            "7.5.1.1",
            "7.5.1.12345", 
            "7.5.1.99999",
            "7.5.1.17001"
        ]
        
        for version in test_versions:
            with self.subTest(version=version):
                device_data = {
                    "firmware_notecard": create_firmware_data_with_version(version)
                }
                
                rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
                
                self.assertIsNotNone(rule_id)
                self.assertEqual(target_versions["notecard"], "7.5.2.17004")
    
    def test_rule_1_7_5_1_version_no_match(self):
        """Test Rule 1: Versions that don't start with '7.5.1.' should not match this rule."""
        test_versions = [
            "7.5.0.1",  # Different minor/patch
            "7.5.2.1",  # Different patch
            "7.4.1.1",  # Different minor
            "8.5.1.1",  # Different major
            "6.5.1.1",  # Different major
            "17.5.1.1"  # Different major
        ]
        
        for version in test_versions:
            with self.subTest(version=version):
                device_data = {
                    "firmware_notecard": create_firmware_data_with_version(version),
                    "fleets": ["some-other-fleet"]  # Make sure it doesn't match rule 2
                }
                
                rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
                
                # Should not match any rule
                self.assertIsNone(rule_id)
                self.assertIsNone(target_versions)
    
    def test_rule_2_major_version_less_than_8_with_fleet(self):
        """Test Rule 2: Major version < 8 AND in specific fleet updates to '8.1.3.17044'."""
        test_versions = [
            "7.9.9.99999",  # Major version 7
            "6.1.1.1",      # Major version 6  
            "5.0.0.0",      # Major version 5
            "1.0.0.0",      # Major version 1
            "0.9.9.9"       # Major version 0
        ]
        
        for version in test_versions:
            with self.subTest(version=version):
                device_data = {
                    "firmware_notecard": create_firmware_data_with_version(version),
                    "fleets": [self.test_fleet]
                }
                
                rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
                
                self.assertIsNotNone(rule_id)
                self.assertEqual(target_versions["notecard"], "8.1.3.17044")
    
    def test_rule_2_major_version_8_or_higher_no_match(self):
        """Test Rule 2: Major version >= 8 should not match even with correct fleet."""
        test_versions = [
            "8.0.0.0",      # Major version 8
            "8.1.3.17044",  # Exact target version
            "9.0.0.0",      # Major version 9
            "10.1.1.1"      # Major version 10
        ]
        
        for version in test_versions:
            with self.subTest(version=version):
                device_data = {
                    "firmware_notecard": create_firmware_data_with_version(version),
                    "fleets": [self.test_fleet]
                }
                
                rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
                
                # Should not match any rule
                self.assertIsNone(rule_id)
                self.assertIsNone(target_versions)
    
    def test_rule_2_wrong_fleet_no_match(self):
        """Test Rule 2: Major version < 8 but wrong fleet should not match."""
        device_data = {
            "firmware_notecard": create_firmware_data_with_version("7.5.4.123"),
            "fleets": ["fleet:different-fleet-id"]
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
        
        # Should not match any rule
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)
    
    def test_rule_2_no_fleet_no_match(self):
        """Test Rule 2: Major version < 8 but no fleet should not match."""
        device_data = {
            "firmware_notecard": create_firmware_data_with_version("7.5.4.123")
            # Missing fleets field
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
        
        # Should not match any rule
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)
    
    def test_rule_precedence_7_5_1_beats_major_version_rule(self):
        """Test that Rule 1 (7.5.1.*) takes precedence over Rule 2 (major < 8) when both match."""
        device_data = {
            "firmware_notecard": {"ver_major": 7,"ver_minor":5, "ver_patch":1,"ver_build":12345},
            "fleets": [self.test_fleet]  # Matches rule 2
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
        
        # Should match Rule 1 first (higher precedence)
        self.assertIsNotNone(rule_id)
        self.assertEqual(target_versions["notecard"], "7.5.2.17004")  # Rule 1 target
        self.assertNotEqual(target_versions["notecard"], "8.1.3.17044")  # Not Rule 2 target
    
    def test_multiple_fleets_rule_2_match(self):
        """Test Rule 2: Device in multiple fleets including the target fleet."""
        device_data = {
            "firmware_notecard": {"ver_major": 7,"ver_minor":9, "ver_patch":9,"ver_build":999},
            "fleets": ["fleet:production", self.test_fleet, "fleet:testing"]
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
        
        self.assertIsNotNone(rule_id)
        self.assertEqual(target_versions["notecard"], "8.1.3.17044")
    
    def test_helper_functions(self):
        """Test the helper functions used in rules."""
        # Test majorVersion function
        self.assertEqual(rules.majorVersion("8.1.3.17044"), 8)
        self.assertEqual(rules.majorVersion("7.5.1.12345"), 7)
        self.assertEqual(rules.majorVersion("10.0.0.1"), 10)
        
        # Test minorVersion function  
        self.assertEqual(rules.minorVersion("8.1.3.17044"), 1)
        self.assertEqual(rules.minorVersion("7.5.1.12345"), 5)
        self.assertEqual(rules.minorVersion("10.2.0.1"), 2)
        
        # Test fleetsContain function
        fleet_checker = rules.fleetsContain("fleet:test")
        self.assertTrue(fleet_checker(["fleet:test"]))
        self.assertTrue(fleet_checker(["fleet:other", "fleet:test", "fleet:more"]))
        self.assertFalse(fleet_checker(["fleet:other", "fleet:different"]))
        self.assertFalse(fleet_checker([]))
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Missing firmware_notecard field
        device_data = {"fleets": [self.test_fleet]}
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)
        
        # firmware_notecard exists but version is missing
        device_data = {
            "firmware_notecard": {"built": "2024-01-15"},  # No version field
            "fleets": [self.test_fleet]
        }
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)
        
        # Empty fleets list
        device_data = {
            "firmware_notecard": {"ver_major": 7,"ver_minor":5, "ver_patch":1,"ver_build":123},
            "fleets": []
        }
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules.DevicesInUpdateFleet)
        # Should still match Rule 1 (doesn't require fleet)
        self.assertIsNotNone(rule_id)
        self.assertEqual(target_versions["notecard"], "7.5.2.17004")


class TestRulesIntegration(unittest.TestCase):
    """Integration tests combining multiple rule sets."""
    
    def test_rules_py_imports_work(self):
        """Test that all imports from rules.py work correctly."""
        # Test that we can import and use all rule sets
        self.assertIsNotNone(rules.DEFAULT_RULES)
        self.assertIsNotNone(rules.DevicesInUpdateFleet)
        self.assertIsNotNone(rules.majorVersion)
        self.assertIsNotNone(rules.minorVersion)
        self.assertIsNotNone(rules.fleetsContain)
        
        # Test that rules have expected structure
        self.assertIsInstance(rules.DEFAULT_RULES, list)
        self.assertIsInstance(rules.DevicesInUpdateFleet, list)
        self.assertEqual(len(rules.DEFAULT_RULES), 1)
        self.assertEqual(len(rules.DevicesInUpdateFleet), 2)


if __name__ == '__main__':
    unittest.main()