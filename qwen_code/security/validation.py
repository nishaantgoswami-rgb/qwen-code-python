"""
Enhanced input validation and sanitization for Qwen Code.
Implements comprehensive security checks for all user inputs.
"""

import re
import html
import urllib.parse
from pathlib import Path
from typing import Optional, Union, List
from qwen_code.utils.logging import get_logger


logger = get_logger()


class InputValidator:
    """
    Enhanced input validation utilities for Qwen Code.
    Implements comprehensive validation and sanitization for all user inputs.
    """
    
    # Regular expressions for validation
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE)
    SQL_INJECTION_PATTERNS = [
        re.compile(r'(union\s+select|select.*from|drop\s+\w+|create\s+\w+|exec\s*\(|execute\s*\(|insert\s+into|update\s+\w+\s+set|delete\s+from)', re.IGNORECASE),
        re.compile(r'(;|\'|")\s*(--|#|/\*|\*/)', re.IGNORECASE),
    ]
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'vbscript:', re.IGNORECASE),
    ]
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r'\.\.\/'),
        re.compile(r'\.\.\\'),
        re.compile(r'%2e%2e%2f'),
        re.compile(r'%2e%2e%5c'),
    ]

    @staticmethod
    def validate_filename(filename: str) -> bool:
        """
        Validate filename for safety against path traversal and special characters.
        
        Args:
            filename: The filename to validate
            
        Returns:
            True if filename is safe, False otherwise
        """
        if not filename or len(filename) > 255:
            logger.warning(f"Invalid filename: too long or empty - {filename}")
            return False
        
        # Check against safe filename pattern
        if not InputValidator.SAFE_FILENAME_PATTERN.match(filename):
            logger.warning(f"Unsafe filename pattern: {filename}")
            return False
        
        # Additional checks for dangerous patterns
        dangerous_patterns = ['..', '~', '$', '`', '|', '&', ';', '<', '>', '>', '<']
        if any(pattern in filename for pattern in dangerous_patterns):
            logger.warning(f"Dangerous pattern in filename: {filename}")
            return False
        
        return True

    @staticmethod
    def validate_path(path: str, base_path: Optional[Path] = None) -> bool:
        """
        Validate file path for safety against path traversal attacks.
        
        Args:
            path: The path to validate
            base_path: Optional base path to check against
            
        Returns:
            True if path is safe, False otherwise
        """
        if not path:
            logger.warning("Empty path provided")
            return False
        
        # Check against path traversal patterns
        for pattern in InputValidator.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(path):
                logger.warning(f"Path traversal attempt detected: {path}")
                return False
        
        # Check for dangerous patterns
        dangerous_patterns = ['~', '$', '`', '|', '&', ';', '<', '>']
        if any(pattern in path for pattern in dangerous_patterns):
            logger.warning(f"Dangerous pattern in path: {path}")
            return False
        
        # If base_path is provided, ensure path is within base_path
        if base_path:
            try:
                # Resolve the full path
                full_path = Path(base_path) / Path(path)
                resolved_full_path = full_path.resolve()
                resolved_base_path = base_path.resolve()
                
                # Check if full_path is within base_path
                if not str(resolved_full_path).startswith(str(resolved_base_path)):
                    logger.warning(f"Path is outside base directory: {path}")
                    return False
            except (OSError, ValueError) as e:
                logger.error(f"Error resolving path {path}: {str(e)}")
                return False
        
        return True

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format and prevent SSRF attacks.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        if not url or len(url) > 2048:
            logger.warning(f"Invalid URL: too long or empty - {url}")
            return False
        
        # Check basic format
        if not InputValidator.URL_PATTERN.match(url):
            logger.warning(f"Invalid URL format: {url}")
            return False
        
        # Parse the URL to check for dangerous schemes or IPs
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            
            # Block private IP addresses
            if host:
                if host.startswith('127.') or host.startswith('10.') or host.startswith('192.168') or host.startswith('172.'):
                    # Additional check for private/local addresses
                    import ipaddress
                    try:
                        ip = ipaddress.ip_address(host)
                        if ip.is_private or ip.is_loopback or ip.is_link_local:
                            logger.warning(f"Blocked private IP address in URL: {url}")
                            return False
                    except ValueError:
                        # Not a valid IP, continue with hostname checks
                        pass
                    
                    # Block localhost and special domains
                    if host.lower() in ['localhost', 'local', 'internal', 'metadata.google.internal']:
                        logger.warning(f"Blocked potentially dangerous host: {host}")
                        return False
        
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {str(e)}")
            return False
        
        return True

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Validate API key format and prevent injection attacks.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if API key is valid, False otherwise
        """
        if not api_key or len(api_key) < 10:
            logger.warning(f"Invalid API key: too short - {api_key[:20] if api_key else 'None'}...")
            return False
        
        # Basic check for alphanumeric and common key characters
        if not re.match(r'^[a-zA-Z0-9._-]+$', api_key):
            logger.warning(f"Invalid API key format: {api_key[:20]}...")
            return False
        
        # Check for potential injection patterns
        check_key = api_key.lower()
        dangerous_patterns = ['union', 'select', 'drop', 'create', 'exec', 'insert', 'delete', 'update']
        if any(pattern in check_key for pattern in dangerous_patterns):
            logger.warning(f"Potential SQL injection in API key: {api_key[:20]}...")
            return False
        
        return True

    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """
        Sanitize input to prevent SQL injection.
        
        Args:
            text: The input text to sanitize
            
        Returns:
            Sanitized input text
        """
        if not text:
            return ""
        
        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if pattern.search(text):
                logger.warning(f"SQL injection pattern detected: {text[:100]}...")
                # Remove dangerous patterns
                text = pattern.sub('', text)
        
        return text

    @staticmethod
    def sanitize_xss_input(text: str) -> str:
        """
        Sanitize input to prevent XSS attacks.
        
        Args:
            text: The input text to sanitize
            
        Returns:
            Sanitized input text
        """
        if not text:
            return ""
        
        # Check for XSS patterns
        for pattern in InputValidator.XSS_PATTERNS:
            if pattern.search(text):
                logger.warning(f"XSS pattern detected: {text[:100]}...")
                # Remove dangerous patterns
                text = pattern.sub('', text)
        
        # Escape HTML characters
        text = html.escape(text)
        
        return text

    @staticmethod
    def sanitize_input(text: str, max_length: int = 10000) -> str:
        """
        Comprehensive sanitization of user input.
        
        Args:
            text: The input text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized input text
        """
        if not text:
            return ""
        
        # Truncate if too long
        if len(text) > max_length:
            logger.warning(f"Input truncated from {len(text)} to {max_length} characters")
            text = text[:max_length]
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Sanitize for SQL injection
        text = InputValidator.sanitize_sql_input(text)
        
        # Sanitize for XSS
        text = InputValidator.sanitize_xss_input(text)
        
        return text

    @staticmethod
    def validate_command_input(command: str) -> bool:
        """
        Validate command-line input for dangerous commands.
        
        Args:
            command: The command input to validate
            
        Returns:
            True if command is safe, False otherwise
        """
        if not command:
            return False
        
        # Convert to lowercase for comparison
        lower_cmd = command.lower()
        
        # Dangerous command patterns
        dangerous_commands = [
            r'\b(rm\s+-rf|rm\s+--no-preserve-root|mkfs|dd|format|del|scsi|fdisk|parted|partition)',
            r'\b(curl|wget|fetch|lynx|links)\s+.*\|.*sh',
            r'\b(base64|hexdump|xxd)\s+.*\|.*sh',
            r'\b(sh|bash|zsh|ksh|csh|tcsh|fish)\s+.*-c',
            r'\b(python|python2|python3|perl|ruby|php|node|java)\s+.*-e',
            r'\bgit\s+clone\s+.*|git\s+remote\s+add',
            r'\bcurl\s+.*-o\s+.*|wget\s+.*-O\s+.*',
            r'\bcurl.*\$\(|`\w+`',
            r'\bexec\b|\beval\b|\bimportlib\b'
        ]
        
        for pattern in dangerous_commands:
            if re.search(pattern, lower_cmd):
                logger.warning(f"Dangerous command pattern detected: {command[:100]}...")
                return False
        
        return True


class PathSecurity:
    """
    Enhanced path security utilities for Qwen Code.
    """
    
    @staticmethod
    def is_safe_path(path: Path, base_path: Path) -> bool:
        """
        Check if a path is safe (within base path) and prevent path traversal.
        
        Args:
            path: The path to check
            base_path: The allowed base path
            
        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Resolve both paths
            resolved_path = path.resolve()
            resolved_base = base_path.resolve()
            
            # Check if path is within base path
            return str(resolved_path).startswith(str(resolved_base))
        except (OSError, ValueError) as e:
            logger.error(f"Error resolving path {path}: {str(e)}")
            return False
    
    @staticmethod
    def get_safe_path(user_path: str, base_path: Path) -> Optional[Path]:
        """
        Get a safe path within base path, preventing path traversal.
        
        Args:
            user_path: User-provided path
            base_path: The allowed base path
            
        Returns:
            Safe Path object or None if path is unsafe
        """
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
    """
    Enhanced data sanitization utilities for Qwen Code.
    """
    
    @staticmethod
    def sanitize_environment_vars() -> None:
        """
        Sanitize sensitive environment variables and log appropriately.
        """
        import os
        sensitive_vars = [
            'QWEN_CLIENT_SECRET',
            'QWEN_API_KEY', 
            'OPENAI_API_KEY',
            'OPENAI_BASE_URL',
            'QWEN_CREDENTIAL_PASSWORD',
            'QWEN_DB_PASSWORD'
        ]
        
        for var in sensitive_vars:
            if var in os.environ:
                # Don't log the actual value, just indicate it's set
                logger.info(f"Sensitive environment variable {var} is set")
    
    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        """
        Mask sensitive data in text for safe logging.
        
        Args:
            text: The text to mask
            
        Returns:
            Text with sensitive data masked
        """
        # Mask API keys (OpenAI, AWS, etc.)
        text = re.sub(r'(sk-[a-zA-Z0-9]{20,})', '[MASKED_API_KEY]', text)
        text = re.sub(r'(api_key["\s]*["\s]*[:=]["\s]*)([a-zA-Z0-9._-]{10,})', 
                     r'\1[MASKED_API_KEY]', text)
        
        # Mask client secrets
        text = re.sub(r'(client_secret["\s]*["\s]*[:=]["\s]*)([a-zA-Z0-9._-]{10,})', 
                     r'\1[MASKED_CLIENT_SECRET]', text)
        
        # Mask passwords
        text = re.sub(r'(password["\s]*["\s]*[:=]["\s]*)([^\s,}]+)', 
                     r'\1[MASKED_PASSWORD]', text)
        
        # Mask tokens
        text = re.sub(r'([bB]earer\s+)([a-zA-Z0-9._-]{20,})', 
                     r'\1[MASKED_TOKEN]', text)
        
        return text


import os as environ

# Global instance for convenience
input_validator = InputValidator()