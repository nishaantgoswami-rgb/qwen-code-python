"""
Configuration settings for Qwen Code.
"""

import os
import yaml
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ModelConfig:
    """AI model configuration."""
    default_model: str = "qwen3-coder-plus"
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 0.95


@dataclass
class SessionConfig:
    """Session configuration parameters."""
    token_limit: int = 32000
    auto_save: bool = True
    compression_threshold: float = 0.8


@dataclass
class AuthProviderConfig:
    """Authentication provider configuration."""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class Config:
    """Application configuration management."""
    
    def __init__(self):
        self.auth_provider = "qwen_oauth"
        self.model_settings = ModelConfig()
        self.session_config = SessionConfig()
        self.ui_theme: str = "default"  # New UI theme setting
        
        # Auth provider configurations
        self.providers = {
            "qwen_oauth": AuthProviderConfig(
                client_id=os.getenv("QWEN_CLIENT_ID", "f0304373b74a44d2b584a3fb70ca9e56"),
                client_secret=os.getenv("QWEN_CLIENT_SECRET"),
                redirect_uri=os.getenv("QWEN_REDIRECT_URI", "http://localhost:8080/callback")
            ),
            "openai_compatible": AuthProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )
        }
    
    async def load(self) -> None:
        """Load configuration from multiple sources."""
        # Try to load from global config file
        global_config_path = Path.home() / ".qwen" / "config.yaml"
        if global_config_path.exists():
            self._load_from_file(global_config_path)
        
        # Try to load from project config file
        project_config_path = Path.cwd() / ".qwen" / "project.yaml"
        if project_config_path.exists():
            self._load_from_file(project_config_path)
        
        # Override with environment variables
        self._load_from_env()
    
    def _load_from_file(self, config_path: Path) -> None:
        """Load configuration from a YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not isinstance(config_data, dict):
                return
            
            # Load auth provider
            if "auth" in config_data:
                auth_data = config_data["auth"]
                if "default_provider" in auth_data:
                    self.auth_provider = auth_data["default_provider"]
                
                # Load provider configurations
                if "providers" in auth_data:
                    for provider_name, provider_data in auth_data["providers"].items():
                        if provider_name in self.providers:
                            # Update existing provider config
                            provider_config = self.providers[provider_name]
                            if "client_id" in provider_data:
                                provider_config.client_id = provider_data["client_id"]
                            if "client_secret" in provider_data:
                                provider_config.client_secret = provider_data["client_secret"]
                            if "redirect_uri" in provider_data:
                                provider_config.redirect_uri = provider_data["redirect_uri"]
                            if "api_key" in provider_data:
                                provider_config.api_key = provider_data["api_key"]
                            if "base_url" in provider_data:
                                provider_config.base_url = provider_data["base_url"]
            
            # Load model settings
            if "models" in config_data:
                models_data = config_data["models"]
                if "default" in models_data:
                    self.model_settings.default_model = models_data["default"]
                if self.model_settings.default_model in models_data:
                    model_config = models_data[self.model_settings.default_model]
                    if "temperature" in model_config:
                        self.model_settings.temperature = model_config["temperature"]
                    if "max_tokens" in model_config:
                        self.model_settings.max_tokens = model_config["max_tokens"]
                    if "top_p" in model_config:
                        self.model_settings.top_p = model_config["top_p"]
            
            # Load session config
            if "session" in config_data:
                session_data = config_data["session"]
                if "token_limit" in session_data:
                    self.session_config.token_limit = session_data["token_limit"]
                if "auto_save" in session_data:
                    self.session_config.auto_save = session_data["auto_save"]
                if "compression_threshold" in session_data:
                    self.session_config.compression_threshold = session_data["compression_threshold"]
            
            # Load UI config
            if "ui" in config_data:
                ui_data = config_data["ui"]
                if "theme" in ui_data:
                    self.ui_theme = ui_data["theme"]
                    
        except (yaml.YAMLError, IOError, KeyError) as e:
            # Log error but don't crash
            print(f"Warning: Could not load config from {config_path}: {e}")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Auth provider
        if "QWEN_AUTH_PROVIDER" in os.environ:
            self.auth_provider = os.environ["QWEN_AUTH_PROVIDER"]
        
        # Provider configurations
        if "QWEN_CLIENT_ID" in os.environ:
            self.providers["qwen_oauth"].client_id = os.environ["QWEN_CLIENT_ID"]
        if "QWEN_CLIENT_SECRET" in os.environ:
            self.providers["qwen_oauth"].client_secret = os.environ["QWEN_CLIENT_SECRET"]
        if "QWEN_REDIRECT_URI" in os.environ:
            self.providers["qwen_oauth"].redirect_uri = os.environ["QWEN_REDIRECT_URI"]
        if "OPENAI_API_KEY" in os.environ:
            self.providers["openai_compatible"].api_key = os.environ["OPENAI_API_KEY"]
        if "OPENAI_BASE_URL" in os.environ:
            self.providers["openai_compatible"].base_url = os.environ["OPENAI_BASE_URL"]
        
        # Model settings
        if "QWEN_DEFAULT_MODEL" in os.environ:
            self.model_settings.default_model = os.environ["QWEN_DEFAULT_MODEL"]
        if "QWEN_TEMPERATURE" in os.environ:
            self.model_settings.temperature = float(os.environ["QWEN_TEMPERATURE"])
        if "QWEN_MAX_TOKENS" in os.environ:
            self.model_settings.max_tokens = int(os.environ["QWEN_MAX_TOKENS"])
        if "QWEN_TOP_P" in os.environ:
            self.model_settings.top_p = float(os.environ["QWEN_TOP_P"])
        
        # Session config
        if "QWEN_SESSION_TOKEN_LIMIT" in os.environ:
            self.session_config.token_limit = int(os.environ["QWEN_SESSION_TOKEN_LIMIT"])
        if "QWEN_AUTO_SAVE" in os.environ:
            self.session_config.auto_save = os.environ["QWEN_AUTO_SAVE"].lower() == "true"
        if "QWEN_COMPRESSION_THRESHOLD" in os.environ:
            self.session_config.compression_threshold = float(os.environ["QWEN_COMPRESSION_THRESHOLD"])
        
        # UI config
        if "QWEN_UI_THEME" in os.environ:
            self.ui_theme = os.environ["QWEN_UI_THEME"]
    
    def save(self) -> None:
        """Save configuration to persistent storage."""
        # Save to global config file
        global_config_path = Path.home() / ".qwen" / "config.yaml"
        global_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            "auth": {
                "default_provider": self.auth_provider,
                "providers": {
                    "qwen_oauth": {
                        "client_id": self.providers["qwen_oauth"].client_id,
                        "client_secret": self.providers["qwen_oauth"].client_secret,
                        "redirect_uri": self.providers["qwen_oauth"].redirect_uri
                    },
                    "openai_compatible": {
                        "api_key": self.providers["openai_compatible"].api_key,
                        "base_url": self.providers["openai_compatible"].base_url
                    }
                }
            },
            "models": {
                "default": self.model_settings.default_model,
                self.model_settings.default_model: {
                    "temperature": self.model_settings.temperature,
                    "max_tokens": self.model_settings.max_tokens,
                    "top_p": self.model_settings.top_p
                }
            },
            "session": {
                "token_limit": self.session_config.token_limit,
                "auto_save": self.session_config.auto_save,
                "compression_threshold": self.session_config.compression_threshold
            },
            "ui": {
                "theme": self.ui_theme
            }
        }
        
        try:
            with open(global_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config to {global_config_path}: {e}")