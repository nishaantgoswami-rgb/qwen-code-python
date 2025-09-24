"""Enhanced logging configuration for Qwen Code CLI."""

import logging
import logging.handlers
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import sys

class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format for better monitoring."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            ]:
                log_entry[key] = value
                
        return json.dumps(log_entry)


def setup_logging(
    log_level: str = "WARNING",  # Changed from INFO to WARNING to reduce console output
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up comprehensive logging for the Qwen Code CLI application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Root logger configured for the application
    """
    # Convert string log level to logging constant
    level = getattr(logging, log_level.upper(), logging.WARNING)  # Changed default to WARNING
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler - Use WARNING level for console to reduce clutter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)  # Only show WARNING and above on console
    
    # Choose formatter based on environment
    if os.getenv('QWEN_LOG_JSON', '').lower() in ('true', '1', 'yes'):
        console_formatter = JSONFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file or os.getenv('QWEN_LOG_FILE'):
        log_path = log_file or os.getenv('QWEN_LOG_FILE')
        if log_path:
            # Ensure log directory exists
            log_dir = Path(log_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(logging.DEBUG)  # File gets all logs
            
            if os.getenv('QWEN_LOG_JSON', '').lower() in ('true', '1', 'yes'):
                file_formatter = JSONFormatter()
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(name)s [%(funcName)s:%(lineno)d]: %(message)s'
                )
            
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
    
    # Syslog handler for production environments
    if os.getenv('QWEN_ENABLE_SYSLOG', '').lower() in ('true', '1', 'yes'):
        try:
            syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
            syslog_handler.setLevel(logging.WARNING)
            syslog_formatter = logging.Formatter(
                'qwen-code-py[%(process)d]: %(levelname)s %(name)s: %(message)s'
            )
            syslog_handler.setFormatter(syslog_formatter)
            root_logger.addHandler(syslog_handler)
        except Exception as e:
            logging.warning(f"Could not set up syslog handler: {e}")
    
    # Application-specific logger
    app_logger = logging.getLogger('qwen_code')
    app_logger.setLevel(level)
    
    return app_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Name of the logger (defaults to 'qwen_code')
    
    Returns:
        Logger instance
    """
    logger_name = name or 'qwen_code'
    return logging.getLogger(logger_name)


def log_exception(
    logger: logging.Logger, 
    message: str, 
    exc_info: bool = True,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an exception with additional context.
    
    Args:
        logger: Logger instance to use
        message: Message to log with the exception
        exc_info: Whether to include exception info
        extra: Additional context to include in the log
    """
    logger.error(message, exc_info=exc_info, extra=extra or {})


# Initialize logging if this module is imported
def initialize_logging():
    """Initialize logging with environment-configured settings."""
    log_level = os.getenv('QWEN_LOG_LEVEL', 'INFO')
    log_file = os.getenv('QWEN_LOG_FILE', str(Path.home() / '.qwen' / 'logs' / 'qwen-code.log'))
    
    setup_logging(
        log_level=log_level,
        log_file=log_file
    )


# Initialize logging when module is loaded
# Only do this if not already initialized elsewhere to prevent duplicate handlers
if not logging.getLogger().handlers:
    initialize_logging()