"""
Integration tests for Qwen Code CLI.
"""

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


class TestIntegration:
    """Integration tests for Qwen Code components."""
    
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
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        db_path.unlink()
    
    @pytest.fixture
    async def app_components(self, temp_db):
        """Create application components for testing."""
        # Create config
        config = Config()
        
        # Create database manager
        db_manager = DatabaseManager(temp_db)
        await db_manager.initialize()
        
        # Create session manager
        session_manager = SessionManager(config.session_config, db_manager)
        
        # Create credential manager
        credential_manager = CredentialManager()
        
        # Create file manager
        file_manager = FileManager(Path("."))
        
        yield {
            "config": config,
            "db_manager": db_manager,
            "session_manager": session_manager,
            "credential_manager": credential_manager,
            "file_manager": file_manager
        }
        
        # Cleanup
        db_manager.close()
    
    @pytest.mark.asyncio
    async def test_full_application_flow(self, temp_project, app_components):
        """Test a full application flow from initialization to execution."""
        # Initialize components
        config = app_components["config"]
        session_manager = app_components["session_manager"]
        credential_manager = app_components["credential_manager"]
        file_manager = app_components["file_manager"]
        
        # Create application
        app = QwenCodeApplication()
        
        # Test configuration loading
        await config.load()
        assert config.auth_provider is not None
        
        # Test session creation
        session = await session_manager.create_session("test-session", str(temp_project))
        assert session.id == "test-session"
        assert session.project_path == str(temp_project)
        
        # Test adding messages to session
        user_message = Message(role="user", content="Analyze this code")
        session.add_message(user_message)
        await session_manager.save_session(session)
        
        # Test file system operations
        analysis = await file_manager.analyze_codebase()
        assert isinstance(analysis, CodebaseAnalysis)
        assert analysis.total_files >= 2  # main.py and utils.py
        assert "Python" in analysis.languages
        
        # Test credential management
        test_creds = Credentials(
            provider="test-provider",
            access_token="test-access-token"
        )
        credential_manager.store_credentials(test_creds)
        assert credential_manager.has_valid_credentials("test-provider")
        
        loaded_creds = credential_manager.load_credentials("test-provider")
        assert loaded_creds is not None
        assert loaded_creds.access_token == "test-access-token"
        
        # Test session statistics
        stats = session_manager.get_session_stats()
        assert stats["total_messages"] == 1
        assert stats["user_messages"] == 1
    
    @pytest.mark.asyncio
    async def test_ai_interaction_flow(self, app_components):
        """Test AI interaction flow with mocked AI client."""
        # Initialize components
        session_manager = app_components["session_manager"]
        
        # Create session
        session = await session_manager.create_session("ai-test-session")
        
        # Mock AI client
        with patch("qwen_code.ai.client.QwenClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock AI response
            mock_response = AIResponse(
                content="This is a test AI response",
                usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                model="qwen3-coder-plus"
            )
            mock_client.chat.return_value = mock_response
            
            # Create real QwenClient instance for testing
            ai_client = QwenClient("test-key")
            
            # Test AI chat
            messages = [Message(role="user", content="Hello, AI!")]
            response = await ai_client.chat(messages)
            
            # Verify response (will be mock response)
            assert response is not None
            
            # Add messages to session
            user_msg = Message(role="user", content="Hello, AI!")
            session.add_message(user_msg)
            
            ai_msg = Message(role="assistant", content=response.content)
            session.add_message(ai_msg)
            
            await session_manager.save_session(session)
            
            # Verify session messages
            assert len(session.messages) == 2
            assert session.messages[0].role == "user"
            assert session.messages[1].role == "assistant"
    
    @pytest.mark.asyncio
    async def test_file_system_integration(self, temp_project, app_components):
        """Test file system integration with session management."""
        # Initialize components
        file_manager = app_components["file_manager"]
        session_manager = app_components["session_manager"]
        
        # Create session with project path
        session = await session_manager.create_session("fs-test-session", str(temp_project))
        
        # Analyze codebase
        analysis = await file_manager.analyze_codebase()
        assert analysis.total_files >= 2
        
        # Add analysis results to session messages
        analysis_msg = Message(
            role="system",
            content=f"Codebase analysis: {analysis.total_files} files, {analysis.total_lines} lines"
        )
        session.add_message(analysis_msg)
        
        await session_manager.save_session(session)
        
        # Verify session has analysis message
        assert len(session.messages) == 1
        assert "Codebase analysis" in session.messages[0].content
    
    @pytest.mark.asyncio
    async def test_credential_encryption(self, app_components):
        """Test credential encryption and storage."""
        credential_manager = app_components["credential_manager"]
        
        # Store credentials
        original_creds = Credentials(
            provider="encryption-test",
            access_token="sensitive-access-token",
            refresh_token="sensitive-refresh-token",
            metadata={"test": "value"}
        )
        credential_manager.store_credentials(original_creds)
        
        # Load credentials
        loaded_creds = credential_manager.load_credentials("encryption-test")
        assert loaded_creds is not None
        assert loaded_creds.provider == "encryption-test"
        assert loaded_creds.access_token == "sensitive-access-token"
        assert loaded_creds.refresh_token == "sensitive-refresh-token"
        assert loaded_creds.metadata == {"test": "value"}
        
        # Verify credentials are listed
        providers = credential_manager.list_providers()
        assert "encryption-test" in providers
        
        # Clear credentials
        credential_manager.clear_credentials("encryption-test")
        assert not credential_manager.has_valid_credentials("encryption-test")
        
        # Verify provider is no longer listed
        providers = credential_manager.list_providers()
        assert "encryption-test" not in providers


class TestApplicationComponents:
    """Test interactions between application components."""
    
    @pytest.mark.asyncio
    async def test_component_initialization(self):
        """Test that all components can be initialized together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Create components
            config = Config()
            db_manager = DatabaseManager(db_path)
            await db_manager.initialize()
            session_manager = SessionManager(config.session_config, db_manager)
            credential_manager = CredentialManager()
            file_manager = FileManager(Path("."))
            
            # Verify all components are created
            assert config is not None
            assert db_manager is not None
            assert session_manager is not None
            assert credential_manager is not None
            assert file_manager is not None
            
            # Cleanup
            db_manager.close()
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, temp_db):
        """Test complete session lifecycle."""
        # Create components
        config = Config()
        db_manager = DatabaseManager(temp_db)
        await db_manager.initialize()
        session_manager = SessionManager(config.session_config, db_manager)
        
        # Create session
        session = await session_manager.create_session("lifecycle-test")
        assert session.id == "lifecycle-test"
        assert session.is_active is True
        
        # Add messages
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="assistant", content="Hi there!")
        session.add_message(msg1)
        session.add_message(msg2)
        
        # Save session
        await session_manager.save_session(session)
        
        # Load session
        loaded_session = await session_manager.load_session("lifecycle-test")
        assert loaded_session is not None
        assert len(loaded_session.messages) == 2
        assert loaded_session.messages[0].content == "Hello"
        assert loaded_session.messages[1].content == "Hi there!"
        
        # Get session stats
        stats = session_manager.get_session_stats()
        assert stats["total_messages"] == 2
        assert stats["user_messages"] == 1
        assert stats["assistant_messages"] == 1
        
        # Delete session
        await session_manager.delete_session("lifecycle-test")
        
        # Verify session is deleted
        deleted_session = await session_manager.load_session("lifecycle-test")
        assert deleted_session is None
        
        # Cleanup
        db_manager.close()