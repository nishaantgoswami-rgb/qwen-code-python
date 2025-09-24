# Multi-stage build for Qwen Code CLI
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*


# Build stage
FROM base as builder

# Install build dependencies
RUN pip install --upgrade pip setuptools wheel build

# Copy project files
COPY pyproject.toml setup.cfg README.md /app/
COPY qwen_code/ /app/qwen_code/

# Build the package
RUN python -m build


# Production stage
FROM base as production

# Install the built package
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl

# Create non-root user
RUN useradd --create-home --shell /bin/bash qwen && \
    mkdir -p /home/qwen/.qwen /workspace && \
    chown -R qwen:qwen /home/qwen /workspace

# Set up configuration directory
ENV QWEN_CONFIG_DIR=/home/qwen/.qwen
ENV HOME=/home/qwen
ENV QWEN_LOG_LEVEL=INFO

# Switch to non-root user
USER qwen

# Set working directory to workspace
WORKDIR /workspace

# Health check - use the health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Expose port for health checks and metrics
EXPOSE 8000

# Default command
ENTRYPOINT ["qwenpy"]
CMD ["--help"]