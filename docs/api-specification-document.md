# API Specification Document - Qwen Code Python CLI

## 1. Overview

This document defines the API specifications for the Python rewrite of Qwen Code CLI, including internal module APIs, external service integrations, and configuration interfaces.

## 2. Core Module APIs

### 2.1 CLI Interface Module

#### `qwen_code.cli.main`

```python
def main() -> int:
    """Main entry point for the CLI application.
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """

def create_app() -> Application:
    """Create and configure the main application instance.
    
    Returns:
        Application: Configured application instance
    """
```

#### `qwen_code.cli.commands`

```python
@click.group()
def qwen() -> None:
    """Qwen Code CLI - AI-powered coding assistant."""

@qwen.command()
@click.option('--version', is_flag=True, help='Show version information')
def version() -> None:
    """Display version information."""

@qwen.command()
@click.option('--interactive', is_flag=True, default=True, help='Start interactive session')
@click.option('--model', default='qwen3-coder-plus', help='AI model to use')
def chat(interactive: bool, model: str) -> None:
    """Start AI conversation session."""
```

### 2.2 Authentication Module

#### `qwen_code.auth.providers`

```python
class AuthProvider(ABC):
    """Abstract base class for authentication providers."""
    
    @abstractmethod
    async def authenticate(self) -> AuthResult:
        """Perform authentication process."""
    
    @abstractmethod
    async def refresh_token(self) -> AuthResult:
        """Refresh authentication token."""
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if current authentication is valid."""

class QwenOAuthProvider(AuthProvider):
    """Qwen OAuth 2.0 authentication provider."""
    
    def __init__(self, client_id: str, redirect_uri: str):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
    
    async def authenticate(self) -> AuthResult:
        """Initiate OAuth flow with browser authentication."""

class OpenAICompatibleProvider(AuthProvider):
    """OpenAI-compatible API key authentication provider."""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
```

#### `qwen_code.auth.credentials`

```python
@dataclass
class Credentials:
    """Authentication credentials container."""
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    
class CredentialManager:
    """Manages secure storage and retrieval of credentials."""
    
    def store_credentials(self, credentials: Credentials) -> None:
        """Securely store credentials."""
    
    def load_credentials(self) -> Optional[Credentials]:
        """Load stored credentials."""
    
    def clear_credentials(self) -> None:
        """Remove stored credentials."""
```

### 2.3 AI Model Integration Module

#### `qwen_code.ai.client`

```python
class AIClient(ABC):
    """Abstract base class for AI model clients."""
    
    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """Send chat messages to AI model."""
    
    @abstractmethod
    async def stream_chat(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        """Stream chat response from AI model."""

class QwenClient(AIClient):
    """Qwen AI model client implementation."""
    
    def __init__(self, credentials: Credentials, model: str = "qwen3-coder-plus"):
        self.credentials = credentials
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    async def chat(self, messages: List[Message], **kwargs) -> AIResponse:
        """Send chat request to Qwen API."""

@dataclass
class Message:
    """Chat message container."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AIResponse:
    """AI model response container."""
    content: str
    usage: TokenUsage
    model: str
    timestamp: datetime = field(default_factory=datetime.now)
```

#### `qwen_code.ai.parser`

```python
class QwenParser:
    """Enhanced parser optimized for Qwen-Coder models."""
    
    def parse_code_blocks(self, content: str) -> List[CodeBlock]:
        """Extract and parse code blocks from AI response."""
    
    def parse_file_operations(self, content: str) -> List[FileOperation]:
        """Parse file operation commands from AI response."""
    
    def extract_commands(self, content: str) -> List[Command]:
        """Extract executable commands from AI response."""

@dataclass
class CodeBlock:
    """Represents a code block in AI response."""
    language: str
    code: str
    filename: Optional[str] = None
    start_line: Optional[int] = None

@dataclass
class FileOperation:
    """Represents a file operation command."""
    operation: Literal["create", "modify", "delete", "read"]
    path: str
    content: Optional[str] = None
```

### 2.4 Session Management Module

#### `qwen_code.session.manager`

