"""
Unit tests for the rules engine functionality.

This test suite validates the getFirmwareUpdateTargets function from rules_engine module,
testing generic rule matching with arbitrary field names, precedence, and target version handling.
"""

import unittest
from unittest.mock import MagicMock
import sys
import os

# Add the parent directory to the path so we can import rules_engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules_engine import getFirmwareUpdateTargets


class TestFirmwareUpdateTargets(unittest.TestCase):
    """Test cases for the getFirmwareUpdateTargets function with arbitrary fields."""

    def test_no_conditions_always_matches(self):
        """Test that rules with no conditions always match."""
        rules = {"id": "always-match", "conditions": None, "target_versions": "update-available"}
        
        rule_id, target_versions = getFirmwareUpdateTargets({}, rules=rules)
        
        self.assertEqual(rule_id, "always-match")
        self.assertEqual(target_versions, "update-available")

    def test_rule_id_auto_generation(self):
        """Test that rule IDs are auto-generated when missing."""
        rules = [
            {"id": "custom-id", "conditions": {"field1": "value1"}}, 
            {"conditions": {"field2": "value2"}},
            {"conditions": {"field3": "value3"}}
        ]

        rule_id, _ = getFirmwareUpdateTargets({"field1": "value1"}, rules=rules)
        self.assertEqual(rule_id, "custom-id")

        rule_id, _ = getFirmwareUpdateTargets({"field2": "value2"}, rules=rules)
        self.assertEqual(rule_id, "rule-2")
        
        rule_id, _ = getFirmwareUpdateTargets({"field3": "value3"}, rules=rules)
        self.assertEqual(rule_id, "rule-3")

    def test_arbitrary_field_string_conditions(self):
        """Test string conditions work with arbitrary field names."""
        device_data = {
            "notecard": "8.1.3",
            "host": "3.1.2", 
            "fleet": "production",
            "deviceType": "sensor",
            "location": "outdoor",
            "environment": "harsh"
        }
        
        # Test single field condition
        rules = {"conditions": {"deviceType": "sensor"}, "target_versions": {"notecard": "8.1.4"}}
        _, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(target_versions["notecard"], "8.1.4")
        
        # Test multiple field conditions
        rules = {
            "conditions": {"deviceType": "sensor", "location": "outdoor", "environment": "harsh"}, 
            "target_versions": {"host": "3.1.3"}
        }
        _, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(target_versions["host"], "3.1.3")

    def test_condition_mismatch(self):
        """Test that mismatched conditions prevent rule from matching."""
        device_data = {"deviceType": "gateway", "location": "indoor"}
        
        rules = {
            "conditions": {"deviceType": "sensor", "location": "outdoor"}, 
            "target_versions": "should-not-match"
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)

    def test_missing_device_fields(self):
        """Test behavior when device data is missing fields referenced in conditions."""
        device_data = {"field1": "value1"}  # Missing field2
        
        rules = {"conditions": {"field1": "value1", "field2": "value2"}, "target_versions": "update"}
        
        # Should not match because field2 is missing (None != "value2")
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)

    def test_callable_conditions(self):
        """Test that callable conditions work with arbitrary fields."""
        device_data = {
            "version": "1.2.3",
            "temperature": 25.5,
            "batteryLevel": 85
        }
        
        rules = [
            {
                "id": "version-check",
                "conditions": {
                    "version": lambda v: v and v.startswith("1.2"),
                    "temperature": lambda t: t and t > 20,
                    "batteryLevel": lambda b: b and b > 80
                },
                "target_versions": {"firmware": "1.2.4"}
            }
        ]
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "version-check")
        self.assertEqual(target_versions["firmware"], "1.2.4")

    def test_callable_condition_returns_false(self):
        """Test that callable conditions returning false prevent matching."""
        device_data = {"batteryLevel": 15}
        
        rules = {
            "conditions": {"batteryLevel": lambda b: b and b > 50},
            "target_versions": "should-not-match"
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)

    def test_mixed_condition_types(self):
        """Test mixing string and callable conditions."""
        device_data = {
            "deviceType": "sensor",
            "firmware": "2.1.0",
            "signalStrength": -65
        }
        
        rules = {
            "id": "mixed-conditions",
            "conditions": {
                "deviceType": "sensor",  # String condition
                "firmware": lambda v: v and v.startswith("2."),  # Callable condition
                "signalStrength": lambda s: s and s > -70  # Callable condition
            },
            "target_versions": {"firmware": "2.1.1"}
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "mixed-conditions")
        self.assertEqual(target_versions["firmware"], "2.1.1")

    def test_rule_precedence(self):
        """Test that rules are processed in order (first match wins)."""
        device_data = {"environment": "production", "criticality": "high"}
        
        rules = [
            {
                "id": "first-rule",
                "conditions": {"environment": "production"},
                "target_versions": {"version": "1.0.0"}
            },
            {
                "id": "second-rule", 
                "conditions": {"environment": "production", "criticality": "high"},
                "target_versions": {"version": "2.0.0"}
            }
        ]
        
        # Should match first rule even though second rule also matches
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "first-rule")
        self.assertEqual(target_versions["version"], "1.0.0")

    def test_target_version_formats(self):
        """Test different target version formats."""
        device_data = {"deviceType": "test"}
        
        # String target version
        rules = {"conditions": {"deviceType": "test"}, "target_versions": "string-version"}
        _, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(target_versions, "string-version")
        
        # Dictionary target version
        rules = {"conditions": {"deviceType": "test"}, "target_versions": {"fw1": "1.0", "fw2": "2.0"}}
        _, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(target_versions["fw1"], "1.0")
        self.assertEqual(target_versions["fw2"], "2.0")
        
        # None target version (no updates needed)
        rules = {"conditions": {"deviceType": "test"}, "target_versions": None}
        _, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(target_versions)

    def test_complex_real_world_scenario(self):
        """Test a complex real-world scenario with multiple device types and conditions."""
        # Outdoor sensor device data
        outdoor_sensor_data = {
            "notecard": "8.1.2",
            "host": "3.1.1",
            "deviceType": "sensor", 
            "location": "outdoor",
            "fleet": "production",
            "batteryLevel": 90,
            "signalStrength": -55
        }
        
        rules = [
            {
                "id": "desired-state",
                "conditions": {
                    "notecard": "8.1.3",
                    "host": "3.1.2",
                    "fleet": "production"
                },
                "target_versions": None  # Already at desired versions
            },
            {
                "id": "outdoor-sensor-update",
                "conditions": {
                    "deviceType": "sensor",
                    "location": "outdoor", 
                    "fleet": "production",
                    "batteryLevel": lambda b: b and b > 50
                },
                "target_versions": {
                    "notecard": "8.1.3",
                    "host": "3.1.2"
                }
            },
            {
                "id": "emergency-update",
                "conditions": {
                    "signalStrength": lambda s: s and s < -80
                },
                "target_versions": {"notecard": "8.1.4-emergency"}
            }
        ]
        
        rule_id, target_versions = getFirmwareUpdateTargets(outdoor_sensor_data, rules=rules)
        self.assertEqual(rule_id, "outdoor-sensor-update")
        self.assertEqual(target_versions["notecard"], "8.1.3")
        self.assertEqual(target_versions["host"], "3.1.2")

    def test_no_rules_match(self):
        """Test when no rules match the device data."""
        device_data = {"deviceType": "unknown"}
        
        rules = [
            {"conditions": {"deviceType": "sensor"}, "target_versions": "sensor-update"},
            {"conditions": {"deviceType": "gateway"}, "target_versions": "gateway-update"}
        ]
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)

    def test_empty_device_data(self):
        """Test behavior with empty device data."""
        rules = {"conditions": {"someField": "someValue"}, "target_versions": "update"}
        
        rule_id, target_versions = getFirmwareUpdateTargets({}, rules=rules)
        self.assertIsNone(rule_id)
        self.assertIsNone(target_versions)

    def test_single_rule_as_dict(self):
        """Test passing a single rule as dict instead of list."""
        device_data = {"status": "active"}
        rules = {"conditions": {"status": "active"}, "target_versions": "single-rule-update"}
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "rule-1")  # Auto-generated ID
        self.assertEqual(target_versions, "single-rule-update")

    def test_dot_notation_simple_field(self):
        """Test dot notation with simple nested object access."""
        device_data = {
            "firmware_notecard": {
                "version": "8.1.3",
                "built": "2024-01-15",
                "type": "release"
            },
            "firmware_host": {
                "version": "3.1.2", 
                "size": 1024000
            }
        }
        
        rules = {
            "conditions": {
                "firmware_notecard.version": "8.1.3",
                "firmware_host.version": "3.1.2"
            },
            "target_versions": None
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "rule-1")
        self.assertIsNone(target_versions)

    def test_dot_notation_with_lambda_conditions(self):
        """Test dot notation with callable conditions."""
        device_data = {
            "firmware_notecard": {
                "version": "8.1.3.17074",
                "built": "2024-01-15"
            },
            "device_info": {
                "batteryLevel": 85,
                "signalStrength": -55
            }
        }
        
        rules = {
            "id": "dot-notation-lambda",
            "conditions": {
                "firmware_notecard.version": lambda v: v and v.startswith("8.1.3"),
                "device_info.batteryLevel": lambda b: b > 80,
                "device_info.signalStrength": lambda s: s > -60
            },
            "target_versions": {"notecard": "8.1.4"}
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "dot-notation-lambda")
        self.assertEqual(target_versions["notecard"], "8.1.4")

    def test_dot_notation_missing_base_field(self):
        """Test dot notation when base field doesn't exist."""
        device_data = {
            "firmware_notecard": {"version": "8.1.3"}
            # firmware_host is missing
        }
        
        rules = {
            "conditions": {
                "firmware_notecard.version": "8.1.3",
                "firmware_host.version": "3.1.2"  # This should fail - base field missing
            },
            "target_versions": "should-not-match"
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(rule_id)  # Should not match due to missing firmware_host
        self.assertIsNone(target_versions)

    def test_dot_notation_missing_nested_field(self):
        """Test dot notation when nested field doesn't exist."""
        device_data = {
            "firmware_notecard": {
                "version": "8.1.3"
                # built field is missing
            }
        }
        
        rules = {
            "conditions": {
                "firmware_notecard.version": "8.1.3",
                "firmware_notecard.built": "2024-01-15"  # This should fail - nested field missing
            },
            "target_versions": "should-not-match"
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(rule_id)  # Should not match due to missing built field
        self.assertIsNone(target_versions)

    def test_dot_notation_non_dict_base_field(self):
        """Test dot notation when base field is not a dictionary."""
        device_data = {
            "firmware_notecard": "8.1.3",  # String, not dict
            "simple_field": "value"
        }
        
        rules = {
            "conditions": {
                "firmware_notecard.version": "8.1.3",  # Should fail - can't traverse string
                "simple_field": "value"  # This part should match
            },
            "target_versions": "should-not-match"
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertIsNone(rule_id)  # Should not match due to invalid traversal
        self.assertIsNone(target_versions)

    def test_dot_notation_deep_nesting(self):
        """Test dot notation with deeply nested objects."""
        device_data = {
            "device": {
                "hardware": {
                    "sensors": {
                        "temperature": {"current": 23.5, "max": 85},
                        "humidity": {"current": 65}
                    }
                },
                "location": {
                    "coordinates": {"lat": 40.7128, "lon": -74.0060}
                }
            }
        }
        
        rules = {
            "id": "deep-nesting",
            "conditions": {
                "device.hardware.sensors.temperature.current": lambda t: t > 20,
                "device.location.coordinates.lat": lambda lat: 40 <= lat <= 41
            },
            "target_versions": {"firmware": "optimized-for-location"}
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "deep-nesting")
        self.assertEqual(target_versions["firmware"], "optimized-for-location")

    def test_mixed_dot_notation_and_regular_fields(self):
        """Test mixing dot notation fields with regular fields."""
        device_data = {
            "deviceType": "sensor",
            "location": "outdoor", 
            "firmware_notecard": {
                "version": "8.1.3",
                "type": "release"
            },
            "fleets": ["fleet:production", "fleet:sensors"]
        }
        
        rules = {
            "conditions": {
                "deviceType": "sensor",  # Regular field
                "firmware_notecard.version": lambda v: v.startswith("8.1"),  # Dot notation
                "location": "outdoor",  # Regular field
                "fleets": lambda fleet_list: "fleet:production" in fleet_list  # Regular field with lambda
            },
            "target_versions": {"notecard": "8.1.4"}
        }
        
        rule_id, target_versions = getFirmwareUpdateTargets(device_data, rules=rules)
        self.assertEqual(rule_id, "rule-1")
        self.assertEqual(target_versions["notecard"], "8.1.4")


if __name__ == '__main__':
    unittest.main()