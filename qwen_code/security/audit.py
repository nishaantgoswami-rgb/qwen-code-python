"""
Enhanced audit logging for security events in Qwen Code.
Implements comprehensive logging for security-related events.
"""

import json
import os
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path
from qwen_code.utils.logging import get_logger


logger = get_logger()


class SecurityEventType(Enum):
    """Types of security events that can be logged."""
    AUTHENTICATION_SUCCESS = "AUTHENTICATION_SUCCESS"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    INPUT_VALIDATION_FAILURE = "INPUT_VALIDATION_FAILURE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    CREDENTIAL_CHANGE = "CREDENTIAL_CHANGE"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    FILE_ACCESS = "FILE_ACCESS"
    API_CALL = "API_CALL"
    SESSION_CREATION = "SESSION_CREATION"
    SESSION_DESTRUCTION = "SESSION_DESTRUCTION"


class AuditLogger:
    """
    Enhanced audit logger for security events in Qwen Code.
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize the audit logger.
        
        Args:
            log_file: Optional path for audit log file
        """
        if log_file is None:
            log_file = Path.home() / ".qwen" / "audit.log"
        
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        
        # Store log file path for audit events
        self.log_file_path = str(self.log_file)
        
    def log_security_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO"
    ) -> None:
        """
        Log a security event with structured information.
        
        Args:
            event_type: Type of security event
            user_id: Optional user identifier
            ip_address: Optional IP address
            details: Optional additional event details
            severity: Log severity level
        """
        if details is None:
            details = {}
        
        # Create structured log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "severity": severity,
            "details": details
        }
        
        # Serialize to JSON for consistent format
        log_message = json.dumps(log_entry, default=str)
        
        with self._lock:
            # Log to file (not to console to maintain clean UI)
            import logging
            audit_logger = logging.getLogger("qwen_code.audit")
            audit_logger.setLevel(logging.INFO)
            
            # Create file handler for audit logs if not exists
            if not audit_logger.handlers:
                file_handler = logging.FileHandler(self.log_file_path)
                formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
                file_handler.setFormatter(formatter)
                audit_logger.addHandler(file_handler)
            
            if severity.upper() == "ERROR" or severity.upper() == "CRITICAL":
                audit_logger.error(log_message)
            elif severity.upper() == "WARNING":
                audit_logger.warning(log_message)
            else:
                audit_logger.info(log_message)
    
    def log_authentication_success(self, user_id: str, ip_address: Optional[str] = None) -> None:
        """Log successful authentication event."""
        self.log_security_event(
            SecurityEventType.AUTHENTICATION_SUCCESS,
            user_id=user_id,
            ip_address=ip_address,
            severity="INFO"
        )
    
    def log_authentication_failure(self, user_id: Optional[str], ip_address: Optional[str] = None, reason: Optional[str] = None) -> None:
        """Log authentication failure event."""
        self.log_security_event(
            SecurityEventType.AUTHENTICATION_FAILURE,
            user_id=user_id,
            ip_address=ip_address,
            details={"reason": reason} if reason else {},
            severity="WARNING"
        )
    
    def log_authorization_failure(self, user_id: str, resource: str, ip_address: Optional[str] = None) -> None:
        """Log authorization failure event."""
        self.log_security_event(
            SecurityEventType.AUTHORIZATION_FAILURE,
            user_id=user_id,
            ip_address=ip_address,
            details={"resource": resource},
            severity="WARNING"
        )
    
    def log_input_validation_failure(self, user_id: Optional[str], input_value: str, validation_rule: str, ip_address: Optional[str] = None) -> None:
        """Log input validation failure event."""
        self.log_security_event(
            SecurityEventType.INPUT_VALIDATION_FAILURE,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "input_value_preview": input_value[:50] if input_value else None,
                "validation_rule": validation_rule
            },
            severity="WARNING"
        )
    
    def log_rate_limit_exceeded(self, user_id: Optional[str], endpoint: str, ip_address: Optional[str] = None) -> None:
        """Log rate limit exceeded event."""
        self.log_security_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            details={"endpoint": endpoint},
            severity="WARNING"
        )
    
    def log_unauthorized_access(self, user_id: Optional[str], resource: str, ip_address: Optional[str] = None) -> None:
        """Log unauthorized access attempt."""
        self.log_security_event(
            SecurityEventType.UNAUTHORIZED_ACCESS,
            user_id=user_id,
            ip_address=ip_address,
            details={"resource": resource},
            severity="WARNING"
        )
    
    def log_suspicious_activity(self, user_id: Optional[str], activity: str, ip_address: Optional[str] = None) -> None:
        """Log suspicious activity."""
        self.log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            ip_address=ip_address,
            details={"activity": activity},
            severity="WARNING"
        )
    
    def log_credential_access(self, user_id: str, provider: str, ip_address: Optional[str] = None) -> None:
        """Log credential access event."""
        self.log_security_event(
            SecurityEventType.CREDENTIAL_ACCESS,
            user_id=user_id,
            ip_address=ip_address,
            details={"provider": provider},
            severity="INFO"
        )
    
    def log_credential_change(self, user_id: str, provider: str, ip_address: Optional[str] = None) -> None:
        """Log credential change event."""
        self.log_security_event(
            SecurityEventType.CREDENTIAL_CHANGE,
            user_id=user_id,
            ip_address=ip_address,
            details={"provider": provider},
            severity="INFO"
        )
    
    def log_config_change(self, user_id: str, config_key: str, old_value: Any, new_value: Any, ip_address: Optional[str] = None) -> None:
        """Log configuration change event."""
        self.log_security_event(
            SecurityEventType.CONFIG_CHANGE,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "config_key": config_key,
                "old_value_preview": str(old_value)[:50] if old_value else None,
                "new_value_preview": str(new_value)[:50] if new_value else None
            },
            severity="INFO"
        )
    
    def log_file_access(self, user_id: str, file_path: str, operation: str, ip_address: Optional[str] = None) -> None:
        """Log file access event."""
        self.log_security_event(
            SecurityEventType.FILE_ACCESS,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "file_path": file_path,
                "operation": operation
            },
            severity="INFO"
        )
    
    def log_api_call(self, user_id: Optional[str], endpoint: str, method: str, ip_address: Optional[str] = None) -> None:
        """Log API call event."""
        self.log_security_event(
            SecurityEventType.API_CALL,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "endpoint": endpoint,
                "method": method
            },
            severity="INFO"
        )
    
    def log_session_creation(self, session_id: str, user_id: Optional[str], ip_address: Optional[str] = None) -> None:
        """Log session creation event."""
        self.log_security_event(
            SecurityEventType.SESSION_CREATION,
            user_id=user_id,
            ip_address=ip_address,
            details={"session_id": session_id},
            severity="INFO"
        )
    
    def log_session_destruction(self, session_id: str, user_id: Optional[str], ip_address: Optional[str] = None) -> None:
        """Log session destruction event."""
        self.log_security_event(
            SecurityEventType.SESSION_DESTRUCTION,
            user_id=user_id,
            ip_address=ip_address,
            details={"session_id": session_id},
            severity="INFO"
        )


