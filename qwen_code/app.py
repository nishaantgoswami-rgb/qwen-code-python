"""Main application module for Qwen Code."""

import asyncio
from typing import Optional
from qwen_code.config.settings import Config
from qwen_code.auth.credentials import CredentialManager
from qwen_code.db.manager import DatabaseManager
from qwen_code.session.manager import SessionManager
from qwen_code.utils.logging import get_logger
from pathlib import Path


class QwenCodeApplication:
    """Main application class for Qwen Code CLI."""
    
    def __init__(self):
        self.logger = get_logger()
        self.config = Config()
        self.credential_manager = CredentialManager()
        self.db_manager: Optional[DatabaseManager] = None
        self.session_manager: Optional[SessionManager] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the application."""
        try:
            if not self._initialized:
                self.logger.info("Initializing Qwen Code application")
                
                # Load configuration
                await self.config.load()
                self.logger.info("Configuration loaded successfully")
                
                # Initialize database
                db_path = Path.home() / ".qwen" / "sessions.db"
                self.db_manager = DatabaseManager(db_path)
                await self.db_manager.initialize()
                self.logger.info("Database initialized successfully")
                
                # Initialize session manager
                if self.db_manager:
                    self.session_manager = SessionManager(self.config.session_config, self.db_manager)
                    self.logger.info("Session manager initialized successfully")
                
                self._initialized = True
                self.logger.info("Application initialization completed")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize application: {str(e)}")
            raise
    
    def is_initialized(self) -> bool:
        """Check if the application is initialized."""
        return self._initialized
    
    async def cleanup(self) -> None:
        """Clean up application resources."""
        try:
            if self.db_manager:
                self.db_manager.close()
                self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")