"""Logging configuration for Qwen Code."""

import logging
import os
from pathlib import Path
from typing import Optional


class QwenLogger:
    """Centralized logging management for Qwen Code."""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("qwen_code")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Prevent adding multiple handlers if logger already configured
        if not self.logger.handlers:
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Add console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # Add file handler if log_file specified
            if log_file:
                # Create log directory if it doesn't exist
                log_path = Path(log_file).expanduser()
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(log_path)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)


# Global logger instance
_qwen_logger: Optional[QwenLogger] = None


def get_logger() -> QwenLogger:
    """Get the global logger instance."""
    global _qwen_logger
    if _qwen_logger is None:
        # Default configuration
        log_level = os.getenv("QWEN_LOG_LEVEL", "INFO")
        log_file = os.getenv("QWEN_LOG_FILE")
        _qwen_logger = QwenLogger(log_level, log_file)
    return _qwen_logger


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup global logging configuration."""
    global _qwen_logger
    _qwen_logger = QwenLogger(log_level, log_file)