class SecurityMonitor:
    """
    Security monitoring component that integrates with the application.
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger or AuditLogger()
        self._active_sessions = set()
        self._monitored_endpoints = set()
    
    def add_monitored_endpoint(self, endpoint: str) -> None:
        """Add an endpoint to the list of monitored endpoints."""
        self._monitored_endpoints.add(endpoint)
    
    def log_and_monitor(self, event_type: SecurityEventType, **kwargs) -> None:
        """Log an event and perform any necessary monitoring actions."""
        self.audit_logger.log_security_event(event_type, **kwargs)
        
        # Perform additional monitoring based on event type
        if event_type == SecurityEventType.AUTHENTICATION_FAILURE:
            # Could implement account lockout logic here
            pass
        elif event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
            # Could implement temporary blocking logic here
            pass
        elif event_type == SecurityEventType.SUSPICIOUS_ACTIVITY:
            # Could implement alerting to security team
            # Only log to file, not to console for cleaner UI
            # logger.warning(f"Suspicious activity detected: {kwargs}")
            pass
    
    def monitor_authentication_success(self, user_id: str, ip_address: Optional[str] = None) -> None:
        """Monitor successful authentication."""
        self.log_and_monitor(SecurityEventType.AUTHENTICATION_SUCCESS, user_id=user_id, ip_address=ip_address)
    
    def monitor_authentication_failure(self, user_id: Optional[str], ip_address: Optional[str] = None, reason: Optional[str] = None) -> None:
        """Monitor authentication failure."""
        self.log_and_monitor(SecurityEventType.AUTHENTICATION_FAILURE, user_id=user_id, ip_address=ip_address, details={"reason": reason} if reason else {})
    
    def monitor_input_validation_failure(self, user_id: Optional[str], input_value: str, validation_rule: str, ip_address: Optional[str] = None) -> None:
        """Monitor input validation failure."""
        self.log_and_monitor(
            SecurityEventType.INPUT_VALIDATION_FAILURE,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "input_value_preview": input_value[:50] if input_value else None,
                "validation_rule": validation_rule
            }
        )
    
    def monitor_rate_limit_exceeded(self, user_id: Optional[str], endpoint: str, ip_address: Optional[str] = None) -> None:
        """Monitor rate limit exceeded."""
        self.log_and_monitor(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            details={"endpoint": endpoint}
        )


# Global audit logger and security monitor instances
audit_logger = AuditLogger()
security_monitor = SecurityMonitor(audit_logger)