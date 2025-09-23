# Qwen Code Python Project Context

## Project Overview

This project is a Python rewrite of the Qwen Code CLI tool, originally implemented in Node.js/TypeScript. Qwen Code is an AI-powered command-line workflow tool specifically optimized for Qwen3-Coder models, adapted from Google's Gemini CLI with enhanced parsing and tool support.

The goal is to achieve 100% feature parity with the original Node.js implementation while leveraging Python's strengths for improved maintainability and extensibility.

**Note**: This appears to be a new project that hasn't been started yet. The directory contains only documentation and agent configuration files.

## Key Features

1. **AI Integration**: Interactive conversation with Qwen3-Coder models and other AI providers
2. **Code Analysis**: Query and edit large codebases beyond traditional context window limits
3. **Workflow Automation**: Automate operational tasks like handling pull requests and complex rebases
4. **Enhanced Parser**: Specifically optimized for Qwen-Coder models
5. **Session Management**: Persistent conversation history with token tracking
6. **Authentication**: Multiple authentication methods (Qwen OAuth, OpenAI-compatible, regional providers)
7. **File System Operations**: Read, analyze, and modify source files
8. **Git Integration**: Version control operations and commit analysis

## Architecture Overview

The application follows a modular architecture with clean separation of concerns:

- **CLI Interface Layer**: Command parsing and user interaction
- **Authentication Layer**: Multiple authentication providers (Qwen OAuth, OpenAI-compatible)
- **Session Management Layer**: Conversation history and state management
- **AI Integration Layer**: AI model clients and response parsing
- **File System Operations Layer**: Code analysis and file manipulation
- **Configuration Management Layer**: Hierarchical configuration system

## Core Technologies

- **Language**: Python 3.8+
- **CLI Framework**: Click or Typer
- **Async Support**: asyncio for concurrent operations
- **Database**: SQLite for session storage
- **Configuration**: YAML/JSON configuration files
- **Testing**: pytest with >90% coverage target
- **Packaging**: pip/PyPI distribution

## Project Structure

Based on the documentation, the expected project structure includes:

```
qwen-code-python/
├── qwen_code/                 # Main Python package
│   ├── __init__.py
│   ├── cli/                   # Command-line interface
│   ├── auth/                  # Authentication providers
│   ├── ai/                    # AI model integration
│   ├── session/               # Session management
│   ├── fs/                    # File system operations
│   ├── config/                # Configuration management
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
├── docs/                      # Documentation
├── .qwen/                     # AI agent configurations
└── README.md, setup.py, etc.  # Project metadata
```

## Key Components

### Authentication System
- Qwen OAuth 2.0 provider (recommended)
- OpenAI-compatible API key authentication
- Regional providers (ModelScope, OpenRouter, Alibaba Cloud)
- Secure credential storage and refresh

### AI Integration
- QwenClient for Dashscope API
- OpenAICompatibleClient for other providers
- Enhanced parser optimized for Qwen-Coder models
- Streaming responses with cancellation support
- Token counting and usage tracking

### Session Management
- SQLite database for conversation history
- Configurable token limits (default: 32,000 tokens)
- Conversation history compression
- Persistent session state across CLI restarts

### File System Operations
- Codebase analysis capabilities
- Safe file read/write operations with backups
- Git repository integration
- Project structure understanding

## Configuration

The application uses a hierarchical configuration system:

1. **Global Configuration**: `~/.qwen/config.yaml`
2. **Project Configuration**: `{project_root}/.qwen/project.yaml`
3. **Environment Variables**: For sensitive data and overrides
4. **Command-line Options**: For temporary overrides

## Testing Strategy

The project follows a comprehensive testing approach:

- **Unit Tests**: 70% coverage, testing individual components
- **Integration Tests**: 20% coverage, testing API and database integration
- **End-to-End Tests**: 10% coverage, testing complete user workflows
- **Performance Tests**: Benchmarking and load testing
- **Security Tests**: Credential protection and input validation
- **Compatibility Tests**: Cross-platform and Python version support

Target coverage: >90% line coverage, >85% branch coverage

## Development Setup

1. **Python Version**: 3.8+
2. **Virtual Environment**: Recommended for isolation
3. **Dependencies**: Managed through pip/PyPI
4. **Development Tools**: 
   - pytest for testing
   - mypy for type checking
   - black for code formatting
   - flake8 for linting

## Deployment

- **Primary Distribution**: PyPI package installation (`pip install qwen-code`)
- **Alternative Methods**: Source installation, Docker containers
- **System Requirements**: Python 3.8+, internet connectivity for AI models
- **Supported Platforms**: Linux, macOS, Windows

## Specialized AI Agents

The project includes several specialized AI agents for different aspects of development:

- **Master Orchestrator**: Technical architecture lead
- **Authentication Architect**: Security and credential management
- **AI Integration Specialist**: Model integration and parsing
- **CLI UX Designer**: User interface and experience
- **Database Engineer**: Data storage and management
- **DevOps Engineer**: Testing and deployment
- **Security Specialist**: Input validation and protection

## Documentation References

Key documentation files in the `docs/` directory:

- `technical-requirements-document.md`: Functional and non-functional requirements
- `system-architecture-document.md`: System architecture and migration considerations
- `api-specification-document.md`: Internal and external API specifications
- `database-design-document.md`: Database schema and data access patterns
- `ui-design-document.md`: Command-line interface design and user experience
- `test-strategy-document.md`: Comprehensive testing approach
- `deployment-guide.md`: Installation and deployment instructions

## Current Project Status

The project directory currently contains only documentation and agent configuration files. No Python source code has been implemented yet. This represents a new project that needs to be built from scratch following the specifications in the documentation.

## Next Steps

1. Create the basic project structure with `qwen_code` package
2. Implement the configuration management system
3. Set up authentication providers
4. Build the AI client infrastructure
5. Implement session management with SQLite
6. Create the CLI interface
7. Add file system operations
8. Implement comprehensive test suite
9. Create documentation and examples

This context file provides the necessary background for understanding and working with the Qwen Code Python CLI project, ensuring consistency with the original Node.js implementation while leveraging Python's capabilities.