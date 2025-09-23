"""Security tests for Qwen Code."""

import pytest
import tempfile
from pathlib import Path
from qwen_code.utils.security import InputValidator, PathSecurity, DataSanitizer


class TestInputValidator:
    """Test input validation utilities."""
    
    def test_validate_filename(self):
        """Test filename validation."""
        # Valid filenames
        assert InputValidator.validate_filename("test.py") is True
        assert InputValidator.validate_filename("my-file_123.txt") is True
        assert InputValidator.validate_filename("file.name") is True
        
        # Invalid filenames
        assert InputValidator.validate_filename("") is False
        assert InputValidator.validate_filename("../test.py") is False
        assert InputValidator.validate_filename("test.py/test") is False
        assert InputValidator.validate_filename("test|file.py") is False
    
    def test_validate_path(self):
        """Test path validation."""
        # Valid paths
        assert InputValidator.validate_path("src/main.py") is True
        assert InputValidator.validate_path("lib/utils.py") is True
        assert InputValidator.validate_path("test_file.py") is True
        
        # Invalid paths with dangerous patterns
        assert InputValidator.validate_path("../secret.py") is False
        assert InputValidator.validate_path("~/secrets.txt") is False
        assert InputValidator.validate_path("file|name.py") is False
        assert InputValidator.validate_path("file;rm -rf /") is False
    
    def test_validate_url(self):
        """Test URL validation."""
        # Valid URLs
        assert InputValidator.validate_url("https://api.openai.com/v1") is True
        assert InputValidator.validate_url("http://localhost:8080") is True
        assert InputValidator.validate_url("https://dashscope.aliyuncs.com") is True
        
        # Invalid URLs
        assert InputValidator.validate_url("") is False
        assert InputValidator.validate_url("not-a-url") is False
        assert InputValidator.validate_url("ftp://example.com") is False  # Only http/https allowed
    
    def test_validate_api_key(self):
        """Test API key validation."""
        # Valid API keys
        assert InputValidator.validate_api_key("sk-1234567890abcdef") is True
        assert InputValidator.validate_api_key("abc_def-123") is True
        
        # Invalid API keys
        assert InputValidator.validate_api_key("") is False
        assert InputValidator.validate_api_key("short") is False
        assert InputValidator.validate_api_key("key with spaces") is False
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        # Normal input
        assert InputValidator.sanitize_input("Hello, World!") == "Hello, World!"
        
        # Input with null bytes
        assert InputValidator.sanitize_input("Hello\x00World") == "HelloWorld"
        
        # Long input (should be truncated)
        long_input = "a" * 15000
        sanitized = InputValidator.sanitize_input(long_input, max_length=10000)
        assert len(sanitized) == 10000


class TestPathSecurity:
    """Test path security utilities."""
    
    def test_is_safe_path(self):
        """Test safe path checking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            safe_path = base_path / "subdir" / "file.py"
            unsafe_path = Path("/etc/passwd")
            
            # Create directories
            (base_path / "subdir").mkdir()
            
            # Safe path should be allowed
            assert PathSecurity.is_safe_path(safe_path, base_path) is True
            
            # Unsafe path should be rejected
            assert PathSecurity.is_safe_path(unsafe_path, base_path) is False
    
    def test_get_safe_path(self):
        """Test getting safe paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            # Valid relative path
            safe_result = PathSecurity.get_safe_path("src/main.py", base_path)
            assert safe_result is not None
            assert safe_result == base_path / "src/main.py"
            
            # Invalid path (absolute)
            unsafe_result = PathSecurity.get_safe_path("/etc/passwd", base_path)
            assert unsafe_result is None
            
            # Invalid path (directory traversal)
            traversal_result = PathSecurity.get_safe_path("../secret.txt", base_path)
            assert traversal_result is None


class TestDataSanitizer:
    """Test data sanitization utilities."""
    
    def test_mask_sensitive_data(self):
        """Test masking sensitive data."""
        # Mask API key
        text_with_key = "API_KEY=sk-1234567890abcdef1234567890"
        masked = DataSanitizer.mask_sensitive_data(text_with_key)
        assert "[MASKED_API_KEY]" in masked
        assert "sk-1234567890abcdef1234567890" not in masked
        
        # Mask client secret
        text_with_secret = 'client_secret: "my-secret-key-123"'
        masked = DataSanitizer.mask_sensitive_data(text_with_secret)
        assert "[MASKED_CLIENT_SECRET]" in masked
        assert "my-secret-key-123" not in masked


if __name__ == "__main__":
    pytest.main([__file__])