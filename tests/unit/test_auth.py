"""
Unit tests for Qwen Code authentication.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from qwen_code.auth.providers import (
    QwenOAuthProvider, OpenAICompatibleProvider, 
    Credentials, AuthResult, PKCEHelper
)
from qwen_code.auth.credentials import CredentialManager


class TestPKCEHelper:
    """Test PKCE helper functions."""
    
    def test_generate_code_verifier(self):
        """Test code verifier generation."""
        verifier = PKCEHelper.generate_code_verifier()
        assert isinstance(verifier, str)
        assert len(verifier) > 0
    
    def test_generate_code_challenge(self):
        """Test code challenge generation."""
        verifier = "test_verifier"
        challenge = PKCEHelper.generate_code_challenge(verifier)
        assert isinstance(challenge, str)
        assert len(challenge) > 0
        assert verifier != challenge


class TestQwenOAuthProvider:
    """Test Qwen OAuth provider."""
    
    def test_init(self):
        """Test provider initialization."""
        provider = QwenOAuthProvider("test_client_id", "http://test/callback")
        assert provider.client_id == "test_client_id"
        assert provider.redirect_uri == "http://test/callback"
        assert provider.client_secret is None
        
        # Test with client secret
        provider = QwenOAuthProvider("test_client_id", "http://test/callback", "test_secret")
        assert provider.client_secret == "test_secret"
    
    @pytest.mark.asyncio
    async def test_authenticate_placeholder(self):
        """Test authenticate method placeholder."""
        provider = QwenOAuthProvider("test_client_id", "http://test/callback")
        result = await provider.authenticate()
        assert isinstance(result, AuthResult)
        assert result.success is False
        # The OAuth flow is now implemented, so we expect a timeout error
        assert "Authentication timeout or cancelled" in result.error_message
    
    def test_is_valid_without_credentials(self):
        """Test is_valid without credentials."""
        provider = QwenOAuthProvider("test_client_id", "http://test/callback")
        assert provider.is_valid() is False


class TestOpenAICompatibleProvider:
    """Test OpenAI-compatible provider."""
    
    def test_init(self):
        """Test provider initialization."""
        provider = OpenAICompatibleProvider("test_key", "http://test/api")
        assert provider.api_key == "test_key"
        assert provider.base_url == "http://test/api"
    
    @pytest.mark.asyncio
    async def test_authenticate(self):
        """Test authenticate method."""
        provider = OpenAICompatibleProvider("test_key", "http://test/api")
        result = await provider.authenticate()
        assert isinstance(result, AuthResult)
        assert result.success is True
        assert result.access_token == "test_key"
    
    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """Test refresh token method."""
        provider = OpenAICompatibleProvider("test_key", "http://test/api")
        # First authenticate to set credentials
        await provider.authenticate()
        result = await provider.refresh_token()
        assert isinstance(result, AuthResult)
        assert result.success is True
        assert result.access_token == "test_key"
    
    def test_is_valid(self):
        """Test is_valid method."""
        provider = OpenAICompatibleProvider("test_key", "http://test/api")
        # Initially not valid
        assert provider.is_valid() is False
        # After authentication, should be valid
        provider._credentials = Credentials("openai_compatible", "test_key")
        assert provider.is_valid() is True


class TestCredentialManager:
    """Test credential manager."""
    
    @pytest.fixture
    def temp_credential_manager(self):
        """Create a credential manager with temporary storage."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        manager = CredentialManager(db_path)
        yield manager
        db_path.unlink()
    
    def test_init(self, temp_credential_manager):
        """Test manager initialization."""
        manager = temp_credential_manager
        assert manager.storage_path is not None
        assert manager.storage_path.exists()
    
    def test_store_and_load_credentials(self, temp_credential_manager):
        """Test storing and loading credentials."""
        manager = temp_credential_manager
        credentials = Credentials("test_provider", "test_token")
        manager.store_credentials(credentials)
        loaded = manager.load_credentials("test_provider")
        assert loaded is not None
        assert loaded.provider == "test_provider"
        assert loaded.access_token == "test_token"
    
    def test_clear_credentials(self, temp_credential_manager):
        """Test clearing credentials."""
        manager = temp_credential_manager
        credentials = Credentials("test_provider", "test_token")
        manager.store_credentials(credentials)
        assert manager.load_credentials("test_provider") is not None
        manager.clear_credentials("test_provider")
        assert manager.load_credentials("test_provider") is None
    
    def test_has_valid_credentials(self, temp_credential_manager):
        """Test has_valid_credentials method."""
        manager = temp_credential_manager
        # Initially no valid credentials
        assert manager.has_valid_credentials("test_provider") is False
        # After storing credentials, should have valid credentials
        credentials = Credentials("test_provider", "test_token")
        manager.store_credentials(credentials)
        assert manager.has_valid_credentials("test_provider") is True
    
    def test_list_providers(self, temp_credential_manager):
        """Test list_providers method."""
        manager = temp_credential_manager
        # Initially no providers
        assert manager.list_providers() == []
        # After storing credentials, should list providers
        credentials = Credentials("test_provider", "test_token")
        manager.store_credentials(credentials)
        assert manager.list_providers() == ["test_provider"]