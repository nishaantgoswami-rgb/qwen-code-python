# Deployment Guide - Qwen Code Python CLI

## 1. Overview

This document provides comprehensive deployment instructions for the Qwen Code Python CLI application, covering installation methods, configuration, and production deployment scenarios.

## 2. Installation Methods

### 2.1 PyPI Installation (Recommended)

#### Standard Installation
```bash
# Install latest stable version
pip install qwen-code

# Verify installation
qwen --version

# First-time setup
qwen config setup
```

#### Development Installation
```bash
# Install with development dependencies
pip install qwen-code[dev]

# Install pre-release versions
pip install --pre qwen-code

# Install specific version
pip install qwen-code==2.0.0
```

### 2.2 Installation from Source

#### Clone and Install
```bash
# Clone repository
git clone https://github.com/QwenLM/qwen-code-python.git
cd qwen-code-python

# Create virtual environment
python -m venv qwen-env
source qwen-env/bin/activate  # Linux/Mac
# or
qwen-env\Scripts\activate     # Windows

# Install in development mode
pip install -e .

# Install with all extras
pip install -e ".[dev,test,docs]"
```

#### Build Distribution
```bash
# Install build tools
pip install build twine

# Build distribution packages
python -m build

# Install from local wheel
pip install dist/qwen_code-*.whl
```

### 2.3 Container Deployment

#### Docker Installation
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install qwen-code
RUN pip install qwen-code

# Create non-root user
RUN useradd -m -u 1000 qwen
USER qwen

# Set up configuration directory
RUN mkdir -p /home/qwen/.qwen

# Entry point
ENTRYPOINT ["qwen"]
CMD ["--help"]
```

#### Build and Run Container
```bash
# Build image
docker build -t qwen-code:latest .

# Run container interactively
docker run -it --rm \
  -v $(pwd):/workspace \
  -v ~/.qwen:/home/qwen/.qwen \
  qwen-code:latest

# Run specific command
docker run --rm \
  -v $(pwd):/workspace \
  qwen-code:latest project analyze
```

#### Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  qwen-code:
    build: .
    volumes:
      - .:/workspace
      - ~/.qwen:/home/qwen/.qwen
      - ~/.gitconfig:/home/qwen/.gitconfig:ro
    environment:
      - QWEN_CONFIG_DIR=/home/qwen/.qwen
      - QWEN_LOG_LEVEL=INFO
    stdin_open: true
    tty: true
```

### 2.4 System Package Installation

#### Homebrew (macOS/Linux)
```bash
# Add tap
brew tap qwenlm/qwen-code

# Install package
brew install qwen-code

# Update package
brew upgrade qwen-code
```

#### Debian/Ubuntu Package
```bash
# Add repository
curl -fsSL https://packages.qwenlm.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/qwenlm.gpg
echo "deb [signed-by=/usr/share/keyrings/qwenlm.gpg] https://packages.qwenlm.com/debian stable main" | sudo tee /etc/apt/sources.list.d/qwenlm.list

# Update and install
sudo apt update
sudo apt install qwen-code
```

## 3. Environment Setup

### 3.1 Python Environment Requirements

#### Version Requirements
```bash
# Check Python version (3.8+ required)
python --version

# Check pip version (20.0+ recommended)
pip --version
```

#### Virtual Environment Setup
```bash
# Using venv (recommended)
python -m venv ~/.qwen-env
source ~/.qwen-env/bin/activate

# Using conda
conda create -n qwen-code python=3.11
conda activate qwen-code

# Using pyenv
pyenv install 3.11.0
pyenv virtualenv 3.11.0 qwen-code
pyenv activate qwen-code
```

### 3.2 System Dependencies

#### Linux (Ubuntu/Debian)
```bash
# Required system packages
sudo apt update
sudo apt install -y \
    python3-dev \
    python3-pip \
    git \
    curl \
    build-essential \
    libffi-dev \
    libssl-dev

# Optional packages for enhanced features
sudo apt install -y \
    sqlite3 \
    libsqlite3-dev \
    pkg-config
```

#### macOS
```bash
# Using Homebrew
brew install python git

# Using MacPorts
sudo port install python311 git

# Install Xcode command line tools
xcode-select --install
```

#### Windows
```powershell
# Using Chocolatey
choco install python git

# Using winget
winget install Python.Python.3.11
winget install Git.Git

# Using Scoop
scoop install python git
```

