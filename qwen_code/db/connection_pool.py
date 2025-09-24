"""
Connection pooling and transaction management for Qwen Code database.
"""

from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SqlSession
from sqlalchemy.pool import QueuePool
from qwen_code.utils.logging import get_logger


logger = get_logger()


class ConnectionPool:
    """
    Enhanced database connection pool with transaction management.
    """
    
    def __init__(self, db_path: str, pool_size: int = 10, max_overflow: int = 20):
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.engine = None
        self.SessionLocal = None
        
    def initialize(self):
        """Initialize the connection pool."""
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            poolclass=QueuePool,  # Use QueuePool for connection pooling
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Connection pool initialized with pool_size={self.pool_size}, max_overflow={self.max_overflow}")
    
    @contextmanager
    def get_session(self) -> Generator[SqlSession, None, None]:
        """
        Get a database session from the pool with automatic cleanup.
        """
        if self.SessionLocal is None:
            raise RuntimeError("Connection pool not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction rolled back due to error: {str(e)}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions with automatic rollback on error.
        """
        if self.SessionLocal is None:
            raise RuntimeError("Connection pool not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction failed and was rolled back: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_raw_connection(self):
        """Get a raw database connection (use sparingly)."""
        if self.engine is None:
            raise RuntimeError("Connection pool not initialized")
        return self.engine.connect()
    
    def dispose(self):
        """Dispose of the connection pool."""
        if self.engine:
            self.engine.dispose()
            logger.info("Connection pool disposed")


class TransactionManager:
    """
    Manager for handling database transactions with proper isolation.
    """
    
    def __init__(self, connection_pool: ConnectionPool):
        self.pool = connection_pool
    
    @contextmanager
    def transaction_scope(self, isolation_level: str = "READ_COMMITTED"):
        """
        Create a transaction scope with specified isolation level.
        
        Args:
            isolation_level: SQL isolation level (not directly supported in SQLite)
        """
        with self.pool.transaction() as session:
            # Note: SQLite doesn't support custom isolation levels, 
            # but we can still use the transaction management
            yield session
    
    def execute_batch(self, operations):
        """
        Execute a batch of database operations in a single transaction.
        
        Args:
            operations: List of tuples (function, args, kwargs) to execute
        """
        with self.pool.transaction() as session:
            results = []
            for op_func, op_args, op_kwargs in operations:
                result = op_func(session, *op_args, **op_kwargs)
                results.append(result)
            return results
    
    def bulk_insert(self, model_class, data_list):
        """
        Perform bulk insert of data.
        
        Args:
            model_class: SQLAlchemy model class
            data_list: List of dictionaries with data to insert
        """
        with self.pool.transaction() as session:
            session.bulk_insert_mappings(model_class, data_list)
            logger.info(f"Bulk inserted {len(data_list)} records into {model_class.__tablename__}")
            return len(data_list)


# Global connection pool instance
_connection_pool = None


def get_connection_pool(db_path: str, pool_size: int = 10, max_overflow: int = 20) -> ConnectionPool:
    """
    Get the global connection pool instance.
    
    Args:
        db_path: Path to the database file
        pool_size: Size of the connection pool
        max_overflow: Maximum number of overflow connections
        
    Returns:
        ConnectionPool instance
    """
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(db_path, pool_size, max_overflow)
        _connection_pool.initialize()
    return _connection_pool