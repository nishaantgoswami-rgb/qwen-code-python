"""
Unit tests for Qwen Code configuration module.
"""

import pytest
from qwen_code.config.settings import Config, ModelConfig, SessionConfig


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test configuration initialization."""
        config = Config()
        assert config.auth_provider == "qwen_oauth"
        assert isinstance(config.model_settings, ModelConfig)
        assert isinstance(config.session_config, SessionConfig)
    
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