"""Security utilities for Qwen Code."""

import re
import os
from pathlib import Path
from typing import Optional, List
from qwen_code.utils.logging import get_logger


logger = get_logger()


class InputValidator:
    """Input validation utilities for Qwen Code."""
    
    # Regular expressions for validation
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename for safety."""
        if not filename or len(filename) > 255:
            return False
        return bool(InputValidator.SAFE_FILENAME_PATTERN.match(filename))
    
    @staticmethod
    def validate_path(path: str, base_path: Optional[Path] = None) -> bool:
        """Validate file path for safety."""
        if not path:
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = ['..', '~', '$', '`', '|', '&', ';', '<', '>']
        if any(pattern in path for pattern in dangerous_patterns):
            return False
        
        # If base_path is provided, ensure path is within base_path
        if base_path:
            try:
                full_path = (base_path / path).resolve()
                base_path_resolved = base_path.resolve()
                # Check if full_path is within base_path
                if not str(full_path).startswith(str(base_path_resolved)):
                    return False
            except (OSError, ValueError):
                return False
        
        return True
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        if not url or len(url) > 2048:
            return False
        return bool(InputValidator.URL_PATTERN.match(url))
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format."""
        if not api_key or len(api_key) < 10:
            return False
        # Basic check for alphanumeric and common key characters
        return bool(re.match(r'^[a-zA-Z0-9._-]+$', api_key))
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 10000) -> str:
        """Sanitize user input."""
        if not text:
            return ""
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Input truncated to {max_length} characters")
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        return text


class PathSecurity:
    """Path security utilities for Qwen Code."""
    
    @staticmethod
    def is_safe_path(path: Path, base_path: Path) -> bool:
        """Check if a path is safe (within base path)."""
        try:
            # Resolve both paths
            resolved_path = path.resolve()
            resolved_base = base_path.resolve()
            
            # Check if path is within base path
            return str(resolved_path).startswith(str(resolved_base))
        except (OSError, ValueError):
            return False
    
    @staticmethod
    def get_safe_path(user_path: str, base_path: Path) -> Optional[Path]:
        """Get a safe path within base path."""
        try:
            # Create path object
            path = Path(user_path)
            
            # Check if path is absolute
            if path.is_absolute():
                logger.warning(f"Absolute path not allowed: {user_path}")
                return None
            
            # Create full path
            full_path = base_path / path
            
            # Check if path is safe
            if not PathSecurity.is_safe_path(full_path, base_path):
                logger.warning(f"Path outside base directory: {user_path}")
                return None
            
            return full_path
        except (OSError, ValueError) as e:
            logger.error(f"Error processing path {user_path}: {str(e)}")
            return None


class DataSanitizer:
    """Data sanitization utilities for Qwen Code."""
    
    @staticmethod
    def sanitize_environment_vars() -> None:
        """Sanitize sensitive environment variables."""
        sensitive_vars = [
            'QWEN_CLIENT_SECRET',
            'QWEN_API_KEY',
            'OPENAI_API_KEY',
            'OPENAI_BASE_URL'
        ]
        
        for var in sensitive_vars:
            if var in os.environ:
                # Don't log the actual value, just indicate it's set
                logger.info(f"Sensitive environment variable {var} is set")
    
    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        """Mask sensitive data in text."""
        # Mask API keys
        text = re.sub(r'(sk-[a-zA-Z0-9]{20,})', '[MASKED_API_KEY]', text)
        text = re.sub(r'(api_key["\s]*["\s]*[:=]["\s]*)([a-zA-Z0-9._-]{10,})', 
                     r'\1[MASKED_API_KEY]', text)
        
        # Mask client secrets
        text = re.sub(r'(client_secret["\s]*["\s]*[:=]["\s]*)([a-zA-Z0-9._-]{10,})', 
                     r'\1[MASKED_CLIENT_SECRET]', text)
        
        return text


def setup_security() -> None:
    """Setup security features for the application."""
    # Sanitize environment variables
    DataSanitizer.sanitize_environment_vars()
    
    # Log security setup
    logger.info("Security features initialized")