"""Session management for Qwen Code."""

import uuid
import json
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from qwen_code.ai.client import Message
from qwen_code.config.settings import SessionConfig
from qwen_code.db.manager import DatabaseManager


@dataclass
class Session:
    """Conversation session data."""
    id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    model: str = "qwen3-coder-plus"
    project_path: Optional[str] = None
    is_active: bool = True
    metadata: dict = field(default_factory=dict)
    
    def add_message(self, message: Message) -> None:
        """Add message to session."""
        self.messages.append(message)
        self.updated_at = datetime.now()
        # In a real implementation, we would calculate actual token count
        # For now, we'll use a simple approximation
        self.token_count += len(message.content.split())
    
    def compress_history(self, target_tokens: int) -> None:
        """Compress conversation history to target token count."""
        # Simple compression: remove oldest messages until we're under the target
        # In a real implementation, we might use more sophisticated techniques
        while self.token_count > target_tokens and len(self.messages) > 2:
            # Keep the first message (system prompt) if it exists
            removed_message = self.messages.pop(1)  # Remove second message (first user message)
            self.token_count -= len(removed_message.content.split())


class SessionManager:
    """Manages conversation sessions and state."""
    
    def __init__(self, config: SessionConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        from qwen_code.db.repositories import SessionRepository, MessageRepository
        self.session_repo = SessionRepository(db_manager)
        self.message_repo = MessageRepository(db_manager)
        self.current_session: Optional[Session] = None
    
    async def create_session(self, project_path: Optional[str] = None, model: Optional[str] = None) -> Session:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        session_model = model or self.config.model_settings.default_model if hasattr(self.config, 'model_settings') else "qwen3-coder-plus"
        
        self.current_session = Session(
            id=session_id, 
            project_path=project_path,
            model=session_model
        )
        await self.session_repo.create_session(self.current_session)
        return self.current_session
    
    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load existing session from storage."""
        session = await self.session_repo.get_session(session_id)
        if session:
            # Load messages for the session
            messages = await self.message_repo.get_messages(session_id)
            session.messages = messages
            self.current_session = session
        return session
    
    async def save_session(self) -> None:
        """Persist current session to storage."""
        if self.current_session:
            await self.session_repo.update_session(self.current_session)
    
    async def add_message_to_session(self, message: Message) -> None:
        """Add a message to the current session."""
        if not self.current_session:
            raise RuntimeError("No active session")
        
        # Add message to session in memory
        self.current_session.add_message(message)
        
        # Save message to database
        await self.message_repo.add_message(self.current_session.id, message)
        
        # Update session in database
        await self.session_repo.update_session(self.current_session)
    
    async def compress_current_session(self) -> None:
        """Compress the current session history."""
        if not self.current_session:
            raise RuntimeError("No active session")
        
        target_tokens = int(self.config.token_limit * self.config.compression_threshold)
        self.current_session.compress_history(target_tokens)
        
        # Update session in database
        await self.session_repo.update_session(self.current_session)
        
        # Delete old messages from database
        # Keep the most recent messages that fit within our target
        await self.message_repo.delete_old_messages(
            self.current_session.id, 
            len(self.current_session.messages)
        )
    
    def get_session_stats(self) -> dict:
        """Get current session statistics."""
        if not self.current_session:
            return {}
        
        user_messages = sum(1 for msg in self.current_session.messages if msg.role == "user")
        assistant_messages = sum(1 for msg in self.current_session.messages if msg.role == "assistant")
        
        return {
            "session_id": self.current_session.id,
            "total_messages": len(self.current_session.messages),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "token_count": self.current_session.token_count,
            "model": self.current_session.model,
            "created_at": self.current_session.created_at.isoformat(),
            "updated_at": self.current_session.updated_at.isoformat()
        }
    
    async def get_active_sessions(self, project_path: str = None) -> List[Session]:
        """Get active sessions, optionally filtered by project."""
        return await self.session_repo.get_active_sessions(project_path)
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        await self.session_repo.delete_session(session_id)
        
        # If we're deleting the current session, clear it
        if self.current_session and self.current_session.id == session_id:
            self.current_session = None
    
    async def list_sessions(self, limit: int = 10) -> List[dict]:
        """List recent sessions with summary information."""
        # This would require a new method in SessionRepository to get session summaries
        # For now, we'll implement a simple version
        active_sessions = await self.get_active_sessions()
        return [
            {
                "id": session.id,
                "model": session.model,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "token_count": session.token_count,
                "message_count": len(session.messages),
                "project_path": session.project_path
            }
            for session in active_sessions[:limit]
        ]
    
    def is_session_active(self) -> bool:
        """Check if there's an active session."""
        return self.current_session is not None and self.current_session.is_active
    
    async def end_session(self) -> None:
        """End the current session."""
        if self.current_session:
            self.current_session.is_active = False
            await self.save_session()
            self.current_session = None