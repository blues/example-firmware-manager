"""
Unit tests for the main module.

This test suite validates the main module functionality including:
- JSON parsing for firmware fields
- String to boolean conversion
- Lambda handler integration
"""

import unittest
import json
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main


class TestJsonParsing(unittest.TestCase):
    """Test cases for JSON parsing functionality."""
    
    def test_parse_firmware_json_with_valid_json_string(self):
        """Test parsing valid JSON string."""
        json_string = '{"version": "8.1.3", "built": "2024-01-15"}'
        expected = {"version": "8.1.3", "built": "2024-01-15"}
        
        result = main.parse_firmware_json(json_string)
        
        self.assertEqual(result, expected)
    
    def test_parse_firmware_json_with_dict_input(self):
        """Test that dict input is returned unchanged."""
        dict_input = {"version": "8.1.3", "built": "2024-01-15"}
        
        result = main.parse_firmware_json(dict_input)
        
        self.assertEqual(result, dict_input)
        self.assertIs(result, dict_input)  # Should be the same object
    
    def test_parse_firmware_json_with_non_json_string(self):
        """Test that non-JSON string is returned unchanged."""
        non_json_string = "just a regular string"
        
        result = main.parse_firmware_json(non_json_string)
        
        self.assertEqual(result, non_json_string)
    
    def test_parse_firmware_json_with_invalid_json(self):
        """Test that invalid JSON string is returned unchanged."""
        invalid_json = '{"version": "8.1.3", "built":}'
        
        result = main.parse_firmware_json(invalid_json)
        
        self.assertEqual(result, invalid_json)
    
    def test_parse_firmware_json_with_non_object_json(self):
        """Test that non-object JSON (array, string) is returned unchanged."""
        array_json = '["version", "8.1.3"]'
        string_json = '"just a string"'
        
        result_array = main.parse_firmware_json(array_json)
        result_string = main.parse_firmware_json(string_json)
        
        self.assertEqual(result_array, array_json)
        self.assertEqual(result_string, string_json)
    
    def test_parse_firmware_json_with_whitespace(self):
        """Test JSON parsing with surrounding whitespace."""
        json_with_whitespace = '  {"version": "8.1.3"}  '
        expected = {"version": "8.1.3"}
        
        result = main.parse_firmware_json(json_with_whitespace)
        
        self.assertEqual(result, expected)
    
    def test_parse_firmware_json_with_none(self):
        """Test that None input is returned unchanged."""
        result = main.parse_firmware_json(None)
        self.assertIsNone(result)
    
    def test_parse_firmware_json_with_number(self):
        """Test that number input is returned unchanged."""
        number_input = 123
        result = main.parse_firmware_json(number_input)
        self.assertEqual(result, number_input)


class TestParseFirmwareFields(unittest.TestCase):
    """Test cases for parse_firmware_fields function."""
    
    def test_parse_firmware_fields_with_json_strings(self):
        """Test parsing payload with JSON string firmware fields."""
        payload = {
            "device": "dev:123456",
            "fleets": ["fleet:abc"],
            "firmware_notecard": '{"version": "8.1.3", "built": "2024-01-15"}',
            "firmware_host": '{"version": "3.1.2", "type": "production"}'
        }
        
        result = main.parse_firmware_fields(payload)
        
        expected = {
            "device": "dev:123456",
            "fleets": ["fleet:abc"],
            "firmware_notecard": {"version": "8.1.3", "built": "2024-01-15"},
            "firmware_host": {"version": "3.1.2", "type": "production"}
        }
        
        self.assertEqual(result, expected)
        # Ensure original payload is not modified
        self.assertIsInstance(payload["firmware_notecard"], str)
        self.assertIsInstance(payload["firmware_host"], str)
    
    def test_parse_firmware_fields_with_dict_firmware(self):
        """Test parsing payload with dict firmware fields (no change needed)."""
        payload = {
            "device": "dev:123456",
            "fleets": ["fleet:abc"],
            "firmware_notecard": {"version": "8.1.3", "built": "2024-01-15"},
            "firmware_host": {"version": "3.1.2", "type": "production"}
        }
        
        result = main.parse_firmware_fields(payload)
        
        self.assertEqual(result, payload)
    
    def test_parse_firmware_fields_with_mixed_types(self):
        """Test parsing with one JSON string and one dict."""
        payload = {
            "device": "dev:123456",
            "firmware_notecard": '{"version": "8.1.3"}',
            "firmware_host": {"version": "3.1.2"}
        }
        
        result = main.parse_firmware_fields(payload)
        
        expected = {
            "device": "dev:123456", 
            "firmware_notecard": {"version": "8.1.3"},
            "firmware_host": {"version": "3.1.2"}
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_firmware_fields_with_no_firmware_fields(self):
        """Test parsing payload without firmware fields."""
        payload = {
            "device": "dev:123456",
            "fleets": ["fleet:abc"]
        }
        
        result = main.parse_firmware_fields(payload)
        
        self.assertEqual(result, payload)
    
    def test_parse_firmware_fields_with_invalid_json(self):
        """Test parsing with invalid JSON in firmware fields."""
        payload = {
            "device": "dev:123456",
            "firmware_notecard": '{"version": invalid}',
            "firmware_host": '{"version": "3.1.2"}'
        }
        
        result = main.parse_firmware_fields(payload)
        
        expected = {
            "device": "dev:123456",
            "firmware_notecard": '{"version": invalid}',  # Unchanged due to invalid JSON
            "firmware_host": {"version": "3.1.2"}         # Parsed successfully
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_firmware_fields_preserves_original(self):
        """Test that the original payload is not modified."""
        original_payload = {
            "device": "dev:123456",
            "firmware_notecard": '{"version": "8.1.3"}'
        }
        payload = original_payload.copy()
        
        result = main.parse_firmware_fields(payload)
        
        # Original payload should be unchanged
        self.assertEqual(payload, original_payload)
        # Result should be different
        self.assertNotEqual(result, original_payload)
        self.assertIsInstance(result["firmware_notecard"], dict)


class TestStrToBool(unittest.TestCase):
    """Test cases for str_to_bool function."""
    
    def test_str_to_bool_true_values(self):
        """Test various true string values."""
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']
        
        for value in true_values:
            with self.subTest(value=value):
                self.assertTrue(main.str_to_bool(value))
    
    def test_str_to_bool_false_values(self):
        """Test various false string values."""
        false_values = ['false', 'False', 'FALSE', '0', 'no', 'NO', 'off', 'OFF', 'random', '']
        
        for value in false_values:
            with self.subTest(value=value):
                self.assertFalse(main.str_to_bool(value))
    
    def test_str_to_bool_none(self):
        """Test None input returns False."""
        self.assertFalse(main.str_to_bool(None))
    
    def test_str_to_bool_non_string(self):
        """Test non-string inputs."""
        self.assertFalse(main.str_to_bool(0))  # str(0) == "0" -> False
        self.assertTrue(main.str_to_bool(1))   # str(1) == "1" -> True
        self.assertFalse(main.str_to_bool(2))  # str(2) == "2" -> False


if __name__ == '__main__':
    unittest.main()