## 4. Configuration Setup

### 4.1 Initial Configuration

#### Interactive Setup
```bash
# Run interactive configuration wizard
qwen config setup

# Manual configuration
qwen config set auth.default_provider qwen_oauth
qwen config set session.token_limit 32000
qwen config set logging.level INFO
```

#### Configuration File
```yaml
# ~/.qwen/config.yaml
auth:
  default_provider: "qwen_oauth"
  providers:
    qwen_oauth:
      client_id: "${QWEN_CLIENT_ID:-default_client_id}"
      redirect_uri: "http://localhost:8080/callback"
    openai_compatible:
      api_key: "${OPENAI_API_KEY}"
      base_url: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"
      model: "${OPENAI_MODEL:-gpt-4}"

session:
  token_limit: 32000
  auto_save: true
  compression_threshold: 0.8
  history_dir: "~/.qwen/sessions"

logging:
  level: "INFO"
  file: "~/.qwen/logs/qwen-code.log"
  max_size: "10MB"
  backup_count: 5

ui:
  color_scheme: "auto"
  show_token_usage: true
  confirm_destructive_actions: true
```

### 4.2 Environment Variables

#### Authentication Variables
```bash
# Qwen OAuth
export QWEN_CLIENT_ID="your_client_id"
export QWEN_CLIENT_SECRET="your_client_secret"

# OpenAI Compatible
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4"

# Regional Providers
export QWEN_DASHSCOPE_API_KEY="your_dashscope_key"
export MODELSCOPE_API_KEY="your_modelscope_key"
```

#### Application Variables
```bash
# Configuration
export QWEN_CONFIG_DIR="$HOME/.qwen"
export QWEN_LOG_LEVEL="INFO"
export QWEN_SESSION_LIMIT="32000"

# Development
export QWEN_DEBUG="false"
export QWEN_PROFILE="false"
export QWEN_CACHE_DISABLED="false"
```

## 5. Production Deployment

### 5.1 Server Deployment

#### Systemd Service (Linux)
```ini
# /etc/systemd/system/qwen-code.service
[Unit]
Description=Qwen Code CLI Service
After=network.target

[Service]
Type=simple
User=qwen
Group=qwen
WorkingDirectory=/opt/qwen-code
Environment=QWEN_CONFIG_DIR=/opt/qwen-code/config
Environment=QWEN_LOG_LEVEL=INFO
ExecStart=/opt/qwen-code/venv/bin/qwen server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Service Management
```bash
# Enable and start service
sudo systemctl enable qwen-code
sudo systemctl start qwen-code

# Check status
sudo systemctl status qwen-code

