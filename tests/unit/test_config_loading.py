"""
Unit tests for Qwen Code configuration management.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from qwen_code.config.settings import Config, ModelConfig, SessionConfig, AuthProviderConfig


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test configuration initialization."""
        config = Config()
        assert config.auth_provider == "qwen_oauth"
        assert isinstance(config.model_settings, ModelConfig)
        assert isinstance(config.session_config, SessionConfig)
        assert "qwen_oauth" in config.providers
        assert "openai_compatible" in config.providers
    
    def test_model_config_defaults(self):
        """Test model configuration defaults."""
        model_config = ModelConfig()
        assert model_config.default_model == "qwen3-coder-plus"
        assert model_config.temperature == 0.1
        assert model_config.max_tokens == 4096
        assert model_config.top_p == 0.95
    
    def test_session_config_defaults(self):
        """Test session configuration defaults."""
        session_config = SessionConfig()
        assert session_config.token_limit == 32000
        assert session_config.auto_save is True
        assert session_config.compression_threshold == 0.8
    
    def test_auth_provider_config(self):
        """Test authentication provider configuration."""
        # Test with environment variables
        with patch.dict(os.environ, {
            "QWEN_CLIENT_ID": "test-client-id",
            "OPENAI_API_KEY": "test-api-key"
        }):
            config = Config()
            assert config.providers["qwen_oauth"].client_id == "test-client-id"
            assert config.providers["openai_compatible"].api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_load_configuration(self):
        """Test loading configuration."""
        config = Config()
        # Just test that it doesn't crash for now
        await config.load()
        # In a real test, we would mock file operations and environment variables
        assert config is not None
    
    def test_save_configuration(self):
        """Test saving configuration."""
        config = Config()
        # Just test that it doesn't crash for now
        config.save()
        # In a real test, we would mock file operations and verify the content
        assert config is not None


class TestModelConfig:
    """Test model configuration data class."""
    
    def test_initialization(self):
        """Test model configuration initialization."""
        model_config = ModelConfig(
            default_model="test-model",
            temperature=0.5,
            max_tokens=2048,
            top_p=0.9
        )
        assert model_config.default_model == "test-model"
        assert model_config.temperature == 0.5
        assert model_config.max_tokens == 2048
        assert model_config.top_p == 0.9


class TestSessionConfig:
    """Test session configuration data class."""
    
    def test_initialization(self):
        """Test session configuration initialization."""
        session_config = SessionConfig(
            token_limit=16000,
            auto_save=False,
            compression_threshold=0.5
        )
        assert session_config.token_limit == 16000
        assert session_config.auto_save is False
        assert session_config.compression_threshold == 0.5


class TestAuthProviderConfig:
    """Test authentication provider configuration data class."""
    
    def test_initialization(self):
        """Test authentication provider configuration initialization."""
        auth_config = AuthProviderConfig(
            client_id="test-client-id",
            redirect_uri="http://test/callback",
            api_key="test-api-key",
            base_url="https://test.api.com"
        )
        assert auth_config.client_id == "test-client-id"
        assert auth_config.redirect_uri == "http://test/callback"
        assert auth_config.api_key == "test-api-key"
        assert auth_config.base_url == "https://test.api.com"