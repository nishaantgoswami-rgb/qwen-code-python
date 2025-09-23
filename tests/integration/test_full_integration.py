"""Comprehensive integration tests for Qwen Code CLI."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
import asyncio

from qwen_code.app import QwenCodeApplication
from qwen_code.config.settings import Config
from qwen_code.ai.client import QwenClient, Message, AIResponse, TokenUsage
from qwen_code.session.manager import SessionManager, Session
from qwen_code.auth.credentials import CredentialManager, Credentials
from qwen_code.fs.operations import FileManager, CodebaseAnalysis
from qwen_code.db.manager import DatabaseManager


class TestFullApplicationIntegration:
    """Comprehensive integration tests for the full Qwen Code application."""
    
    @pytest.fixture
    async def temp_project(self):
        """Create a temporary project for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create some test files
            (project_path / "main.py").write_text("def main():\n    print('Hello, World!')\n")
            (project_path / "utils.py").write_text("def helper():\n    return 'utils'\n")
            (project_path / "README.md").write_text("# Test Project\n")
            
            yield project_path
    
    @pytest.fixture
    async def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield db_path
    
    @pytest.mark.asyncio
    async def test_application_initialization(self, temp_db):
        """Test full application initialization."""
        # Create application
        app = QwenCodeApplication()
        
        # Initialize application
        await app.initialize()
        
        # Verify initialization
        assert app.is_initialized() is True
        assert app.config is not None
        assert app.db_manager is not None
        assert app.session_manager is not None
        assert app.credential_manager is not None
        
        # Cleanup
        await app.cleanup()
    
    @pytest.mark.asyncio
    async def test_complete_session_lifecycle(self, temp_project, temp_db):
        """Test complete session lifecycle from creation to deletion."""
        # Initialize application
        app = QwenCodeApplication()
        await app.initialize()
        
        # Create session
        session = await app.session_manager.create_session(
            project_path=str(temp_project),
            model="qwen3-coder-plus"
        )
        
        # Verify session creation
        assert session is not None
        assert session.project_path == str(temp_project)
        assert session.model == "qwen3-coder-plus"
        assert session.is_active is True
        
        # Add messages to session
        user_msg = Message(role="user", content="Analyze my code")
        await app.session_manager.add_message_to_session(user_msg)
        
        # Verify message was added
        loaded_session = await app.session_manager.load_session(session.id)
        assert len(loaded_session.messages) == 1
        assert loaded_session.messages[0].content == "Analyze my code"
        
        # Get session stats
        stats = app.session_manager.get_session_stats()
        assert stats["total_messages"] == 1
        assert stats["user_messages"] == 1
        
        # Cleanup
        await app.cleanup()
    
    @pytest.mark.asyncio
    async def test_file_system_integration(self, temp_project, temp_db):
        """Test file system operations integration."""
        # Initialize application
        app = QwenCodeApplication()
        await app.initialize()
        
        # Create file manager
        file_manager = FileManager(temp_project)
        
        # Analyze codebase
        analysis = await file_manager.analyze_codebase()
        
        # Verify analysis results
        assert isinstance(analysis, CodebaseAnalysis)
        assert analysis.total_files >= 2  # main.py and utils.py
        assert "Python" in analysis.languages
        assert analysis.total_lines > 0
        
        # Test file search
        search_results = await file_manager.search_files("Hello")
        assert len(search_results) >= 1
        assert Path("main.py") in search_results
        
        # Cleanup
        await app.cleanup()
    
    @pytest.mark.asyncio
    async def test_credential_management(self, temp_db):
        """Test credential management integration."""
        # Initialize application
        app = QwenCodeApplication()
        await app.initialize()
        
        # Store credentials
        test_creds = Credentials(
            provider="integration-test",
            access_token="test-access-token",
            refresh_token="test-refresh-token"
        )
        app.credential_manager.store_credentials(test_creds)
        
        # Verify credentials are stored
        assert app.credential_manager.has_valid_credentials("integration-test") is True
        
        # Load credentials
        loaded_creds = app.credential_manager.load_credentials("integration-test")
        assert loaded_creds is not None
        assert loaded_creds.access_token == "test-access-token"
        assert loaded_creds.refresh_token == "test-refresh-token"
        
        # List providers
        providers = app.credential_manager.list_providers()
        assert "integration-test" in providers
        
        # Cleanup
        await app.cleanup()
    
    @pytest.mark.asyncio
    async def test_configuration_persistence(self, temp_db):
        """Test configuration loading and saving."""
        # Initialize application
        app = QwenCodeApplication()
        await app.initialize()
        
        # Modify configuration
        app.config.auth_provider = "openai_compatible"
        app.config.model_settings.default_model = "gpt-4"
        app.config.session_config.token_limit = 16000
        
        # Save configuration
        app.config.save()
        
        # Create new config instance and load
        new_config = Config()
        await new_config.load()
        
        # Verify configuration was saved and loaded
        assert new_config.auth_provider == "openai_compatible"
        assert new_config.model_settings.default_model == "gpt-4"
        assert new_config.session_config.token_limit == 16000
        
        # Cleanup
        await app.cleanup()


class TestAIIntegration:
    """AI client integration tests."""
    
    @pytest.mark.asyncio
    async def test_ai_client_initialization(self):
        """Test AI client initialization."""
        # Test Qwen client
        qwen_client = QwenClient("test-api-key", "qwen3-coder-plus")
        assert qwen_client.api_key == "test-api-key"
        assert qwen_client.model == "qwen3-coder-plus"
        assert qwen_client.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # Test OpenAI compatible client
        openai_client = QwenClient("test-api-key", "gpt-4")
        assert openai_client.api_key == "test-api-key"
        assert openai_client.model == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_message_structure(self):
        """Test message structure and handling."""
        # Test user message
        user_msg = Message(role="user", content="Hello, AI!")
        assert user_msg.role == "user"
        assert user_msg.content == "Hello, AI!"
        
        # Test assistant message
        assistant_msg = Message(role="assistant", content="Hello! How can I help?")
        assert assistant_msg.role == "assistant"
        assert assistant_msg.content == "Hello! How can I help?"
        
        # Test system message
        system_msg = Message(role="system", content="You are a helpful assistant.")
        assert system_msg.role == "system"
        assert system_msg.content == "You are a helpful assistant."


class TestDatabaseIntegration:
    """Database integration tests."""
    
    @pytest.mark.asyncio
    async def test_database_operations(self, temp_db):
        """Test database operations."""
        # Initialize database
        db_manager = DatabaseManager(temp_db)
        await db_manager.initialize()
        
        # Verify database file was created
        assert temp_db.exists()
        
        # Create session repository
        from qwen_code.db.repositories import SessionRepository
        session_repo = SessionRepository(db_manager)
        
        # Verify repository was created
        assert session_repo is not None
        
        # Cleanup
        db_manager.close()


if __name__ == "__main__":
    pytest.main([__file__])