# View logs
sudo journalctl -u qwen-code -f
```

### 5.2 Load Balancer Configuration

#### Nginx Configuration
```nginx
# /etc/nginx/sites-available/qwen-code
upstream qwen_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name qwen-code.example.com;
    
    location / {
        proxy_pass http://qwen_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for streaming
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 5.3 Monitoring and Logging

#### Prometheus Metrics
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter('qwen_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('qwen_request_duration_seconds', 'Request duration')
ACTIVE_SESSIONS = Gauge('qwen_active_sessions', 'Active sessions')

# AI model metrics
AI_REQUESTS = Counter('qwen_ai_requests_total', 'AI API requests', ['model', 'provider'])
TOKEN_USAGE = Counter('qwen_tokens_used_total', 'Tokens consumed', ['type'])
```

#### Logging Configuration
```yaml
# logging.yaml
version: 1
formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout
    
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: json
    filename: /var/log/qwen-code/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    
  syslog:
    class: logging.handlers.SysLogHandler
    level: WARNING
    formatter: standard
    address: ['localhost', 514]

loggers:
  qwen_code:
    level: DEBUG
    handlers: [console, file]
    propagate: false
    
  qwen_code.auth:
    level: INFO
    handlers: [file, syslog]
    propagate: false

root:
  level: WARNING
  handlers: [console]
```

## 6. Security Deployment

### 6.1 SSL/TLS Configuration

#### Let's Encrypt Setup
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d qwen-code.example.com

# Auto-renewal
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

### 6.2 Firewall Configuration

#### UFW (Ubuntu)
```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 'Nginx Full'

# Allow specific port for Qwen Code
sudo ufw allow 8000/tcp
```

#### iptables Rules
```bash
# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Save rules
iptables-save > /etc/iptables/rules.v4
```

## 7. Backup and Recovery

### 7.1 Data Backup

#### Backup Script
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/qwen-code"
CONFIG_DIR="$HOME/.qwen"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$TIMESTAMP"

# Backup configuration
cp -r "$CONFIG_DIR" "$BACKUP_DIR/$TIMESTAMP/"

# Backup databases
sqlite3 "$CONFIG_DIR/sessions.db" ".backup $BACKUP_DIR/$TIMESTAMP/sessions.db"

# Compress backup
tar -czf "$BACKUP_DIR/qwen-code-$TIMESTAMP.tar.gz" \
    -C "$BACKUP_DIR" "$TIMESTAMP"

# Clean up
rm -rf "$BACKUP_DIR/$TIMESTAMP"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

#### Automated Backup
```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

### 7.2 Recovery Process

#### Configuration Recovery
```bash
# Extract backup
tar -xzf qwen-code-20231201_020000.tar.gz

# Restore configuration
cp -r 20231201_020000/.qwen ~/

# Set permissions
chmod -R 600 ~/.qwen/credentials.db
chmod 755 ~/.qwen
```

## 8. Performance Optimization

### 8.1 System Tuning

#### File Descriptor Limits
```bash
# /etc/security/limits.conf
qwen soft nofile 65536
qwen hard nofile 65536

# Verify limits
ulimit -n
```

#### Memory Optimization
```bash
# /etc/sysctl.conf
vm.swappiness=10
vm.dirty_ratio=15
vm.dirty_background_ratio=5
```

### 8.2 Application Tuning

#### Environment Variables
```bash
# Python optimizations
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# SQLite optimizations
export QWEN_DB_CACHE_SIZE=2000
export QWEN_DB_SYNC_MODE=NORMAL
```

## 9. Troubleshooting

### 9.1 Common Issues

#### Installation Problems
```bash
# Permission issues
sudo chown -R $USER:$USER ~/.qwen

# Python path issues
which python
python -m site

# Dependency conflicts
pip check
pip list --outdated
```

#### Runtime Issues
```bash
# Check configuration
qwen config validate

# Check authentication
qwen auth status

# View logs
tail -f ~/.qwen/logs/qwen-code.log

# Debug mode
QWEN_DEBUG=true qwen chat
```

### 9.2 Performance Issues

#### Profiling
```bash
# Enable profiling
QWEN_PROFILE=true qwen project analyze

# Memory profiling
pip install memory-profiler
python -m memory_profiler qwen
```

## 10. Upgrading

### 10.1 Version Upgrade

#### Standard Upgrade
```bash
# Backup configuration
cp -r ~/.qwen ~/.qwen.backup

# Upgrade package
pip install --upgrade qwen-code

# Verify upgrade
qwen --version

# Test functionality
qwen config validate
```

#### Major Version Upgrade
```bash
# Check breaking changes
qwen migrate --dry-run

# Run migration
qwen migrate --from-version 1.x

# Verify migration
qwen config validate
qwen session list
```

## 11. Rich UI Dependencies

### 11.1 Rich Library Installation

The Qwen Code CLI uses the Rich library for enhanced visual presentation:

```bash
# Rich is automatically installed as a dependency
pip install qwen-code

# Verify Rich installation
python -c "import rich; print(f'Rich version: {rich.__version__}')"
```

### 11.2 Terminal Compatibility

#### Windows Compatibility
- **Windows Terminal**: Full Rich UI support
- **Command Prompt**: Limited color support
- **PowerShell**: Full Rich UI support

#### macOS Compatibility
- **Terminal.app**: Full Rich UI support
- **iTerm2**: Enhanced Rich UI support
- **Hyper**: Full Rich UI support

#### Linux Compatibility
- **GNOME Terminal**: Full Rich UI support
- **Konsole**: Full Rich UI support
- **xterm**: Limited Rich UI support
- **SSH Terminals**: Basic Rich UI support

### 11.3 Performance Considerations

```bash
# For systems with limited resources
export RICH_TRACEBACKS=0
export RICH_MIN_WIDTH=80
export RICH_MAX_WIDTH=120

# Disable Rich UI for minimal environments
export QWEN_DISABLE_RICH_UI=1
qwen --no-rich-ui
```

This deployment guide provides comprehensive instructions for installing, configuring, and maintaining the Qwen Code Python CLI in various environments, ensuring reliable and secure operation.