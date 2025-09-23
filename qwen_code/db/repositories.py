"""
Database repositories for Qwen Code.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import sqlite3
from qwen_code.db.manager import DatabaseManager
# Import Session and Message locally in methods to avoid circular imports


class SessionRepository:
    """Repository for session data operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_session(self, session) -> None:  # Accept session object without type hint
        """Create new session."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        # Import Session locally to avoid circular imports
        from qwen_code.session.manager import Session
        
        if not isinstance(session, Session):
            raise TypeError("session must be a Session instance")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            INSERT INTO sessions (
                id, project_path, model, token_count, is_active, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session.id,
            session.project_path,
            session.model,
            session.token_count,
            session.is_active,
            json.dumps(session.metadata) if session.metadata else None
        ))
        self.db.connection.commit()
    
    async def get_session(self, session_id: str):
        """Retrieve session by ID."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        # Import Session locally to avoid circular imports
        from qwen_code.session.manager import Session
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT * FROM sessions WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return Session(
            id=row["id"],
            project_path=row["project_path"],
            model=row["model"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            token_count=row["token_count"],
            is_active=row["is_active"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
    
    async def update_session(self, session) -> None:  # Accept session object without type hint
        """Update existing session."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        # Import Session locally to avoid circular imports
        from qwen_code.session.manager import Session
        
        if not isinstance(session, Session):
            raise TypeError("session must be a Session instance")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            UPDATE sessions SET
                project_path = ?, model = ?, updated_at = ?,
                token_count = ?, is_active = ?, metadata = ?
            WHERE id = ?
        """, (
            session.project_path,
            session.model,
            datetime.now().isoformat(),
            session.token_count,
            session.is_active,
            json.dumps(session.metadata) if session.metadata else None,
            session.id
        ))
        self.db.connection.commit()
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session and related data."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            DELETE FROM sessions WHERE id = ?
        """, (session_id,))
        self.db.connection.commit()
    
    async def get_active_sessions(self, project_path: str = None):
        """Get active sessions, optionally filtered by project."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        # Import Session locally to avoid circular imports
        from qwen_code.session.manager import Session
        
        cursor = self.db.connection.cursor()
        if project_path:
            cursor.execute("""
                SELECT * FROM sessions WHERE is_active = ? AND project_path = ?
            """, (True, project_path))
        else:
            cursor.execute("""
                SELECT * FROM sessions WHERE is_active = ?
            """, (True,))
        
        rows = cursor.fetchall()
        sessions = []
        for row in rows:
            sessions.append(Session(
                id=row["id"],
                project_path=row["project_path"],
                model=row["model"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                token_count=row["token_count"],
                is_active=row["is_active"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            ))
        
        return sessions


class MessageRepository:
    """Repository for message data operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def add_message(self, session_id: str, message) -> None:  # Accept message object without type hint
        """Add message to session."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        # Import Message locally to avoid circular imports
        from qwen_code.ai.client import Message
        
        if not isinstance(message, Message):
            raise TypeError("message must be a Message instance")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            INSERT INTO messages (
                session_id, role, content, token_count, metadata
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            message.role,
            message.content,
            getattr(message, 'token_count', None),  # Not in current Message definition
            json.dumps({})  # Empty metadata for now
        ))
        self.db.connection.commit()
    
    async def get_messages(self, session_id: str):
        """Get messages for session."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        # Import Message locally to avoid circular imports
        from qwen_code.ai.client import Message
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC
        """, (session_id,))
        
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            messages.append(Message(
                role=row["role"],
                content=row["content"]
            ))
        
        return messages
    
    async def delete_old_messages(self, session_id: str, keep_count: int) -> None:
        """Delete old messages keeping specified count."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            DELETE FROM messages WHERE session_id = ? AND id NOT IN (
                SELECT id FROM messages WHERE session_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            )
        """, (session_id, session_id, keep_count))
        self.db.connection.commit()


class ConfigRepository:
    """Repository for configuration data."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def get_preference(self, key: str) -> Any:
        """Get user preference value."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT value, type FROM user_preferences WHERE key = ?
        """, (key,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        value, type_ = row["value"], row["type"]
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
    
    async def set_preference(self, key: str, value: Any) -> None:
        """Set user preference value."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
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
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_preferences (key, value, type)
            VALUES (?, ?, ?)
        """, (key, str(value), type_))
        self.db.connection.commit()
    
    async def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT key, value, type FROM user_preferences
        """)
        
        rows = cursor.fetchall()
        preferences = {}
        for row in rows:
            key, value, type_ = row["key"], row["value"], row["type"]
            if type_ == "string":
                preferences[key] = value
            elif type_ == "integer":
                preferences[key] = int(value)
            elif type_ == "float":
                preferences[key] = float(value)
            elif type_ == "boolean":
                preferences[key] = value.lower() == "true"
            elif type_ == "json":
                preferences[key] = json.loads(value)
            else:
                preferences[key] = value
        
        return preferences
    
    async def delete_preference(self, key: str) -> None:
        """Delete user preference."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            DELETE FROM user_preferences WHERE key = ?
        """, (key,))
        self.db.connection.commit()


class AuthTokenRepository:
    """Repository for authentication tokens."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def store_token(self, provider: str, access_token: str, 
                         refresh_token: str = None, expires_at: datetime = None) -> None:
        """Store authentication token."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO auth_tokens (
                provider, access_token, refresh_token, expires_at
            ) VALUES (?, ?, ?, ?)
        """, (
            provider,
            access_token,
            refresh_token,
            expires_at.isoformat() if expires_at else None
        ))
        self.db.connection.commit()
    
    async def get_token(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get authentication token for provider."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT * FROM auth_tokens WHERE provider = ?
        """, (provider,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "provider": row["provider"],
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "expires_at": datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            "created_at": datetime.fromisoformat(row["created_at"]),
            "updated_at": datetime.fromisoformat(row["updated_at"])
        }
    
    async def refresh_token(self, provider: str, new_access_token: str, 
                           new_expires_at: datetime = None) -> None:
        """Update token after refresh."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            UPDATE auth_tokens SET
                access_token = ?, expires_at = ?, updated_at = ?
            WHERE provider = ?
        """, (
            new_access_token,
            new_expires_at.isoformat() if new_expires_at else None,
            datetime.now().isoformat(),
            provider
        ))
        self.db.connection.commit()
    
    async def delete_token(self, provider: str) -> None:
        """Delete authentication token."""
        if not self.db.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.db.connection.cursor()
        cursor.execute("""
            DELETE FROM auth_tokens WHERE provider = ?
        """, (provider,))
        self.db.connection.commit()