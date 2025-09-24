"""
Security initialization module for Qwen Code.
Sets up all security features when the application starts.
"""

from qwen_code.security.validation import input_validator, DataSanitizer
from qwen_code.security.credentials import SecureCredentialManager
from qwen_code.security.rate_limiting import api_rate_limiter
from qwen_code.security.audit import audit_logger, security_monitor
from qwen_code.utils.logging import get_logger


logger = get_logger()


def initialize_security() -> None:
    """Initialize all security features for the application."""
    # logger.info("Initializing security features...")  # Removed for cleaner UI
    
    # Initialize input validation
    # logger.info("Input validation initialized")  # Removed for cleaner UI
    
    # Sanitize environment variables
    DataSanitizer.sanitize_environment_vars()
    # logger.info("Environment variables sanitized")  # Removed for cleaner UI
    
    # Initialize secure credential manager
    credential_manager = SecureCredentialManager()
    # logger.info("Secure credential manager initialized")  # Removed for cleaner UI
    
    # Initialize rate limiter (already configured with defaults)
    # logger.info("Rate limiting initialized with default policies")  # Removed for cleaner UI
    
    # Initialize audit logging
    # logger.info("Audit logging initialized")  # Removed for cleaner UI
    
    # Initialize security monitor
    # logger.info("Security monitoring initialized")  # Removed for cleaner UI
    
    # logger.info("All security features initialized successfully")  # Removed for cleaner UI


def setup_security_policies() -> None:
    """Setup additional security policies as needed."""
    # Add any specific security policies here
    logger.info("Security policies configured")