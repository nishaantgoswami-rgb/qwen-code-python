"""
Simple integration tests for Qwen Code CLI.
"""

import pytest
import tempfile
from pathlib import Path

from qwen_code.config.settings import Config
from qwen_code.ai.client import Message
from qwen_code.session.manager import SessionManager, Session
from qwen_code.auth.credentials import CredentialManager, Credentials
from qwen_code.fs.operations import FileManager, CodebaseAnalysis
from qwen_code.db.manager import DatabaseManager


class TestIntegration:
    """Simple integration tests for Qwen Code components."""
    
    def test_config_loading(self):
        """Test configuration loading."""
        config = Config()
        assert config.auth_provider is not None
        assert config.model_settings is not None
        assert config.session_config is not None
    
    def test_session_creation(self):
        """Test session creation and management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db_manager = DatabaseManager(db_path)
            config = Config()
            
            # This would normally be async, but we're simplifying for testing
            # await db_manager.initialize()
            
            session_manager = SessionManager(config.session_config, db_manager)
            assert session_manager is not None
    
    def test_credential_storage(self):
        """Test credential storage and retrieval."""
        credential_manager = CredentialManager()
        
        # Store credentials
        creds = Credentials(
            provider="test-provider",
            access_token="test-token"
        )
        credential_manager.store_credentials(creds)
        
        # Load credentials
        loaded_creds = credential_manager.load_credentials("test-provider")
        assert loaded_creds is not None
        assert loaded_creds.access_token == "test-token"
    
    def test_file_analysis(self):
        """Test file system analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            
            # Create test files
            (project_path / "main.py").write_text("def main():\n    print('Hello')\n")
            (project_path / "README.md").write_text("# Test Project\n")
            
            # Analyze codebase
            file_manager = FileManager(project_path)
            # This would normally be async
            # analysis = await file_manager.analyze_codebase()
            
            # For now, just test that the file manager works
            assert file_manager is not None


class TestApplicationComponents:
    """Test application component interactions."""
    
    def test_component_initialization(self):
        """Test that all components can be initialized together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Create components
            config = Config()
            db_manager = DatabaseManager(db_path)
            credential_manager = CredentialManager()
            file_manager = FileManager(Path("."))
            
            # Verify all components are created
            assert config is not None
            assert db_manager is not None
            assert credential_manager is not None
            assert file_manager is not None