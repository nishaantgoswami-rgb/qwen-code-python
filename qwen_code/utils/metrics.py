"""Metrics collection and monitoring module for Qwen Code CLI."""

import time
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging

# Try to import prometheus client, but make it optional
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Define mock classes to avoid breaking the application
    class MockMetric:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
    
    Counter = Histogram = Gauge = MockMetric

logger = logging.getLogger(__name__)

@dataclass
class MetricLabels:
    """Common metric labels for Qwen Code."""
    method: str = ""
    endpoint: str = ""
    model: str = ""
    provider: str = ""


class MetricsCollector:
    """Collects and exposes application metrics for monitoring."""
    
    def __init__(self):
        self.start_time = time.time()
        
        # Request metrics
        self.request_count = Counter(
            'qwen_requests_total', 
            'Total requests', 
            ['method', 'endpoint']
        ) if PROMETHEUS_AVAILABLE else None
        
        self.request_duration = Histogram(
            'qwen_request_duration_seconds', 
            'Request duration',
            ['method', 'endpoint']
        ) if PROMETHEUS_AVAILABLE else None
        
        # Session metrics
        self.active_sessions = Gauge(
            'qwen_active_sessions', 
            'Active sessions'
        ) if PROMETHEUS_AVAILABLE else None
        
        # AI model metrics
        self.ai_requests = Counter(
            'qwen_ai_requests_total', 
            'AI API requests', 
            ['model', 'provider']
        ) if PROMETHEUS_AVAILABLE else None
        
        self.token_usage = Counter(
            'qwen_tokens_used_total', 
            'Tokens consumed', 
            ['type']  # 'input', 'output', 'cache_read', 'cache_write'
        ) if PROMETHEUS_AVAILABLE else None
        
        # Error metrics
        self.error_count = Counter(
            'qwen_errors_total',
            'Total errors',
            ['type', 'endpoint']
        ) if PROMETHEUS_AVAILABLE else None
        
        # Performance metrics
        self.response_time = Histogram(
            'qwen_response_time_seconds',
            'Response time for operations',
            ['operation']
        ) if PROMETHEUS_AVAILABLE else None
        
        logger.info("Metrics collector initialized")
    
    def increment_request_count(self, method: str, endpoint: str):
        """Increment request count."""
        if self.request_count:
            self.request_count.labels(method=method, endpoint=endpoint).inc()
    
    def observe_request_duration(self, method: str, endpoint: str, duration: float):
        """Observe request duration."""
        if self.request_duration:
            self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def set_active_sessions(self, count: int):
        """Set active sessions count."""
        if self.active_sessions:
            self.active_sessions.set(count)
    
    def increment_ai_requests(self, model: str, provider: str):
        """Increment AI request count."""
        if self.ai_requests:
            self.ai_requests.labels(model=model, provider=provider).inc()
    
    def increment_token_usage(self, token_type: str, count: int = 1):
        """Increment token usage."""
        if self.token_usage:
            self.token_usage.labels(type=token_type).inc(count)
    
    def increment_error_count(self, error_type: str, endpoint: str = ""):
        """Increment error count."""
        if self.error_count:
            self.error_count.labels(type=error_type, endpoint=endpoint).inc()
    
    def observe_response_time(self, operation: str, duration: float):
        """Observe response time for operations."""
        if self.response_time:
            self.response_time.labels(operation=operation).observe(duration)
    
    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "prometheus_available": PROMETHEUS_AVAILABLE
        }
    
    def start_server(self, port: int = 8000):
        """Start the metrics server (if Prometheus is available)."""
        if PROMETHEUS_AVAILABLE:
            start_http_server(port)
            logger.info(f"Metrics server started on port {port}")
        else:
            logger.warning("Prometheus client not available, skipping metrics server")


# Global metrics collector instance
metrics = MetricsCollector()