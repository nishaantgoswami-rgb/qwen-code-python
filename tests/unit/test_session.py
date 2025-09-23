"""
Unit tests for Qwen Code session management.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from qwen_code.ai.client import Message
from qwen_code.config.settings import SessionConfig
from qwen_code.db.manager import DatabaseManager


class TestSession:
    """Test session data class."""
    
    def test_session_initialization(self):
        """Test session initialization."""
        # Import Session locally to avoid circular imports in tests
        from qwen_code.session.manager import Session
        session = Session(id="test-session")
        assert session.id == "test-session"
        assert session.messages == []
        assert session.token_count == 0
        assert session.model == "qwen3-coder-plus"
        assert session.project_path is None
        assert session.is_active is True
        assert session.metadata == {}
    
    def test_add_message(self):
        """Test adding messages to session."""
        # Import Session locally to avoid circular imports in tests
        from qwen_code.session.manager import Session
        session = Session(id="test-session")
        message = Message(role="user", content="Hello, world!")
        session.add_message(message)
        
        assert len(session.messages) == 1
        assert session.messages[0] == message
        assert session.token_count > 0  # Should have counted tokens


class TestSessionManager:
    """Test session manager."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        db_path.unlink()
    
    @pytest.fixture
    def session_manager(self, temp_db):
        """Create a session manager with temporary database."""
        config = SessionConfig()
        db_manager = DatabaseManager(temp_db)
        # Run initialize in an async context
        async def init_db():
            await db_manager.initialize()
            return db_manager
        db_manager = asyncio.run(init_db())
        
        # Import SessionManager locally to avoid circular imports
        from qwen_code.session.manager import SessionManager
        manager = SessionManager(config, db_manager)
        yield manager
        db_manager.close()
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test creating a session."""
        session = await session_manager.create_session("test-session", "/test/project")
        assert session.id == "test-session"
        assert session.project_path == "/test/project"
        assert session.is_active is True
    
    @pytest.mark.asyncio
    async def test_save_and_load_session(self, session_manager):
        """Test saving and loading a session."""
        # Create and save a session
        session = await session_manager.create_session("test-session", "/test/project")
        message = Message(role="user", content="Hello, world!")
        session.add_message(message)
        await session_manager.save_session(session)
        
        # Load the session
        loaded_session = await session_manager.load_session("test-session")
        assert loaded_session is not None
        assert loaded_session.id == "test-session"
        assert loaded_session.project_path == "/test/project"
    
    @pytest.mark.asyncio
    async def test_add_message_to_session(self, session_manager):
        """Test adding a message to a session."""
        # Create a session
        session = await session_manager.create_session("test-session")
        initial_token_count = session.token_count
        
        # Add a message
        message = Message(role="user", content="Hello, world!")
        await session_manager.add_message_to_session("test-session", message)
        
        # Verify the message was added
        loaded_session = await session_manager.load_session("test-session")
        assert loaded_session is not None
        assert len(loaded_session.messages) == 1
        assert loaded_session.messages[0].role == "user"
        assert loaded_session.messages[0].content == "Hello, world!"
        assert loaded_session.token_count > initial_token_count
    
    @pytest.mark.asyncio
    async def test_get_session_stats(self, session_manager):
        """Test getting session statistics."""
        # Import Session locally to avoid circular imports in tests
        from qwen_code.session.manager import Session
        # Create a session with messages
        session = await session_manager.create_session("test-session")
        session.add_message(Message(role="user", content="Hello"))
        session.add_message(Message(role="assistant", content="Hi there!"))
        session.add_message(Message(role="user", content="How are you?"))
        
        # Get stats
        stats = session_manager.get_session_stats()
        assert stats["total_messages"] == 3
        assert stats["user_messages"] == 2
        assert stats["assistant_messages"] == 1
        assert stats["token_count"] > 0
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_manager):
        """Test getting active sessions."""
        # Create two sessions
        await session_manager.create_session("session-1", "/project1")
        await session_manager.create_session("session-2", "/project2")
        
        # Get all active sessions
        sessions = await session_manager.get_active_sessions()
        assert len(sessions) == 2
        
        # Get sessions for a specific project
        sessions = await session_manager.get_active_sessions("/project1")
        assert len(sessions) == 1
        assert sessions[0].id == "session-1"
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        """Test deleting a session."""
        # Create a session
        await session_manager.create_session("test-session")
        
        # Verify it exists
        session = await session_manager.load_session("test-session")
        assert session is not None
        
        # Delete the session
        await session_manager.delete_session("test-session")
        
        # Verify it's gone
        session = await session_manager.load_session("test-session")
        assert session is None