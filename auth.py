"""
Authentication module for the Confluence PDF Generator Lambda function.

This module provides authentication functionality including:
- Request authentication using authorization headers
- Support for both Authorization and x-api-key headers
- Bearer token format handling
- Secure token comparison using HMAC
"""

import hmac
import logging

# Configure logging
logger = logging.getLogger(__name__)


def authenticate_request(event, expected_token):
    """
    Authenticate incoming Lambda requests using authorization headers.
    
    Validates requests by extracting and verifying authorization tokens from HTTP headers.
    Supports multiple authentication schemes and header formats with secure token comparison.
    
    Authentication Methods Supported:
        - Authorization header with Bearer token: 'Authorization: Bearer <token>'
        - Authorization header with direct token: 'Authorization: <token>'
        - X-API-Key header: 'x-api-key: <token>'
    
    Header Processing:
        - Case-insensitive header matching
        - x-api-key takes precedence over Authorization header if both present
        - Automatic Bearer token prefix handling
        - Whitespace trimming and validation
    
    Security Features:
        - Constant-time token comparison using hmac.compare_digest()
        - Protection against timing attacks
        - Comprehensive input validation
    
    Args:
        event (dict): Lambda event object containing request data including:
            - headers (dict): HTTP headers from the request
        expected_token: token value used for comparison
    
    Returns:
        dict: Authentication result with the following structure:
            - success (bool): True if authentication succeeded, False otherwise
            - error (str or None): Error message if authentication failed, None if successful
            
    Example:
        >>> result = authenticate_request(event, secrets_manager)
        >>> if result['success']:
        >>>     # Request is authenticated, proceed
        >>>     pass
        >>> else:
        >>>     # Authentication failed
        >>>     print(f"Auth error: {result['error']}")
    
    Raises:
        Exception: Internal exceptions are caught and returned as authentication failures
    """
    try:
        # Get headers from event (handle both direct invocation and API Gateway)
        headers = event.get('headers', {})
        
        # Handle case-insensitive headers
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        # Extract authorization header - x-api-key takes precedence
        auth_header = headers_lower.get('x-api-key') or headers_lower.get('authorization')
        
        if auth_header is None:
            return {'success': False, 'error': 'Missing authorization header'}
        
        # Check if header exists but is empty
        if not auth_header.strip():
            return {'success': False, 'error': 'Empty authorization token'}
        
        # Extract token from header (handle "Bearer token" or just "token")
        token = auth_header
        if auth_header.lower().startswith('bearer '):
            token = auth_header[7:]  # Remove "Bearer " prefix
        
        token = token.strip()
        if not token:
            return {'success': False, 'error': 'Empty authorization token'}
        
        
        if not expected_token:
            return {'success': False, 'error': 'Authentication not configured'}
        
        # Compare tokens (constant time comparison for security)
        if not hmac.compare_digest(token, expected_token):
            return {'success': False, 'error': 'Invalid authorization token'}
        
        return {'success': True, 'error': None}
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return {'success': False, 'error': 'Authentication system error'}
    

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