```python
class SessionManager:
    """Manages conversation sessions and state."""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self.current_session: Optional[Session] = None
    
    def create_session(self) -> Session:
        """Create a new conversation session."""
    
    def load_session(self, session_id: str) -> Session:
        """Load existing session from storage."""
    
    def save_session(self, session: Session) -> None:
        """Persist session to storage."""
    
    def get_session_stats(self) -> SessionStats:
        """Get current session statistics."""

@dataclass
class Session:
    """Conversation session data."""
    id: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    token_count: int = 0
    model: str = "qwen3-coder-plus"
    
    def add_message(self, message: Message) -> None:
        """Add message to session."""
    
    def compress_history(self, target_tokens: int) -> None:
        """Compress conversation history to target token count."""

@dataclass
class SessionConfig:
    """Session configuration parameters."""
    token_limit: int = 32000
    auto_save: bool = True
    compression_threshold: float = 0.8
```

### 2.5 File System Operations Module

#### `qwen_code.fs.operations`

```python
class FileManager:
    """Handles file system operations for code analysis and modification."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    async def read_file(self, path: Path) -> str:
        """Read file content safely."""
    
    async def write_file(self, path: Path, content: str) -> None:
        """Write content to file with backup."""
    
    async def analyze_codebase(self) -> CodebaseAnalysis:
        """Analyze project structure and dependencies."""
    
    def get_project_files(self, patterns: List[str] = None) -> List[Path]:
        """Get list of project files matching patterns."""

class GitManager:
    """Git repository operations."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
    
    def get_recent_commits(self, days: int = 7) -> List[GitCommit]:
        """Get recent git commits."""
    
    def analyze_changes(self, since: str = "HEAD~10") -> ChangeAnalysis:
        """Analyze code changes in repository."""

@dataclass
class CodebaseAnalysis:
    """Results of codebase analysis."""
    total_files: int
    total_lines: int
    languages: Dict[str, int]
    dependencies: List[str]
    structure: Dict[str, Any]
```

### 2.6 Configuration Module

#### `qwen_code.config.settings`

```python
class Config:
    """Application configuration management."""
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from multiple sources."""
    
    @property
    def auth_provider(self) -> str:
        """Get configured authentication provider."""
    
    @property
    def model_settings(self) -> ModelConfig:
        """Get AI model configuration."""
    
    @property
    def session_config(self) -> SessionConfig:
        """Get session management configuration."""

@dataclass
class ModelConfig:
    """AI model configuration."""
    default_model: str = "qwen3-coder-plus"
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 0.95
```

## 3. External API Integrations

### 3.1 Qwen AI API

#### Authentication Endpoints

```
POST https://chat.qwen.ai/api/v1/oauth2/token
Authorization: Bearer {client_credentials}
Content-Type: application/json

Request Body:
{
    "grant_type": "authorization_code",
    "code": "{authorization_code}",
    "redirect_uri": "{redirect_uri}"
}

Response:
{
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "Bearer",
    "expires_in": 3600
}

POST https://chat.qwen.ai/api/v1/oauth2/device/code
Content-Type: application/json

Request Body:
{
    "client_id": "{client_id}",
    "scope": "openid profile email"
}

Response:
{
    "device_code": "string",
    "user_code": "string",
    "verification_uri": "https://chat.qwen.ai/device",
    "expires_in": 1800,
    "interval": 5
}
```

#### Chat Completion Endpoint

```
POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
Authorization: Bearer {access_token}
Content-Type: application/json

Request Body:
{
    "model": "qwen3-coder-plus",
    "messages": [
        {
            "role": "user",
            "content": "string"
        }
    ],
    "temperature": 0.1,
    "max_tokens": 4096,
    "stream": false
}

Response:
{
    "id": "string",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "qwen3-coder-plus",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "string"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 200,
        "total_tokens": 300
    }
}
```

### 3.2 OpenAI-Compatible APIs

#### Rate Limits and Error Handling

