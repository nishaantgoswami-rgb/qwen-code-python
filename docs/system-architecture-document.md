# System Architecture Document - Qwen Code CLI Tool

## Executive Summary

This document outlines the system architecture for rewriting the Qwen Code CLI tool from Node.js/TypeScript to Python. Qwen Code is an AI-powered command-line workflow tool specifically optimized for Qwen3-Coder models, adapted from Google's Gemini CLI with enhanced parsing and tool support.

## Current System Overview

### Technology Stack
- **Runtime**: Node.js 20+
- **Language**: TypeScript (98.3%) with minimal JavaScript (1.5%)
- **Package Manager**: npm
- **Distribution**: npm global package (@qwen-code/qwen-code)
- **Architecture**: CLI-based AI coding agent
- **License**: Apache 2.0

### Core Functionality
1. **Code Understanding & Editing** - Query and edit large codebases beyond traditional context window limits
2. **Workflow Automation** - Automate operational tasks like handling pull requests and complex rebases
3. **Enhanced Parser** - Adapted parser specifically optimized for Qwen-Coder models

## System Architecture Components

### 1. Command Line Interface (CLI) Layer
- **Current**: Commander.js framework for CLI parsing
- **Responsibilities**:
  - Command parsing and validation
  - Help system and documentation
  - Interactive session management
  - Keyboard shortcuts handling (Ctrl+C, Ctrl+D, Up/Down navigation)

### 2. Authentication & Authorization Layer
- **Multiple Authentication Methods**:
  - Qwen OAuth (Recommended - 2,000 requests/day)
  - OpenAI-compatible API providers
  - Regional providers (ModelScope, OpenRouter, Alibaba Cloud)
- **Credential Management**:
  - Environment variables
  - .env file configuration
  - Automatic credential refresh for OAuth

### 3. Session Management Layer
- **Token Tracking**: Configurable session limits (default: 32,000 tokens)
- **Conversation History**: Persistent conversation state
- **Commands**:
  - `/compress` - Compress conversation history
  - `/clear` - Clear all conversation history
  - `/stats` - Show current token usage
  - `/auth` - Switch authentication methods

### 4. AI Integration Layer
- **Model Support**:
  - Qwen3-Coder-Plus (commercial)
  - Qwen3-Coder-480B-A35B-Instruct (open source)
  - OpenAI-compatible models
- **Enhanced Parser**: Specifically adapted for Qwen-Coder models
- **Context Management**: Handles large codebases beyond traditional limits

### 5. File System Operations Layer
- **Code Analysis**: Static code analysis capabilities
- **File Manipulation**: Read, write, and modify source files
- **Project Structure**: Understanding of project hierarchies
- **Git Integration**: Git operations and commit analysis

### 6. Configuration Management Layer
- **Settings**: `.qwen/settings.json` in user home directory
- **Project-specific**: Project-level configuration support
- **Environment**: Multiple configuration sources (env vars, .env files)

## Data Flow Architecture

```
User Input → CLI Parser → Authentication → Session Manager → AI Model → File Operations → Response
     ↑                                                                                      ↓
     └─────────────────── Response Formatting ←─────────────────────────────────────────┘
```

## Integration Points

### External APIs
1. **Qwen AI Models** (dashscope.aliyuncs.com)
2. **OpenAI Compatible APIs** (various providers)
3. **OAuth Services** (qwen.ai authentication)

### File System
1. **User Home Directory** (`.qwen/` configuration)
2. **Project Directories** (codebase analysis)
3. **Git Repositories** (version control integration)

## Security Architecture

### Authentication Security
- OAuth 2.0 flow for Qwen authentication
- API key management for alternative providers
- Secure credential storage and refresh

### File System Security
- Project boundary enforcement
- Safe file operations
- Permission validation

## Performance Characteristics

### Current Benchmarks
- **Terminal-Bench Performance**:
  - Qwen3-Coder-480A35: 37.5% accuracy
  - Qwen3-Coder-30BA3B: 31.3% accuracy

### Scalability Considerations
- Token usage optimization (high consumption noted)
- Session management for long conversations
- File system operations for large codebases

## Deployment Architecture

### Distribution
- **Current**: npm global package installation
- **Alternative**: Homebrew package (macOS/Linux)
- **Source**: Direct installation from GitHub repository

### Requirements
- Node.js 20+ (current requirement)
- Internet connectivity for AI model access
- File system read/write permissions

## Key Architectural Patterns

1. **Command Pattern**: CLI commands as discrete operations
2. **Plugin Architecture**: Extensible tool and parser system
3. **Session State Management**: Persistent conversation handling
4. **Provider Pattern**: Multiple authentication and AI providers
5. **Configuration Hierarchy**: Layered configuration system

## Migration Considerations for Python

### Core Dependencies to Replace
- **Commander.js** → Click or argparse (Python CLI frameworks)
- **Node.js runtime** → Python 3.8+ runtime
- **npm package system** → pip/PyPI distribution
- **TypeScript type system** → Python type hints with mypy

### Architecture Preservation
- Maintain modular layer separation
- Preserve plugin/extension capabilities
- Keep configuration hierarchy intact
- Maintain session management patterns

### Enhanced Opportunities
- **Better Package Management**: Python's pip and virtual environments
- **Rich CLI Libraries**: Rich, Typer for enhanced UX
- **Async Capabilities**: asyncio for concurrent operations
- **Data Processing**: pandas, numpy for advanced code analysis

### Rich UI Features
- **Enhanced Visual Presentation**: Panels, tables, and markdown rendering using the Rich library
- **Color-Coded Messaging**: Distinct colors for different message types (user input, AI responses, system messages)
- **Progress Indicators**: Animated spinners during AI processing and long operations
- **Structured Information Display**: Organized panels for welcome messages, authentication status, and error handling
- **Tabular Data Presentation**: Formatted tables for command listings, session management, and statistics
- **Markdown Rendering**: Syntax highlighting for code blocks in AI responses

## Technical Debt & Improvement Opportunities

1. **Token Usage Optimization**: Current implementation has high token consumption
2. **Error Handling**: Robust error handling for network and file operations
3. **Testing Infrastructure**: Comprehensive test suite for reliability
4. **Documentation**: Enhanced inline documentation and user guides
5. **Performance**: Caching and optimization for repeated operations
6. **UI/UX Enhancement**: Rich library integration for improved visual presentation

This architecture document serves as the foundation for the Python rewrite, ensuring all critical components and patterns are preserved while leveraging Python's strengths for improved maintainability and extensibility.