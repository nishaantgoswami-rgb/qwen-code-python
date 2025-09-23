# Database Design Document - Qwen Code Python CLI

## 1. Overview

This document outlines the database design for the Qwen Code Python CLI application. The application uses a combination of local file-based storage and optional cloud synchronization for session data, configuration, and user preferences.

## 2. Storage Architecture

### 2.1 Storage Strategy
- **Primary Storage**: Local file-based storage using SQLite and JSON files
- **Configuration**: YAML/JSON configuration files
- **Session Data**: SQLite database for conversation history
- **Credentials**: Encrypted keyring storage
- **Cache**: Local file cache for API responses and project analysis

### 2.2 Directory Structure

```
~/.qwen/
├── config.yaml                 # Global configuration
├── credentials.db              # Encrypted credentials storage
├── sessions.db                 # Session data SQLite database
├── cache/                      # Cached data directory
│   ├── projects/              # Project analysis cache
│   ├── models/                # Model response cache
│   └── tokens/                # Token usage cache
├── logs/                      # Application logs
│   └── qwen-code.log
└── plugins/                   # User plugins directory

{project_root}/.qwen/
├── project.yaml               # Project-specific configuration
├── session_history.db         # Project session history
└── analysis_cache.json       # Project analysis cache
```

## 3. Database Schema

### 3.1 Sessions Database Schema

#### Table: `sessions`
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT,
    model TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON
);

CREATE INDEX idx_sessions_project ON sessions(project_path);
CREATE INDEX idx_sessions_created ON sessions(created_at);
CREATE INDEX idx_sessions_active ON sessions(is_active);
```

#### Table: `messages`
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    token_count INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_messages_role ON messages(role);
```

#### Table: `session_stats`
```sql
CREATE TABLE session_stats (
    session_id TEXT PRIMARY KEY,
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    user_messages INTEGER DEFAULT 0,
    assistant_messages INTEGER DEFAULT 0,
    average_response_time REAL,
    last_activity TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
```

### 3.2 Configuration Database Schema

