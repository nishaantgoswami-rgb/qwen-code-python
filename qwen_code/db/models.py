"""
SQLAlchemy models for Qwen Code database with enhanced performance indexing.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, JSON, Float, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Session(Base):
    """
    Session data model.
    """
    __tablename__ = 'sessions'

    id = Column(String, primary_key=True, index=True)
    project_path = Column(String, index=True)
    model = Column(String, nullable=False, index=True)  # Added index for model queries
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False, index=True)  # Added index
    updated_at = Column(DateTime, default=func.current_timestamp(), 
                        onupdate=func.current_timestamp(), nullable=False)
    token_count = Column(Integer, default=0, index=True)  # Added index
    is_active = Column(Boolean, default=True, index=True)
    metadata_ = Column("metadata", JSON)

    # Relationship to messages
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    stats = relationship("SessionStats", back_populates="session", uselist=False, cascade="all, delete-orphan")


class Message(Base):
    """
    Message data model.
    """
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String, CheckConstraint("role IN ('user', 'assistant', 'system')"), nullable=False, index=True)  # Added index
    content = Column(Text, nullable=False)
    token_count = Column(Integer, index=True)  # Added index for token count queries
    timestamp = Column(DateTime, default=func.current_timestamp(), nullable=False, index=True)
    metadata_ = Column("metadata", JSON)

    # Relationship to session
    session = relationship("Session", back_populates="messages")


class SessionStats(Base):
    """
    Session statistics data model.
    """
    __tablename__ = 'session_stats'

    session_id = Column(String, ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
    total_messages = Column(Integer, default=0, index=True)  # Added index
    total_tokens = Column(Integer, default=0, index=True)  # Added index
    user_messages = Column(Integer, default=0)
    assistant_messages = Column(Integer, default=0)
    average_response_time = Column(Float)
    last_activity = Column(DateTime, index=True)  # Added index

    # Relationship to session
    session = relationship("Session", back_populates="stats")


class UserPreference(Base):
    """
    User preference data model.
    """
    __tablename__ = 'user_preferences'

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    type = Column(String, CheckConstraint("type IN ('string', 'integer', 'float', 'boolean', 'json')"), nullable=False, index=True)  # Added index
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False, index=True)  # Added index
    updated_at = Column(DateTime, default=func.current_timestamp(), 
                        onupdate=func.current_timestamp(), nullable=False)


class AuthToken(Base):
    """
    Authentication token data model with encrypted storage.
    """
    __tablename__ = 'auth_tokens'

    provider = Column(String, primary_key=True)
    encrypted_access_token = Column(Text, nullable=False)  # Encrypted access token
    encrypted_refresh_token = Column(Text)  # Encrypted refresh token
    expires_at = Column(DateTime, index=True)  # Added index for expiration queries
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False, index=True)  # Added index
    updated_at = Column(DateTime, default=func.current_timestamp(),
                        onupdate=func.current_timestamp(), nullable=False)


class ProjectAnalysis(Base):
    """
    Project analysis data model.
    """
    __tablename__ = 'project_analysis'

    project_path = Column(String, primary_key=True)
    total_files = Column(Integer, index=True)  # Added index
    total_lines = Column(Integer, index=True)  # Added index
    languages = Column(JSON)
    dependencies = Column(JSON)
    structure = Column(JSON)
    last_analyzed = Column(DateTime, default=func.current_timestamp(), nullable=False, index=True)  # Added index
    analysis_version = Column(String, index=True)  # Added index


class FileMetadata(Base):
    """
    File metadata data model.
    """
    __tablename__ = 'file_metadata'

    file_path = Column(String, primary_key=True)
    project_path = Column(String, ForeignKey('project_analysis.project_path'), index=True)
    file_type = Column(String, index=True)
    size_bytes = Column(Integer, index=True)  # Added index
    lines_count = Column(Integer, index=True)  # Added index
    last_modified = Column(DateTime, index=True)  # Added index
    content_hash = Column(String, index=True)  # Added index for hash comparisons
    analysis_data = Column(JSON)

    # Relationship to project analysis
    project_analysis = relationship("ProjectAnalysis", back_populates="files")


# Define relationship on ProjectAnalysis side
ProjectAnalysis.files = relationship("FileMetadata", back_populates="project_analysis")


class UsageStats(Base):
    """
    Usage statistics data model.
    """
    __tablename__ = 'usage_stats'

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    event_data = Column(JSON)
    timestamp = Column(DateTime, default=func.current_timestamp(), nullable=False, index=True)
    session_id = Column(String, index=True)  # Added index
    user_id = Column(String, index=True)  # Added index


class ApiUsage(Base):
    """
    API usage data model.
    """
    __tablename__ = 'api_usage'

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)  # Added index
    prompt_tokens = Column(Integer, index=True)  # Added index
    completion_tokens = Column(Integer, index=True)  # Added index
    total_tokens = Column(Integer, index=True)  # Added index
    cost_estimate = Column(Float, index=True)  # Added index
    timestamp = Column(DateTime, default=func.current_timestamp(), nullable=False, index=True)
    session_id = Column(String, index=True)  # Added index


# Define additional composite indexes for performance
Index('idx_messages_session_timestamp', Message.session_id, Message.timestamp)
Index('idx_messages_role_timestamp', Message.role, Message.timestamp)  # Additional index
Index('idx_sessions_project_active', Session.project_path, Session.is_active)
Index('idx_sessions_model_active', Session.model, Session.is_active)  # Additional index
Index('idx_file_metadata_project_type', FileMetadata.project_path, FileMetadata.file_type)
Index('idx_file_metadata_type_size', FileMetadata.file_type, FileMetadata.size_bytes)  # Additional index
Index('idx_usage_stats_type_timestamp', UsageStats.event_type, UsageStats.timestamp)
Index('idx_usage_stats_session_timestamp', UsageStats.session_id, UsageStats.timestamp)  # Additional index
Index('idx_api_usage_provider_timestamp', ApiUsage.provider, ApiUsage.timestamp)  # Additional index
Index('idx_api_usage_model_timestamp', ApiUsage.model, ApiUsage.timestamp)  # Additional index