"""
Migration manager for Qwen Code database.
"""

import os
from pathlib import Path
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from qwen_code.utils.logging import get_logger


logger = get_logger()


class MigrationManager:
    """
    Manages database schema migrations using Alembic.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.alembic_dir = Path(__file__).parent / "alembic"
        self.alembic_ini_path = Path(__file__).parent / "alembic.ini"
        
    def _get_alembic_config(self) -> Config:
        """Create and return Alembic configuration object."""
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(self.alembic_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{self.db_path}")
        return alembic_cfg
    
    def init_db(self) -> None:
        """
        Initialize the database with the current schema.
        """
        logger.info(f"Initializing database at {self.db_path}")
        
        # First run any pending migrations
        self.run_migrations()
        
        logger.info("Database initialization completed")
    
    def run_migrations(self) -> None:
        """
        Run all pending migrations to bring the database up to date.
        """
        logger.info("Running database migrations...")
        
        alembic_cfg = self._get_alembic_config()
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migrations completed successfully")
    
    def create_migration(self, message: str) -> str:
        """
        Create a new migration file with the given message.
        
        Args:
            message: Description of the migration
            
        Returns:
            Path to the created migration file
        """
        logger.info(f"Creating migration: {message}")
        
        alembic_cfg = self._get_alembic_config()
        revision = command.revision(alembic_cfg, message, autogenerate=True)
        
        if revision:
            logger.info(f"Migration created: {revision}")
            return revision
        else:
            raise RuntimeError("Failed to create migration")
    
    def check_current_revision(self) -> str:
        """
        Check the current database revision.
        
        Returns:
            Current revision identifier
        """
        # For now, we'll check if the tables exist to determine if database is initialized
        engine = create_engine(f"sqlite:///{self.db_path}")
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if tables:
            # If we have tables, we're at the latest version
            # In a real implementation, we'd query the alembic_version table
            logger.info(f"Database has {len(tables)} tables")
            return "current"
        else:
            logger.info("Database is empty")
            return "empty"
    
    def rollback_migration(self, revision: str) -> None:
        """
        Rollback to a specific migration revision.
        
        Args:
            revision: Revision to rollback to
        """
        logger.info(f"Rolling back to revision: {revision}")
        
        alembic_cfg = self._get_alembic_config()
        command.downgrade(alembic_cfg, revision)
        
        logger.info(f"Successfully rolled back to revision: {revision}")


# Global migration manager instance
_migration_manager = None


def get_migration_manager(db_path: Path) -> MigrationManager:
    """
    Get the global migration manager instance.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        MigrationManager instance
    """
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager(db_path)
    return _migration_manager