#### Table: `user_preferences`
```sql
CREATE TABLE user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('string', 'integer', 'float', 'boolean', 'json')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Table: `auth_tokens`
```sql
CREATE TABLE auth_tokens (
    provider TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 Project Analysis Cache Schema

#### Table: `project_analysis`
```sql
CREATE TABLE project_analysis (
    project_path TEXT PRIMARY KEY,
    total_files INTEGER,
    total_lines INTEGER,
    languages JSON,
    dependencies JSON,
    structure JSON,
    last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_version TEXT
);
```

#### Table: `file_metadata`
```sql
CREATE TABLE file_metadata (
    file_path TEXT PRIMARY KEY,
    project_path TEXT,
    file_type TEXT,
    size_bytes INTEGER,
    lines_count INTEGER,
    last_modified TIMESTAMP,
    content_hash TEXT,
    analysis_data JSON,
    FOREIGN KEY (project_path) REFERENCES project_analysis(project_path)
);

CREATE INDEX idx_file_metadata_project ON file_metadata(project_path);
CREATE INDEX idx_file_metadata_type ON file_metadata(file_type);
```

### 3.4 Usage Analytics Schema

#### Table: `usage_stats`
```sql
CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    event_data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    user_id TEXT
);

CREATE INDEX idx_usage_stats_type ON usage_stats(event_type);
CREATE INDEX idx_usage_stats_timestamp ON usage_stats(timestamp);
```

#### Table: `api_usage`
```sql
CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_estimate REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT
);

CREATE INDEX idx_api_usage_provider ON api_usage(provider);
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);
```

## 4. Data Access Layer

### 4.1 Database Manager

```python
class DatabaseManager:
    """Central database management class."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
    
    async def initialize(self) -> None:
        """Initialize database with schema."""
        
    async def migrate(self, target_version: str) -> None:
        """Migrate database to target version."""
    
    async def backup(self, backup_path: Path) -> None:
        """Create database backup."""
```

### 4.2 Session Data Access

```python
class SessionRepository:
    """Repository for session data operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_session(self, project_path: str, model: str) -> Session:
        """Create new session."""
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve session by ID."""
    
    async def update_session(self, session: Session) -> None:
        """Update existing session."""
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session and related data."""
    
    async def get_active_sessions(self, project_path: str = None) -> List[Session]:
        """Get active sessions, optionally filtered by project."""

class MessageRepository:
    """Repository for message data operations."""
    
    async def add_message(self, session_id: str, message: Message) -> None:
        """Add message to session."""
    
    async def get_messages(self, session_id: str, limit: int = None) -> List[Message]:
        """Get messages for session."""
    
    async def delete_old_messages(self, session_id: str, keep_count: int) -> None:
        """Delete old messages keeping specified count."""
    
    async def compress_messages(self, session_id: str, compression_ratio: float) -> None:
        """Compress message history."""
```

### 4.3 Configuration Data Access

```python
class ConfigRepository:
    """Repository for configuration data."""
    
    async def get_preference(self, key: str) -> Any:
        """Get user preference value."""
    
    async def set_preference(self, key: str, value: Any) -> None:
        """Set user preference value."""
    
    async def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
    
    async def delete_preference(self, key: str) -> None:
        """Delete user preference."""

class AuthTokenRepository:
    """Repository for authentication tokens."""
    
    async def store_token(self, provider: str, access_token: str, 
                         refresh_token: str = None, expires_at: datetime = None) -> None:
        """Store authentication token."""
    
    async def get_token(self, provider: str) -> Optional[AuthToken]:
        """Get authentication token for provider."""
    
    async def refresh_token(self, provider: str, new_access_token: str, 
                           new_expires_at: datetime = None) -> None:
        """Update token after refresh."""
    
    async def delete_token(self, provider: str) -> None:
        """Delete authentication token."""
```

### 4.4 Project Analysis Data Access

```python
class ProjectAnalysisRepository:
    """Repository for project analysis data."""
    
    async def store_analysis(self, project_path: str, analysis: ProjectAnalysis) -> None:
        """Store project analysis results."""
    
    async def get_analysis(self, project_path: str) -> Optional[ProjectAnalysis]:
        """Get cached project analysis."""
    
    async def is_analysis_stale(self, project_path: str, max_age: timedelta) -> bool:
        """Check if analysis needs refresh."""
    
    async def update_file_metadata(self, file_path: str, metadata: FileMetadata) -> None:
        """Update file metadata cache."""
    
    async def get_project_files(self, project_path: str) -> List[FileMetadata]:
        """Get cached file metadata for project."""
```

## 5. Data Models

### 5.1 Core Data Models

```python
@dataclass
class Session:
    """Session data model."""
    id: str
    project_path: Optional[str]
    model: str
    created_at: datetime
    updated_at: datetime
    token_count: int = 0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Message:
    """Message data model."""
    id: Optional[int]
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    token_count: Optional[int]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProjectAnalysis:
    """Project analysis data model."""
    project_path: str
    total_files: int
    total_lines: int
    languages: Dict[str, int]
    dependencies: List[str]
    structure: Dict[str, Any]
    last_analyzed: datetime
    analysis_version: str

@dataclass
class FileMetadata:
    """File metadata model."""
    file_path: str
    project_path: str
    file_type: str
    size_bytes: int
    lines_count: int
    last_modified: datetime
    content_hash: str
    analysis_data: Dict[str, Any] = field(default_factory=dict)
```

## 6. Migration System

### 6.1 Migration Framework

```python
class Migration(ABC):
    """Base class for database migrations."""
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Migration version identifier."""
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Migration description."""
    
    @abstractmethod
    async def up(self, connection: sqlite3.Connection) -> None:
        """Apply migration."""
    
    @abstractmethod
    async def down(self, connection: sqlite3.Connection) -> None:
        """Rollback migration."""

class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.migrations: List[Migration] = []
    
    async def apply_migrations(self) -> None:
        """Apply pending migrations."""
    
    async def rollback_migration(self, target_version: str) -> None:
        """Rollback to target version."""
    
    async def get_current_version(self) -> str:
        """Get current database version."""
```

### 6.2 Initial Migrations

```python
class InitialMigration(Migration):
    """Initial database schema migration."""
    
    @property
    def version(self) -> str:
        return "001_initial"
    
    @property
    def description(self) -> str:
        return "Create initial database schema"
    
    async def up(self, connection: sqlite3.Connection) -> None:
        # Create all initial tables
        await self._create_sessions_table(connection)
        await self._create_messages_table(connection)
        await self._create_preferences_table(connection)
        # ... etc
```

## 7. Performance Optimization

### 7.1 Indexing Strategy

```sql
-- Performance indexes for common queries
CREATE INDEX idx_messages_session_timestamp ON messages(session_id, timestamp);
CREATE INDEX idx_sessions_project_active ON sessions(project_path, is_active);
CREATE INDEX idx_file_metadata_project_type ON file_metadata(project_path, file_type);
CREATE INDEX idx_usage_stats_type_timestamp ON usage_stats(event_type, timestamp);
```

### 7.2 Query Optimization

```python
class OptimizedQueries:
    """Optimized database queries."""
    
    @staticmethod
    async def get_recent_session_messages(session_id: str, limit: int = 50) -> List[Message]:
        """Get recent messages with optimized query."""
        query = """
            SELECT * FROM messages 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
    
    @staticmethod
    async def get_session_statistics(session_id: str) -> SessionStats:
        """Get session statistics with single query."""
        query = """
            SELECT 
                COUNT(*) as total_messages,
                SUM(token_count) as total_tokens,
                SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                MAX(timestamp) as last_activity
            FROM messages 
            WHERE session_id = ?
        """
```

## 8. Data Retention and Cleanup

### 8.1 Cleanup Policies

```python
class DataCleanupManager:
    """Manages data retention and cleanup."""
    
    async def cleanup_old_sessions(self, retention_days: int = 30) -> None:
        """Remove sessions older than retention period."""
    
    async def compress_old_conversations(self, compression_days: int = 7) -> None:
        """Compress old conversation history."""
    
    async def cleanup_cache(self, max_cache_size: int = 100_000_000) -> None:
        """Clean up cache when size exceeds limit."""
    
    async def archive_inactive_data(self, archive_days: int = 90) -> None:
        """Archive inactive data to separate storage."""
```

## 9. Backup and Recovery

### 9.1 Backup Strategy

```python
class BackupManager:
    """Manages database backups."""
    
    async def create_backup(self, backup_type: str = "full") -> Path:
        """Create database backup."""
    
    async def restore_backup(self, backup_path: Path) -> None:
        """Restore from backup."""
    
    async def schedule_backups(self, interval: timedelta) -> None:
        """Schedule automatic backups."""
    
    async def verify_backup(self, backup_path: Path) -> bool:
        """Verify backup integrity."""
```

This database design provides a robust foundation for the Qwen Code Python CLI application, ensuring efficient data storage, retrieval, and management while maintaining data integrity and performance.