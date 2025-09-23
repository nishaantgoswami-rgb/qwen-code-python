"""
Unit tests for Qwen Code session management.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from qwen_code.session.manager import SessionManager, Session
from qwen_code.ai.client import Message
from qwen_code.config.settings import SessionConfig
from qwen_code.db.manager import DatabaseManager


class TestSession:
    """Test session data class."""
    
    def test_session_initialization(self):
        """Test session initialization."""
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
        # In a real test, we would initialize the database
        # await db_manager.initialize()
        
        # Mock the repositories
        session_repo_mock = AsyncMock()
        message_repo_mock = AsyncMock()
        
        # Create session manager with mocked repositories
        manager = SessionManager(config, db_manager)
        manager.session_repo = session_repo_mock
        manager.message_repo = message_repo_mock
        
        return manager, session_repo_mock, message_repo_mock
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test creating a session."""
        manager, session_repo_mock, _ = session_manager
        session = await manager.create_session("test-session", "/test/project")
        assert session.id == "test-session"
        assert session.project_path == "/test/project"
        assert session.is_active is True
        session_repo_mock.create_session.assert_called_once_with(session)
    
    @pytest.mark.asyncio
    async def test_load_session(self, session_manager):
        """Test loading a session."""
        manager, session_repo_mock, message_repo_mock = session_manager
        
        # Mock session and messages
        mock_session = Session(id="test-session")
        session_repo_mock.get_session.return_value = mock_session
        message_repo_mock.get_messages.return_value = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!")
        ]
        
        # Load the session
        session = await manager.load_session("test-session")
        assert session is not None
        assert session.id == "test-session"
        assert len(session.messages) == 2
        session_repo_mock.get_session.assert_called_once_with("test-session")
        message_repo_mock.get_messages.assert_called_once_with("test-session")
    
    @pytest.mark.asyncio
    async def test_save_session(self, session_manager):
        """Test saving a session."""
        manager, session_repo_mock, _ = session_manager
        session = Session(id="test-session")
        await manager.save_session(session)
        session_repo_mock.update_session.assert_called_once_with(session)
    
    @pytest.mark.asyncio
    async def test_add_message_to_session(self, session_manager):
        """Test adding a message to a session."""
        manager, session_repo_mock, message_repo_mock = session_manager
        message = Message(role="user", content="Hello, world!")
        
        # Mock session
        mock_session = Session(id="test-session")
        mock_session.token_count = 10
        session_repo_mock.get_session.return_value = mock_session
        
        # Add message to session
        await manager.add_message_to_session("test-session", message)
        message_repo_mock.add_message.assert_called_once_with("test-session", message)
        session_repo_mock.get_session.assert_called_once_with("test-session")
        session_repo_mock.update_session.assert_called_once()
    
    def test_get_session_stats(self):
        """Test getting session statistics."""
        # Create a session manager with a real database for this test
        config = SessionConfig()
        manager = SessionManager(config, MagicMock())
        
        # Create a session with messages
        session = Session(id="test-session")
        session.add_message(Message(role="user", content="Hello"))
        session.add_message(Message(role="assistant", content="Hi there!"))
        session.add_message(Message(role="user", content="How are you?"))
        manager.current_session = session
        
        # Get stats
        stats = manager.get_session_stats()
        assert stats["total_messages"] == 3
        assert stats["user_messages"] == 2
        assert stats["assistant_messages"] == 1
        assert stats["token_count"] > 0
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_manager):
        """Test getting active sessions."""
        manager, session_repo_mock, _ = session_manager
        
        # Mock active sessions
        mock_sessions = [Session(id="session-1"), Session(id="session-2")]
        session_repo_mock.get_active_sessions.return_value = mock_sessions
        
        # Get active sessions
        sessions = await manager.get_active_sessions()
        assert sessions == mock_sessions
        session_repo_mock.get_active_sessions.assert_called_once_with(None)
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        """Test deleting a session."""
        manager, session_repo_mock, _ = session_manager
        await manager.delete_session("test-session")
        session_repo_mock.delete_session.assert_called_once_with("test-session")