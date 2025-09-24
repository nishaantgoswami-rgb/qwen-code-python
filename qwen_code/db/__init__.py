"""
Database module for Qwen Code.

This module provides database access functionality using SQLAlchemy ORM,
with support for migrations, encryption, and performance optimization.
"""

from .manager import DatabaseManager
from .migrations import MigrationManager, get_migration_manager
from .models import (
    Base,
    Session as SessionModel,
    Message as MessageModel,
    UserPreference,
    AuthToken,
    ProjectAnalysis,
    FileMetadata,
    UsageStats,
    ApiUsage,
    SessionStats
)
from .repositories import (
    SessionRepository,
    MessageRepository,
    ConfigRepository,
    AuthTokenRepository,
    ProjectAnalysisRepository,
    UsageStatsRepository,
    ApiUsageRepository
)
from .encryption import EncryptionManager
from .secure_credentials import SecureCredentialService


__all__ = [
    # Core classes
    "DatabaseManager",
    "MigrationManager",
    "get_migration_manager",
    
    # Models
    "Base",
    "SessionModel",
    "MessageModel",
    "UserPreference",
    "AuthToken",
    "ProjectAnalysis",
    "FileMetadata",
    "UsageStats",
    "ApiUsage",
    "SessionStats",
    
    # Repositories
    "SessionRepository",
    "MessageRepository", 
    "ConfigRepository",
    "AuthTokenRepository",
    "ProjectAnalysisRepository",
    "UsageStatsRepository",
    "ApiUsageRepository",
    
    # Security
    "EncryptionManager",
    "SecureCredentialService"
]