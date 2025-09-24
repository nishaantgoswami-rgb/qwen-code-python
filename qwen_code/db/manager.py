"""
Enhanced database manager using SQLAlchemy for Qwen Code.
"""

from typing import Optional, Dict, Any, Generator
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from qwen_code.db.models import Base
from qwen_code.db.connection_pool import get_connection_pool, TransactionManager
from qwen_code.db.backup_restore import BackupRestoreManager
from qwen_code.utils.logging import get_logger


logger = get_logger()


class DatabaseManager:
    """
    Enhanced database management class using SQLAlchemy with connection pooling.
    """
    
    def __init__(self, db_path: Path, pool_size: int = 10, max_overflow: int = 20):
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.connection_pool = None
        self.transaction_manager = None
        self.backup_manager = None
        
    def initialize(self) -> None:
        """
        Initialize database with connection pooling and backup manager.
        """
        # Create database directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection pool
        self.connection_pool = get_connection_pool(
            str(self.db_path), 
            self.pool_size, 
            self.max_overflow
        )
        
        # Initialize transaction manager
        self.transaction_manager = TransactionManager(self.connection_pool)
        
        # Initialize backup manager
        self.backup_manager = BackupRestoreManager(self.db_path)
        
        # Create database tables using a temporary engine
        from sqlalchemy import create_engine
        temp_engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(bind=temp_engine)
        temp_engine.dispose()
        # logger.info("Database tables created successfully")  # Removed for cleaner UI
        
        # logger.info(f"Database initialized at {self.db_path} with pool_size={self.pool_size}")  # Removed for cleaner UI
    
    def _create_tables(self) -> None:
        """Create all database tables based on models using a fresh connection."""
        # Use a temporary engine just for creating tables
        from sqlalchemy import create_engine
        temp_engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(bind=temp_engine)
        temp_engine.dispose()
        logger.info("Database tables created successfully")
    
    @contextmanager
    def get_session(self) -> Generator:
        """
        Get a database session from the pool with automatic cleanup.
        """
        if self.connection_pool is None:
            raise RuntimeError("Database not initialized")
        
        with self.connection_pool.get_session() as session:
            yield session
    
    @contextmanager
    def transaction(self):
        """
        Get a transactional database session with automatic rollback on error.
        """
        if self.connection_pool is None:
            raise RuntimeError("Database not initialized")
        
        with self.connection_pool.transaction() as session:
            yield session
    
    def close(self) -> None:
        """
        Close database connections and dispose of connection pool.
        """
        if self.connection_pool:
            self.connection_pool.dispose()
            # logger.info("Database connections closed")  # Removed for cleaner UI
    
    def backup(self, backup_path: Path, encrypt: bool = True, include_sensitive: bool = True) -> bool:
        """
        Create database backup with optional encryption.
        
        Args:
            backup_path: Path where the backup should be saved
            encrypt: Whether to encrypt the backup (default: True)
            include_sensitive: Whether to include sensitive data (default: True)
            
        Returns:
            True if backup was successful, False otherwise
        """
        return self.backup_manager.create_backup(backup_path, encrypt, include_sensitive)
    
    def restore(self, backup_path: Path, restore_to: Optional[Path] = None, 
                decrypt: bool = True) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to the backup file
            restore_to: Path where database should be restored (defaults to original location)
            decrypt: Whether to decrypt the backup during restore (default: True)
            
        Returns:
            True if restore was successful, False otherwise
        """
        return self.backup_manager.restore_backup(backup_path, restore_to, decrypt)
    
    def get_backup_info(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get information about a backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Dictionary with backup information or None if failed
        """
        return self.backup_manager.get_backup_info(backup_path)
    
    def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL query with parameters using a transaction.
        """
        from sqlalchemy import text
        
        if self.connection_pool is None:
            raise RuntimeError("Database not initialized")
        
        with self.transaction() as session:
            result = session.execute(text(sql), params or {})
            session.commit()  # Commit if it's a write operation
            return result