```python
@dataclass
class RateLimit:
    """Rate limiting information."""
    requests_per_minute: int
    tokens_per_minute: int
    remaining_requests: int
    remaining_tokens: int
    reset_time: datetime

class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int, error_code: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
```

## 4. Configuration API

### 4.1 Configuration File Format

#### Global Configuration (`~/.qwen/config.yaml`)

```yaml
auth:
  default_provider: "qwen_oauth"
  providers:
    qwen_oauth:
      client_id: "your_client_id"
      redirect_uri: "http://localhost:8080/callback"
    openai_compatible:
      api_key: "${OPENAI_API_KEY}"
      base_url: "${OPENAI_BASE_URL}"
      model: "${OPENAI_MODEL}"

session:
  token_limit: 32000
  auto_save: true
  compression_threshold: 0.8
  history_dir: "~/.qwen/sessions"

models:
  default: "qwen3-coder-plus"
  qwen3-coder-plus:
    temperature: 0.1
    max_tokens: 4096
    top_p: 0.95

logging:
  level: "INFO"
  file: "~/.qwen/logs/qwen-code.log"
  max_size: "10MB"
  backup_count: 5
```

#### Project Configuration (`.qwen/project.yaml`)

```yaml
project:
  name: "My Project"
  description: "Project description"
  ignore_patterns:
    - "node_modules/**"
    - "*.pyc"
    - "__pycache__/**"
    - ".git/**"

analysis:
  include_patterns:
    - "src/**/*.py"
    - "lib/**/*.py"
    - "*.py"
  max_file_size: "1MB"
  
workflows:
  custom_commands:
    - name: "analyze"
      description: "Analyze project architecture"
      prompt: "Analyze this project's architecture and main components"
```

### 4.2 Environment Variables

```bash
# Authentication
QWEN_CLIENT_ID=your_client_id
QWEN_CLIENT_SECRET=your_client_secret
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# Configuration
QWEN_CONFIG_DIR=~/.qwen
QWEN_LOG_LEVEL=INFO
QWEN_SESSION_LIMIT=32000

# Development
QWEN_DEBUG=false
QWEN_PROFILE=false
```

## 5. Plugin API

### 5.1 Plugin Interface

```python
class Plugin(ABC):
    """Base class for Qwen Code plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
    
    @abstractmethod
    def initialize(self, app: Application) -> None:
        """Initialize plugin with application instance."""
    
    @abstractmethod
    def register_commands(self) -> List[click.Command]:
        """Register CLI commands provided by plugin."""

class ParserPlugin(Plugin):
    """Plugin for custom parsers."""
    
    @abstractmethod
    def parse_response(self, content: str, context: ParseContext) -> ParseResult:
        """Parse AI response content."""

class WorkflowPlugin(Plugin):
    """Plugin for custom workflows."""
    
    @abstractmethod
    def execute_workflow(self, workflow: str, context: WorkflowContext) -> WorkflowResult:
        """Execute custom workflow."""
```

## 6. Error Handling API

### 6.1 Exception Hierarchy

```python
class QwenCodeError(Exception):
    """Base exception for Qwen Code errors."""

class AuthenticationError(QwenCodeError):
    """Authentication related errors."""

class APIError(QwenCodeError):
    """External API errors."""

class FileSystemError(QwenCodeError):
    """File system operation errors."""

class SessionError(QwenCodeError):
    """Session management errors."""

class ConfigurationError(QwenCodeError):
    """Configuration errors."""
```

## 7. Testing API

### 7.1 Test Utilities

```python
class MockAIClient:
    """Mock AI client for testing."""
    
    def __init__(self, responses: List[str]):
        self.responses = responses
        self.call_count = 0

class TestSessionManager:
    """Test utilities for session management."""
    
    @staticmethod
    def create_test_session() -> Session:
        """Create a test session with sample data."""

class FileSystemTestUtils:
    """Utilities for testing file operations."""
    
    @staticmethod
    def create_temp_project() -> Path:
        """Create temporary project structure for testing."""
```

This API specification provides the foundation for implementing a robust, maintainable, and extensible Python version of Qwen Code CLI while preserving all the functionality of the original Node.js implementation.