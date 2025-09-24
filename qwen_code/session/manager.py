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
        
        # Check if token count is already calculated, otherwise calculate it
        if message.token_count == 0:
            # Calculate accurate token count for the message using the new enhanced counter
            from qwen_code.ai.token_counter import AdvancedTokenCounter
            token_counter = AdvancedTokenCounter(self.model)
            message.token_count = token_counter.count_message_tokens(message)
        self.token_count += message.token_count
    
    def compress_history(self, target_tokens: int) -> None:
        """Compress conversation history to target token count."""
        try:
            from qwen_code.ai.token_counter import AdvancedTokenCounter
            
            if self.token_count <= target_tokens:
                return  # No compression needed
                
            # Initialize token counter
            token_counter = AdvancedTokenCounter(self.model)
            
            # Calculate actual token count for all messages to ensure accuracy
            total_tokens = 0
            message_tokens = []
            
            for message in self.messages:
                if message.token_count == 0:
                    # Calculate token count if not already set
                    msg_tokens = token_counter.count_message_tokens(message)
                    message.token_count = msg_tokens
                else:
                    msg_tokens = message.token_count
                message_tokens.append(msg_tokens)
                total_tokens += msg_tokens
            
            self.token_count = total_tokens
            
            if self.token_count <= target_tokens:
                return  # No compression needed after recalculation
            
            # Implement smart compression preserving context
            # Keep system messages and recent exchanges
            preserved_messages = []
            preserved_tokens = 0
            
            # Always try to keep the first message (system prompt) if it exists
            if self.messages and self.messages[0].role == "system":
                system_msg = self.messages[0]
                preserved_messages.append(system_msg)
                preserved_tokens += message_tokens[0]
            
            # Keep recent messages (last few exchanges) and some key exchanges
            recent_messages = []
            recent_tokens = 0
            
            # Calculate how many recent messages we can keep
            # Reserve some tokens for potentially important earlier messages
            reserved_tokens = min(int(target_tokens * 0.1), 2000)  # Reserve 10% or 2000 tokens, whichever is smaller
            available_tokens = target_tokens - preserved_tokens - reserved_tokens
            
            # Collect recent messages backwards
            for i in range(len(self.messages) - 1, -1, -1):
                if self.messages[i].role == "system" and i == 0:
                    # Skip system message as it's already handled above
                    continue
                    
                msg_tokens = message_tokens[i]
                
                if recent_tokens + msg_tokens <= available_tokens:
                    recent_messages.append((i, self.messages[i], msg_tokens))
                    recent_tokens += msg_tokens
                else:
                    break
            
            # Reverse to get them in chronological order
            recent_messages.reverse()
            
            # If we have remaining tokens, look for important earlier messages
            remaining_tokens = target_tokens - preserved_tokens - recent_tokens
            
            # Add important earlier messages if they fit (messages with code or long content that was important)
            important_messages = []
            for i in range(len(self.messages)):  # Check all messages for importance 
                # Skip if this is a system message (already handled) or recent message
                if (i == 0 and self.messages and self.messages[0].role == "system") or \
                   any(msg_idx == i for msg_idx, _, _ in recent_messages):
                    continue
                    
                msg_tokens = message_tokens[i]
                message = self.messages[i]
                
                # Check if message is likely important: contains code blocks, or is a long message
                is_important = (
                    '```' in message.content or  # Contains code blocks
                    len(message.content) > 200 or  # Longer message
                    message.role == "user" and len(message.content.split()) > 20  # Substantial user query
                )
                
                if is_important and remaining_tokens >= msg_tokens:
                    important_messages.append((i, message, msg_tokens))
                    remaining_tokens -= msg_tokens
            
            # Combine preserved, important, and recent messages in chronological order
            all_indices = set()
            final_messages = []
            
            # Add system message if preserved
            if preserved_messages:
                final_messages.append(preserved_messages[0])
                all_indices.add(0)
            
            # Add important messages in chronological order
            important_messages.sort(key=lambda x: x[0])  # Sort by index
            for idx, msg, tokens in important_messages:
                if idx not in all_indices:
                    final_messages.append(msg)
                    all_indices.add(idx)
            
            # Add recent messages in chronological order
            for idx, msg, tokens in recent_messages:
                if idx not in all_indices:
                    final_messages.append(msg)
                    all_indices.add(idx)
            
            # Update the session
            self.messages = final_messages
            
            # Recalculate token count
            self.token_count = sum(token_counter.count_message_tokens(msg) for msg in self.messages)
            
            # Ensure we're within the target
            if self.token_count > target_tokens:
                # If still over target, do simple truncation as fallback
                simple_target = target_tokens
                current_tokens = 0
                reduced_messages = []
                
                for msg in self.messages:
                    msg_tokens = token_counter.count_message_tokens(msg)
                    if current_tokens + msg_tokens <= simple_target:
                        reduced_messages.append(msg)
                        current_tokens += msg_tokens
                    else:
                        break
                
                self.messages = reduced_messages
                self.token_count = current_tokens
                
        except Exception as e:
            import logging
            logging.error(f"Error during session compression: {str(e)}")
            # Fallback to basic compression if the smart approach fails
            basic_target = target_tokens
            current_tokens = 0
            reduced_messages = []
            
            for message in self.messages:
                from qwen_code.ai.token_counter import AdvancedTokenCounter
                token_counter = AdvancedTokenCounter(self.model)
                msg_tokens = token_counter.count_message_tokens(message)
                if current_tokens + msg_tokens <= basic_target:
                    reduced_messages.append(message)
                    current_tokens += msg_tokens
                else:
                    break
            
            self.messages = reduced_messages
            self.token_count = current_tokens


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
        
        # Check if we need to compress the session
        if self.current_session.token_count > self.config.token_limit:
            await self.compress_current_session()
        
        # Save message to database
        await self.message_repo.add_message(self.current_session.id, message)
        
        # Update session in database
        await self.session_repo.update_session(self.current_session)
    
    async def check_session_compression(self) -> bool:
        """Check if current session needs compression and compress if needed.
        
        Returns True if compression was performed, False otherwise.
        """
        if not self.current_session:
            return False
            
        # Calculate the threshold for compression based on compression_threshold
        compression_threshold_tokens = int(self.config.token_limit * self.config.compression_threshold)
        
        if self.current_session.token_count > compression_threshold_tokens:
            await self.compress_current_session()
            return True
            
        return False
    
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