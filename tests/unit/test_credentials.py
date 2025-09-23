"""
Unit tests for Qwen Code credential management.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from qwen_code.auth.credentials import CredentialManager, Credentials


class TestCredentials:
    """Test credentials data class."""
    
    def test_initialization(self):
        """Test credentials initialization."""
        creds = Credentials(
            provider="test-provider",
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_at="2023-12-31T23:59:59Z",
            metadata={"test": "value"}
        )
        assert creds.provider == "test-provider"
        assert creds.access_token == "test-access-token"
        assert creds.refresh_token == "test-refresh-token"
        assert creds.expires_at == "2023-12-31T23:59:59Z"
        assert creds.metadata == {"test": "value"}
    
    def test_initialization_with_defaults(self):
        """Test credentials initialization with default values."""
        creds = Credentials(
            provider="test-provider",
            access_token="test-access-token"
        )
        assert creds.provider == "test-provider"
        assert creds.access_token == "test-access-token"
        assert creds.refresh_token is None
        assert creds.expires_at is None
        assert creds.metadata == {}


class TestCredentialManager:
    """Test credential manager functionality."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            storage_path = Path(f.name)
        yield storage_path
        storage_path.unlink()
    
    @pytest.fixture
    def credential_manager(self, temp_storage):
        """Create a credential manager with temporary storage."""
        return CredentialManager(storage_path=temp_storage)
    
    def test_init(self, temp_storage):
        """Test credential manager initialization."""
        cm = CredentialManager(storage_path=temp_storage)
        assert cm.storage_path == temp_storage
        assert temp_storage.parent.exists()
    
    def test_store_and_load_credentials(self, credential_manager):
        """Test storing and loading credentials."""
        # Create test credentials
        creds = Credentials(
            provider="test-provider",
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_at="2023-12-31T23:59:59Z",
            metadata={"test": "value"}
        )
        
        # Store credentials
        credential_manager.store_credentials(creds)
        
        # Load credentials
        loaded_creds = credential_manager.load_credentials("test-provider")
        assert loaded_creds is not None
        assert loaded_creds.provider == "test-provider"
        assert loaded_creds.access_token == "test-access-token"
        assert loaded_creds.refresh_token == "test-refresh-token"
        assert loaded_creds.expires_at == "2023-12-31T23:59:59Z"
        assert loaded_creds.metadata == {"test": "value"}
    
    def test_load_nonexistent_credentials(self, credential_manager):
        """Test loading credentials that don't exist."""
        creds = credential_manager.load_credentials("nonexistent-provider")
        assert creds is None
    
    def test_clear_credentials(self, credential_manager):
        """Test clearing stored credentials."""
        # Store credentials
        creds = Credentials(
            provider="test-provider",
            access_token="test-access-token"
        )
        credential_manager.store_credentials(creds)
        
        # Verify credentials exist
        loaded_creds = credential_manager.load_credentials("test-provider")
        assert loaded_creds is not None
        
        # Clear credentials
        credential_manager.clear_credentials("test-provider")
        
        # Verify credentials are gone
        loaded_creds = credential_manager.load_credentials("test-provider")
        assert loaded_creds is None
    
    def test_has_valid_credentials(self, credential_manager):
        """Test checking for valid credentials."""
        # Initially no credentials
        assert not credential_manager.has_valid_credentials("test-provider")
        
        # Store credentials
        creds = Credentials(
            provider="test-provider",
            access_token="test-access-token"
        )
        credential_manager.store_credentials(creds)
        
        # Now should have valid credentials
        assert credential_manager.has_valid_credentials("test-provider")
    
    def test_list_providers(self, credential_manager):
        """Test listing providers with stored credentials."""
        # Initially no providers
        assert credential_manager.list_providers() == []
        
        # Store credentials for two providers
        creds1 = Credentials(
            provider="provider-1",
            access_token="test-access-token"
        )
        creds2 = Credentials(
            provider="provider-2",
            access_token="test-access-token"
        )
        credential_manager.store_credentials(creds1)
        credential_manager.store_credentials(creds2)
        
        # Should list both providers
        providers = credential_manager.list_providers()
        assert len(providers) == 2
        assert "provider-1" in providers
        assert "provider-2" in providers