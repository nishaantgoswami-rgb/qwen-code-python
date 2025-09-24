"""
Enhanced database repositories for Qwen Code using SQLAlchemy ORM.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_
from qwen_code.db.models import (
    Session as SessionModel, Message as MessageModel, 
    UserPreference, AuthToken, ProjectAnalysis, 
    FileMetadata, UsageStats, ApiUsage, SessionStats
)
from qwen_code.db.secure_credentials import SecureCredentialService
from qwen_code.utils.logging import get_logger


logger = get_logger()


class SessionRepository:
    """Repository for session data operations using SQLAlchemy ORM."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_session(self, session_data: Dict[str, Any]) -> SessionModel:
        """Create new session."""
        session = SessionModel(
            id=session_data["id"],
            project_path=session_data.get("project_path"),
            model=session_data["model"],
            token_count=session_data.get("token_count", 0),
            is_active=session_data.get("is_active", True),
            metadata_=session_data.get("metadata")
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        logger.info(f"Created session: {session.id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Retrieve session by ID with optimized query."""
        session = (
            self.db.query(SessionModel)
            .filter(SessionModel.id == session_id)
            .first()
        )
        if session:
            logger.debug(f"Retrieved session: {session_id}")
        else:
            logger.debug(f"Session not found: {session_id}")
        return session
    
    def get_session_with_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session with associated stats in a single query for performance."""
        result = (
            self.db.query(SessionModel, SessionStats)
            .outerjoin(SessionStats, SessionModel.id == SessionStats.session_id)
            .filter(SessionModel.id == session_id)
            .first()
        )
        
        if result:
            session, stats = result
            return {"session": session, "stats": stats}
        return None
    
    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> Optional[SessionModel]:
        """Update existing session with atomic transaction."""
        try:
            session = (
                self.db.query(SessionModel)
                .filter(SessionModel.id == session_id)
                .with_for_update()  # Lock row for update
                .first()
            )
            
            if not session:
                return None
            
            for key, value in update_data.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(session)
            logger.info(f"Updated session: {session_id}")
            return session
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update session {session_id}: {str(e)}")
            raise
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and related data with CASCADE handling."""
        try:
            # Using the delete trigger should handle cascading deletes automatically due to CASCADE constraint
            result = self.db.query(SessionModel).filter(SessionModel.id == session_id).delete()
            self.db.commit()
            
            if result > 0:
                logger.info(f"Deleted session: {session_id}")
                return True
            else:
                logger.debug(f"Session not found for deletion: {session_id}")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete session {session_id}: {str(e)}")
            raise
    
    def get_active_sessions(self, project_path: Optional[str] = None) -> List[SessionModel]:
        """Get active sessions with optional project filtering, optimized with indexes."""
        query = self.db.query(SessionModel).filter(SessionModel.is_active == True)
        
        if project_path:
            query = query.filter(SessionModel.project_path == project_path)
        
        # Order by most recently updated for better UX
        sessions = query.order_by(desc(SessionModel.updated_at)).all()
        logger.debug(f"Retrieved {len(sessions)} active sessions")
        return sessions
    
    def get_sessions_by_project(self, project_path: str) -> List[SessionModel]:
        """Get all sessions for a specific project with optimized query."""
        sessions = (
            self.db.query(SessionModel)
            .filter(SessionModel.project_path == project_path)
            .order_by(desc(SessionModel.created_at))
            .all()
        )
        logger.debug(f"Retrieved {len(sessions)} sessions for project: {project_path}")
        return sessions
    
    def get_session_count_by_model(self) -> Dict[str, int]:
        """Get session count grouped by model for analytics."""
        results = (
            self.db.query(SessionModel.model, func.count(SessionModel.id))
            .filter(SessionModel.is_active == True)
            .group_by(SessionModel.model)
            .all()
        )
        
        return {model: count for model, count in results}


class MessageRepository:
    """Repository for message data operations using SQLAlchemy ORM."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def add_message(self, session_id: str, message_data: Dict[str, Any]) -> MessageModel:
        """Add message to session with transaction safety."""
        try:
            message = MessageModel(
                session_id=session_id,
                role=message_data["role"],
                content=message_data["content"],
                token_count=message_data.get("token_count"),
                metadata_=message_data.get("metadata")
            )
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            logger.debug(f"Added message to session: {session_id}")
            return message
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add message to session {session_id}: {str(e)}")
            raise
    
    def add_messages_bulk(self, session_id: str, messages_data: List[Dict[str, Any]]) -> int:
        """Add multiple messages in bulk for better performance."""
        try:
            messages = [
                MessageModel(
                    session_id=session_id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    token_count=msg_data.get("token_count"),
                    metadata_=msg_data.get("metadata")
                )
                for msg_data in messages_data
            ]
            
            self.db.bulk_insert_mappings(MessageModel, [
                {
                    "session_id": session_id,
                    "role": msg_data["role"],
                    "content": msg_data["content"],
                    "token_count": msg_data.get("token_count"),
                    "metadata_": msg_data.get("metadata")
                }
                for msg_data in messages_data
            ])
            self.db.commit()
            
            logger.debug(f"Added {len(messages_data)} messages in bulk to session: {session_id}")
            return len(messages_data)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add messages in bulk to session {session_id}: {str(e)}")
            raise
    
    def get_messages(self, session_id: str, limit: Optional[int] = None, 
                    order_by: str = "timestamp", order_dir: str = "asc") -> List[MessageModel]:
        """Get messages for session with optional limit and ordering."""
        query = self.db.query(MessageModel).filter(MessageModel.session_id == session_id)
        
        # Apply ordering
        if order_by == "timestamp":
            if order_dir == "desc":
                query = query.order_by(desc(MessageModel.timestamp))
            else:
                query = query.order_by(asc(MessageModel.timestamp))
        elif order_by == "id":
            if order_dir == "desc":
                query = query.order_by(desc(MessageModel.id))
            else:
                query = query.order_by(asc(MessageModel.id))
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        messages = query.all()
        logger.debug(f"Retrieved {len(messages)} messages for session: {session_id}")
        return messages
    
    def get_messages_paginated(self, session_id: str, offset: int = 0, limit: int = 50) -> List[MessageModel]:
        """Get messages with pagination for large conversations."""
        messages = (
            self.db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(asc(MessageModel.timestamp))
            .offset(offset)
            .limit(limit)
            .all()
        )
        logger.debug(f"Retrieved {len(messages)} messages for session: {session_id} (offset: {offset}, limit: {limit})")
        return messages
    
    def get_recent_messages(self, session_id: str, limit: int = 50) -> List[MessageModel]:
        """Get recent messages for session with optimized query."""
        messages = (
            self.db.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(desc(MessageModel.timestamp))
            .limit(limit)
            .all()
        )
        logger.debug(f"Retrieved {len(messages)} recent messages for session: {session_id}")
        return messages
    
    def count_messages_by_role(self, session_id: str) -> Dict[str, int]:
        """Count messages by role in a session efficiently."""
        results = (
            self.db.query(MessageModel.role, func.count(MessageModel.id))
            .filter(MessageModel.session_id == session_id)
            .group_by(MessageModel.role)
            .all()
        )
        return {role: count for role, count in results}
    
    def delete_old_messages(self, session_id: str, keep_count: int) -> int:
        """Delete old messages keeping specified count using efficient subquery."""
        try:
            # Get the ID threshold (messages with IDs below this will be deleted)
            threshold_result = (
                self.db.query(MessageModel.id)
                .filter(MessageModel.session_id == session_id)
                .order_by(desc(MessageModel.timestamp))
                .offset(keep_count - 1)  # -1 because offset is 0-based
                .limit(1)
                .first()
            )
            
            if threshold_result is None:
                # Not enough messages to delete
                return 0
            
            threshold_id = threshold_result.id
            
            # Delete messages with IDs less than the threshold
            deleted_count = (
                self.db.query(MessageModel)
                .filter(
                    MessageModel.session_id == session_id,
                    MessageModel.id < threshold_id
                )
                .delete(synchronize_session=False)
            )
            
            self.db.commit()
            logger.info(f"Deleted {deleted_count} old messages for session: {session_id}, kept {keep_count}")
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete old messages for session {session_id}: {str(e)}")
            raise
    
    def get_session_message_count(self, session_id: str) -> int:
        """Get total message count for a session efficiently."""
        count = (
            self.db.query(func.count(MessageModel.id))
            .filter(MessageModel.session_id == session_id)
            .scalar()
        )
        return count or 0


class ConfigRepository:
    """Repository for configuration data using SQLAlchemy ORM."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_preference(self, key: str) -> Any:
        """Get user preference value."""
        pref = self.db.query(UserPreference).filter(UserPreference.key == key).first()
        if not pref:
            logger.debug(f"Preference not found: {key}")
            return None
        
        value, type_ = pref.value, pref.type
        logger.debug(f"Retrieved preference: {key}")
        
        if type_ == "string":
            return value
        elif type_ == "integer":
            return int(value)
        elif type_ == "float":
            return float(value)
        elif type_ == "boolean":
            return value.lower() == "true"
        elif type_ == "json":
            return json.loads(value)
        else:
            return value
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set user preference value."""
        # Determine type
        if isinstance(value, str):
            type_ = "string"
        elif isinstance(value, int):
            type_ = "integer"
        elif isinstance(value, float):
            type_ = "float"
        elif isinstance(value, bool):
            type_ = "boolean"
            value = str(value).lower()
        else:
            type_ = "json"
            value = json.dumps(value)
        
        pref = self.db.query(UserPreference).filter(UserPreference.key == key).first()
        if pref:
            # Update existing
            pref.value = str(value)
            pref.type = type_
            pref.updated_at = datetime.utcnow()
        else:
            # Create new
            pref = UserPreference(key=key, value=str(value), type=type_)
            self.db.add(pref)
        
        self.db.commit()
        logger.info(f"Set preference: {key} = {value}")
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        preferences = {}
        for pref in self.db.query(UserPreference).all():
            if pref.type == "string":
                preferences[pref.key] = pref.value
            elif pref.type == "integer":
                preferences[pref.key] = int(pref.value)
            elif pref.type == "float":
                preferences[pref.key] = float(pref.value)
            elif pref.type == "boolean":
                preferences[pref.key] = pref.value.lower() == "true"
            elif pref.type == "json":
                preferences[pref.key] = json.loads(pref.value)
            else:
                preferences[pref.key] = pref.value
        
        logger.debug(f"Retrieved {len(preferences)} preferences")
        return preferences
    
    def delete_preference(self, key: str) -> bool:
        """Delete user preference."""
        pref = self.db.query(UserPreference).filter(UserPreference.key == key).first()
        if not pref:
            return False
        
        self.db.delete(pref)
        self.db.commit()
        logger.info(f"Deleted preference: {key}")
        return True


class AuthTokenRepository:
    """Repository for authentication tokens with encryption support."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.secure_service = SecureCredentialService()
    
    def store_token(self, provider: str, access_token: str, 
                   refresh_token: Optional[str] = None, expires_at: Optional[datetime] = None) -> None:
        """Store authentication token with encryption."""
        self.secure_service.store_token_encrypted(
            self.db, provider, access_token, refresh_token, expires_at
        )
    
    def get_token(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get authentication token for provider with decryption."""
        return self.secure_service.get_token_decrypted(self.db, provider)
    
    def refresh_token(self, provider: str, new_access_token: str, 
                     new_expires_at: Optional[datetime] = None) -> bool:
        """Update token after refresh."""
        token_data = self.get_token(provider)
        if not token_data:
            return False
        
        self.secure_service.store_token_encrypted(
            self.db, provider, new_access_token, 
            token_data.get("refresh_token"), new_expires_at
        )
        return True
    
    def delete_token(self, provider: str) -> bool:
        """Delete authentication token."""
        return self.secure_service.delete_token(self.db, provider)
    
    def is_token_expired(self, provider: str) -> bool:
        """Check if authentication token is expired."""
        token_data = self.get_token(provider)
        if not token_data:
            return True
        return self.secure_service.is_token_expired(token_data)


class ProjectAnalysisRepository:
    """Repository for project analysis data using SQLAlchemy ORM."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def store_analysis(self, project_path: str, analysis_data: Dict[str, Any]) -> None:
        """Store project analysis results."""
        analysis = self.db.query(ProjectAnalysis).filter(ProjectAnalysis.project_path == project_path).first()
        
        if analysis:
            # Update existing analysis
            analysis.total_files = analysis_data.get("total_files")
            analysis.total_lines = analysis_data.get("total_lines")
            analysis.languages = analysis_data.get("languages")
            analysis.dependencies = analysis_data.get("dependencies")
            analysis.structure = analysis_data.get("structure")
            analysis.last_analyzed = datetime.utcnow()
            analysis.analysis_version = analysis_data.get("analysis_version")
        else:
            # Create new analysis
            analysis = ProjectAnalysis(
                project_path=project_path,
                total_files=analysis_data.get("total_files"),
                total_lines=analysis_data.get("total_lines"),
                languages=analysis_data.get("languages"),
                dependencies=analysis_data.get("dependencies"),
                structure=analysis_data.get("structure"),
                analysis_version=analysis_data.get("analysis_version")
            )
            self.db.add(analysis)
        
        self.db.commit()
        logger.info(f"Stored project analysis for: {project_path}")
    
    def get_analysis(self, project_path: str) -> Optional[ProjectAnalysis]:
        """Get cached project analysis."""
        analysis = self.db.query(ProjectAnalysis).filter(ProjectAnalysis.project_path == project_path).first()
        if analysis:
            logger.debug(f"Retrieved project analysis for: {project_path}")
        else:
            logger.debug(f"No analysis found for project: {project_path}")
        return analysis
    
    def is_analysis_stale(self, project_path: str, max_age_hours: int = 24) -> bool:
        """Check if analysis needs refresh based on age."""
        analysis = self.get_analysis(project_path)
        if not analysis:
            return True
        
        age = datetime.utcnow() - analysis.last_analyzed
        max_age = max_age_hours * 3600  # Convert hours to seconds
        
        is_stale = age.total_seconds() > max_age
        if is_stale:
            logger.debug(f"Project analysis is stale for: {project_path}")
        return is_stale
    
    def update_file_metadata(self, file_path: str, metadata: Dict[str, Any]) -> None:
        """Update file metadata cache."""
        file_meta = self.db.query(FileMetadata).filter(FileMetadata.file_path == file_path).first()
        
        if file_meta:
            # Update existing metadata
            file_meta.project_path = metadata.get("project_path", file_meta.project_path)
            file_meta.file_type = metadata.get("file_type", file_meta.file_type)
            file_meta.size_bytes = metadata.get("size_bytes", file_meta.size_bytes)
            file_meta.lines_count = metadata.get("lines_count", file_meta.lines_count)
            file_meta.last_modified = metadata.get("last_modified", file_meta.last_modified)
            file_meta.content_hash = metadata.get("content_hash", file_meta.content_hash)
            file_meta.analysis_data = metadata.get("analysis_data", file_meta.analysis_data)
        else:
            # Create new metadata
            file_meta = FileMetadata(
                file_path=file_path,
                project_path=metadata.get("project_path"),
                file_type=metadata.get("file_type"),
                size_bytes=metadata.get("size_bytes"),
                lines_count=metadata.get("lines_count"),
                last_modified=metadata.get("last_modified"),
                content_hash=metadata.get("content_hash"),
                analysis_data=metadata.get("analysis_data")
            )
            self.db.add(file_meta)
        
        self.db.commit()
        logger.debug(f"Updated file metadata: {file_path}")
    
    def get_project_files(self, project_path: str) -> List[FileMetadata]:
        """Get cached file metadata for project."""
        files = self.db.query(FileMetadata).filter(FileMetadata.project_path == project_path).all()
        logger.debug(f"Retrieved {len(files)} file metadata entries for project: {project_path}")
        return files
    
    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """Get metadata for a specific file."""
        file_meta = self.db.query(FileMetadata).filter(FileMetadata.file_path == file_path).first()
        if file_meta:
            logger.debug(f"Retrieved file metadata: {file_path}")
        else:
            logger.debug(f"No metadata found for file: {file_path}")
        return file_meta


class UsageStatsRepository:
    """Repository for usage statistics data using SQLAlchemy ORM."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def log_event(self, event_type: str, event_data: Dict[str, Any], 
                 session_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
        """Log a usage event efficiently."""
        try:
            usage_stat = UsageStats(
                event_type=event_type,
                event_data=event_data,
                session_id=session_id,
                user_id=user_id
            )
            self.db.add(usage_stat)
            # For high-volume logging, consider using commit less frequently or bulk operations
            self.db.commit()
            logger.debug(f"Logged usage event: {event_type}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log usage event {event_type}: {str(e)}")
            raise
    
    def log_events_bulk(self, events_data: List[Dict[str, Any]]) -> int:
        """Log multiple events in bulk for better performance."""
        try:
            events = [
                UsageStats(
                    event_type=event["event_type"],
                    event_data=event["event_data"],
                    session_id=event.get("session_id"),
                    user_id=event.get("user_id")
                )
                for event in events_data
            ]
            
            self.db.bulk_insert_mappings(UsageStats, [
                {
                    "event_type": event["event_type"],
                    "event_data": event["event_data"],
                    "session_id": event.get("session_id"),
                    "user_id": event.get("user_id")
                }
                for event in events_data
            ])
            self.db.commit()
            
            logger.debug(f"Logged {len(events_data)} events in bulk")
            return len(events_data)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log events in bulk: {str(e)}")
            raise
    
    def get_usage_stats(self, event_type: Optional[str] = None, 
                       start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None) -> List[UsageStats]:
        """Get usage statistics with optional filtering."""
        query = self.db.query(UsageStats)
        
        if event_type:
            query = query.filter(UsageStats.event_type == event_type)
        
        if start_date:
            query = query.filter(UsageStats.timestamp >= start_date)
        
        if end_date:
            query = query.filter(UsageStats.timestamp <= end_date)
        
        # Order by timestamp for chronological order
        stats = query.order_by(UsageStats.timestamp).all()
        logger.debug(f"Retrieved {len(stats)} usage statistics")
        return stats
    
    def get_usage_count_by_type(self, start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, int]:
        """Get count of usage events grouped by type for analytics."""
        query = self.db.query(UsageStats.event_type, func.count(UsageStats.id))
        
        if start_date:
            query = query.filter(UsageStats.timestamp >= start_date)
        
        if end_date:
            query = query.filter(UsageStats.timestamp <= end_date)
        
        results = query.group_by(UsageStats.event_type).all()
        return {event_type: count for event_type, count in results}
    
    def get_daily_usage(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get daily usage statistics for the specified number of days."""
        from datetime import timedelta
        
        # Get events in the last n days grouped by date and type
        results = (
            self.db.query(
                func.date(UsageStats.timestamp).label('date'),
                UsageStats.event_type,
                func.count(UsageStats.id).label('count')
            )
            .filter(UsageStats.timestamp >= (datetime.utcnow() - timedelta(days=days_back)))
            .group_by(func.date(UsageStats.timestamp), UsageStats.event_type)
            .order_by(func.date(UsageStats.timestamp).desc(), UsageStats.event_type)
            .all()
        )
        
        daily_stats = []
        for result in results:
            daily_stats.append({
                "date": result.date,
                "event_type": result.event_type,
                "count": result.count
            })
        
        logger.debug(f"Retrieved daily usage stats for last {days_back} days")
        return daily_stats
    
    def get_usage_summary(self, start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive usage summary for reporting."""
        query = self.db.query(UsageStats)
        
        if start_date:
            query = query.filter(UsageStats.timestamp >= start_date)
        
        if end_date:
            query = query.filter(UsageStats.timestamp <= end_date)
        
        total_count = query.count()
        
        # Get count by event type
        type_counts = (
            self.db.query(UsageStats.event_type, func.count(UsageStats.id))
            .filter(UsageStats.timestamp >= (start_date or datetime.min))
            .filter(UsageStats.timestamp <= (end_date or datetime.max))
            .group_by(UsageStats.event_type)
            .all()
        )
        
        # Get date range
        date_range = (
            self.db.query(
                func.min(UsageStats.timestamp),
                func.max(UsageStats.timestamp)
            )
            .filter(UsageStats.timestamp >= (start_date or datetime.min))
            .filter(UsageStats.timestamp <= (end_date or datetime.max))
            .first()
        )
        
        return {
            "total_events": total_count,
            "event_types_count": dict(type_counts),
            "date_range": {"start": date_range[0], "end": date_range[1]} if date_range else None
        }


class ApiUsageRepository:
    """Repository for API usage data using SQLAlchemy ORM."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def log_api_call(self, provider: str, model: str, 
                    prompt_tokens: int, completion_tokens: int, 
                    total_tokens: int, cost_estimate: float,
                    session_id: Optional[str] = None) -> None:
        """Log an API usage event."""
        api_usage = ApiUsage(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_estimate=cost_estimate,
            session_id=session_id
        )
        self.db.add(api_usage)
        self.db.commit()
        logger.debug(f"Logged API usage for provider: {provider}, model: {model}")
    
    def get_provider_usage(self, provider: str, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> List[ApiUsage]:
        """Get API usage for a specific provider with optional date filtering."""
        query = self.db.query(ApiUsage).filter(ApiUsage.provider == provider)
        
        if start_date:
            query = query.filter(ApiUsage.timestamp >= start_date)
        
        if end_date:
            query = query.filter(ApiUsage.timestamp <= end_date)
        
        usage = query.all()
        logger.debug(f"Retrieved {len(usage)} API usage records for provider: {provider}")
        return usage
    
    def get_total_usage(self, start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> Dict[str, int]:
        """Get total usage statistics with optional date filtering."""
        query = self.db.query(ApiUsage)
        
        if start_date:
            query = query.filter(ApiUsage.timestamp >= start_date)
        
        if end_date:
            query = query.filter(ApiUsage.timestamp <= end_date)
        
        total_usage = query.all()
        
        total_stats = {
            "total_calls": len(total_usage),
            "total_prompt_tokens": sum(usage.prompt_tokens or 0 for usage in total_usage),
            "total_completion_tokens": sum(usage.completion_tokens or 0 for usage in total_usage),
            "total_tokens": sum(usage.total_tokens or 0 for usage in total_usage),
            "total_cost": sum(usage.cost_estimate or 0 for usage in total_usage)
        }
        
        logger.debug(f"Calculated total usage: {total_stats}")
        return total_stats