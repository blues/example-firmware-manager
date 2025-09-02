"""
Unit tests for the auth module.

This test suite validates the authentication functionality including:
- Request authentication with various header formats
- Bearer token handling
- Case-insensitive header processing
- Error handling and edge cases
- Security features like constant-time comparison
"""

import unittest
from unittest.mock import patch, MagicMock
import hmac
import sys
import os

# Add the parent directory to the path so we can import auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth


class TestAuthenticateRequest(unittest.TestCase):
    """Test cases for the authenticate_request function."""

    def setUp(self):
        """Set up test fixtures."""
        self.expected_token = "test_token_123"
        self.valid_event_with_auth = {
            'headers': {
                'Authorization': f'Bearer {self.expected_token}',
                'Content-Type': 'application/json'
            }
        }

    def test_successful_authentication_with_bearer_token(self):
        """Test successful authentication with Bearer token in Authorization header."""
        event = {
            'headers': {
                'Authorization': f'Bearer {self.expected_token}'
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_successful_authentication_with_direct_token(self):
        """Test successful authentication with direct token in Authorization header."""
        event = {
            'headers': {
                'Authorization': self.expected_token
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_successful_authentication_with_api_key_header(self):
        """Test successful authentication with x-api-key header."""
        event = {
            'headers': {
                'x-api-key': self.expected_token
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_api_key_takes_precedence_over_authorization(self):
        """Test that x-api-key header takes precedence over Authorization header."""
        event = {
            'headers': {
                'Authorization': 'Bearer wrong_token',
                'x-api-key': self.expected_token
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_case_insensitive_headers(self):
        """Test that headers are processed case-insensitively."""
        event = {
            'headers': {
                'AUTHORIZATION': f'Bearer {self.expected_token}'
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_case_insensitive_api_key_header(self):
        """Test case-insensitive processing for x-api-key header."""
        event = {
            'headers': {
                'X-API-KEY': self.expected_token
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_case_insensitive_bearer_keyword(self):
        """Test case-insensitive Bearer keyword handling."""
        event = {
            'headers': {
                'Authorization': f'BEARER {self.expected_token}'
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_whitespace_handling_in_tokens(self):
        """Test that whitespace is properly trimmed from tokens."""
        event = {
            'headers': {
                'Authorization': f'Bearer   {self.expected_token}   '
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_missing_authorization_header(self):
        """Test authentication failure when authorization header is missing."""
        event = {
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Missing authorization header')

    def test_empty_headers_dict(self):
        """Test authentication failure when headers dict is empty."""
        event = {'headers': {}}
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Missing authorization header')

    def test_no_headers_key_in_event(self):
        """Test authentication when event has no headers key."""
        event = {}
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Missing authorization header')

    def test_empty_authorization_header(self):
        """Test authentication failure when authorization header is empty."""
        event = {
            'headers': {
                'Authorization': ''
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Empty authorization token')

    def test_whitespace_only_authorization_header(self):
        """Test authentication failure when authorization header contains only whitespace."""
        event = {
            'headers': {
                'Authorization': '   '
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Empty authorization token')

    def test_bearer_with_empty_token(self):
        """Test authentication failure when Bearer token is empty."""
        event = {
            'headers': {
                'Authorization': 'Bearer'
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        # Note: "Bearer" without space gets processed as invalid token, not empty token
        self.assertEqual(result['error'], 'Invalid authorization token')

    def test_bearer_with_whitespace_token(self):
        """Test authentication failure when Bearer token is only whitespace."""
        event = {
            'headers': {
                'Authorization': 'Bearer   '
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Empty authorization token')

    def test_invalid_token(self):
        """Test authentication failure with invalid token."""
        event = {
            'headers': {
                'Authorization': 'Bearer wrong_token'
            }
        }
        result = auth.authenticate_request(event, self.expected_token)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Invalid authorization token')

    def test_none_expected_token(self):
        """Test authentication failure when expected token is None."""
        event = {
            'headers': {
                'Authorization': f'Bearer {self.expected_token}'
            }
        }
        result = auth.authenticate_request(event, None)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Authentication not configured')

    def test_empty_expected_token(self):
        """Test authentication failure when expected token is empty."""
        event = {
            'headers': {
                'Authorization': f'Bearer {self.expected_token}'
            }
        }
        result = auth.authenticate_request(event, '')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Authentication not configured')

    def test_constant_time_comparison_is_used(self):
        """Test that hmac.compare_digest is used for token comparison."""
        with patch('hmac.compare_digest', return_value=True) as mock_compare:
            event = {
                'headers': {
                    'Authorization': f'Bearer {self.expected_token}'
                }
            }
            result = auth.authenticate_request(event, self.expected_token)
            
            mock_compare.assert_called_once_with(self.expected_token, self.expected_token)
            self.assertTrue(result['success'])

    def test_exception_handling(self):
        """Test that exceptions are properly handled and logged."""
        with patch('auth.logger') as mock_logger:
            # Create an event that will cause an exception when processing headers
            event = None  # This will cause an exception
            
            result = auth.authenticate_request(event, self.expected_token)
            
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'Authentication system error')
            mock_logger.error.assert_called_once()

    def test_various_bearer_token_formats(self):
        """Test various formats of Bearer token."""
        test_cases = [
            'Bearer token123',
            'bearer token123',
            'BEARER token123',
            'BeArEr token123'
        ]
        
        for auth_header in test_cases:
            with self.subTest(auth_header=auth_header):
                event = {
                    'headers': {
                        'Authorization': auth_header
                    }
                }
                result = auth.authenticate_request(event, 'token123')
                self.assertTrue(result['success'], f"Failed for: {auth_header}")

    def test_token_with_special_characters(self):
        """Test tokens containing special characters."""
        special_token = "token!@#$%^&*()_+-={}[]|;:,.<>?"
        event = {
            'headers': {
                'Authorization': f'Bearer {special_token}'
            }
        }
        result = auth.authenticate_request(event, special_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_very_long_token(self):
        """Test authentication with very long token."""
        long_token = "a" * 1000
        event = {
            'headers': {
                'Authorization': f'Bearer {long_token}'
            }
        }
        result = auth.authenticate_request(event, long_token)
        
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])

    def test_unicode_in_token(self):
        """Test tokens containing unicode characters."""
        unicode_token = "token_测试_🔐"
        event = {
            'headers': {
                'Authorization': f'Bearer {unicode_token}'
            }
        }
        result = auth.authenticate_request(event, unicode_token)
        
        # hmac.compare_digest doesn't support non-ASCII characters
        # This results in an authentication system error
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Authentication system error')


if __name__ == '__main__':
    unittest.main()