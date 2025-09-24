# Qwen Code Py

Qwen Code Py is an AI-powered command-line workflow tool specifically optimized for Qwen3-Coder models. It's a Python rewrite of the original Node.js/TypeScript implementation, adapted from Google's Gemini CLI with enhanced parsing and tool support.

## Features

- **AI Integration**: Interactive conversation with Qwen3-Coder models and other AI providers
- **Code Analysis**: Query and edit large codebases beyond traditional context window limits
- **Workflow Automation**: Automate operational tasks like handling pull requests and complex rebases
- **Enhanced Parser**: Specifically optimized for Qwen-Coder models
- **Session Management**: Persistent conversation history with token tracking
- **Multiple Authentication**: Qwen OAuth, OpenAI-compatible API keys, and regional providers
- **File System Operations**: Read, analyze, and modify source files
- **Git Integration**: Version control operations and commit analysis
- **Smart Command Discovery**: Press `/` at any time to instantly see available commands
- **Auto-completion**: Use `Tab` for command auto-completion in interactive mode

## Installation

```bash
pip install qwen-code-py
```

## Usage

```bash
# Start interactive session
qwenpy

# Show help
qwenpy --help

# Use specific AI model
qwenpy chat --model gpt-4
```

## Configuration

Qwen Code Py can be configured through:
- Global configuration file (`~/.qwen/config.yaml`)
- Project-specific configuration (`.qwen/project.yaml`)
- Environment variables
- Command-line options

## Interactive Mode Features

In interactive mode, Qwen Code provides several productivity enhancements:

### Command Discovery
Press the forward slash (`/`) key at any time to instantly see a list of available commands without needing to press Enter.

### Auto-completion
Use the Tab key to auto-complete commands when typing. For example, typing `/he` and pressing Tab will complete to `/help`.

### Available Commands
- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/stats` - Show conversation statistics
- `/quit` - Exit the session

## Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/QwenLM/qwen-code-python.git
cd qwen-code-python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Testing

Run the test suite:

```bash
# Run unit tests
pytest tests/unit

# Run with coverage
pytest --cov=qwen_code tests/
```

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Documentation

For detailed documentation, check out these files:

- [User Guide](docs/user-guide.md) - Complete guide for end users
- [API Reference](docs/api-reference.md) - Technical API documentation
- [Development Guide](docs/development-guide.md) - Contributing and development setup
- [Technical Requirements](docs/technical-requirements-document.md) - System and feature requirements
- [Deployment Guide](docs/deployment-guide.md) - Installation and deployment instructions
- [Enterprise Deployment Guide](docs/enterprise-deployment-guide.md) - Production deployment best practices