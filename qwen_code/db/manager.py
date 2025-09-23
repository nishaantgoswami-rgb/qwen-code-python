"""
Database manager for Qwen Code.
"""

from typing import Optional
import sqlite3
import json
from pathlib import Path
from datetime import datetime


class DatabaseManager:
    """Central database management class."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
    
    async def initialize(self) -> None:
        """Initialize database with schema."""
        # Create database directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        
        # Create tables
        await self._create_tables()
    
    async def _create_tables(self) -> None:
        """Create database tables."""
        if not self.connection:
            raise RuntimeError("Database not initialized")
        
        cursor = self.connection.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_path TEXT,
                model TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                token_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                metadata JSON
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                token_count INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Session stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_stats (
                session_id TEXT PRIMARY KEY,
                total_messages INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                user_messages INTEGER DEFAULT 0,
                assistant_messages INTEGER DEFAULT 0,
                average_response_time REAL,
                last_activity TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('string', 'integer', 'float', 'boolean', 'json')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Auth tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_tokens (
                provider TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Project analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_analysis (
                project_path TEXT PRIMARY KEY,
                total_files INTEGER,
                total_lines INTEGER,
                languages JSON,
                dependencies JSON,
                structure JSON,
                last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analysis_version TEXT
            )
        """)
        
        # File metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_path TEXT PRIMARY KEY,
                project_path TEXT,
                file_type TEXT,
                size_bytes INTEGER,
                lines_count INTEGER,
                last_modified TIMESTAMP,
                content_hash TEXT,
                analysis_data JSON,
                FOREIGN KEY (project_path) REFERENCES project_analysis(project_path)
            )
        """)
        
        # Usage stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                user_id TEXT
            )
        """)
        
        # API usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost_estimate REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_metadata_project ON file_metadata(project_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_metadata_type ON file_metadata(file_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_stats_type ON usage_stats(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_stats_timestamp ON usage_stats(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage(provider)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp)")
        
        self.connection.commit()
    
    async def migrate(self, target_version: str) -> None:
        """Migrate database to target version."""
        # Implementation will be expanded with actual migration logic
        pass
    
    async def backup(self, backup_path: Path) -> None:
        """Create database backup."""
        if not self.connection:
            raise RuntimeError("Database not initialized")
        
        # Create backup directory if it doesn't exist
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup database
        backup_conn = sqlite3.connect(backup_path)
        self.connection.backup(backup_conn)
        backup_conn.close()
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None