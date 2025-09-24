"""HTTP server with health check endpoints for Qwen Code CLI."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
from aiohttp import web
import argparse
import os

from qwen_code.utils.monitoring import monitoring_service, HealthStatus
from qwen_code.utils.metrics import metrics
from qwen_code.app import QwenCodeApplication

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """HTTP server that provides health check and monitoring endpoints."""
    
    def __init__(self, app: QwenCodeApplication, port: int = 8000):
        self.app_instance = app
        self.port = port
        self.web_app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Set up routes
        self.setup_routes()
    
    def setup_routes(self):
        """Set up the HTTP routes for health checks and monitoring."""
        self.web_app.router.add_get('/health', self.health_handler)
        self.web_app.router.add_get('/health/live', self.liveness_handler)
        self.web_app.router.add_get('/health/ready', self.readiness_handler)
        self.web_app.router.add_get('/metrics', self.metrics_handler)
        self.web_app.router.add_get('/info', self.info_handler)
        self.web_app.router.add_get('/status', self.status_handler)
        self.web_app.router.add_get('/ping', self.ping_handler)
        self.web_app.router.add_get('/stats', self.stats_handler)
    
    async def health_handler(self, request) -> web.Response:
        """Main health check endpoint."""
        try:
            health_status = await monitoring_service.get_current_health()
            response_data = {
                "status": health_status.status,
                "timestamp": health_status.timestamp.isoformat(),
                "checks": health_status.checks,
                "details": health_status.details,
                "version": self.get_version()
            }
            
            status_code = 200 if health_status.status == "healthy" else 503
            return web.json_response(response_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
    
    async def liveness_handler(self, request) -> web.Response:
        """Liveness probe - indicates if the application is running."""
        try:
            # Liveness probe should be minimal and just check if the service is alive
            response_data = {
                "status": "alive",
                "timestamp": datetime.now().isoformat(),
                "version": self.get_version()
            }
            return web.json_response(response_data, status=200)
            
        except Exception as e:
            logger.error(f"Liveness check failed: {str(e)}")
            return web.json_response({
                "status": "dead",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
    
    async def readiness_handler(self, request) -> web.Response:
        """Readiness probe - indicates if the application is ready to serve requests."""
        try:
            # Check if we can handle requests
            health_status = await monitoring_service.get_current_health()
            
            # For readiness, we might be more strict than liveness
            is_ready = health_status.status in ["healthy", "degraded"]
            
            response_data = {
                "status": "ready" if is_ready else "not_ready",
                "timestamp": datetime.now().isoformat(),
                "version": self.get_version(),
                "health_details": {
                    "overall_status": health_status.status,
                    "checks": health_status.checks
                }
            }
            
            status_code = 200 if is_ready else 503
            return web.json_response(response_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            return web.json_response({
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
    
    async def metrics_handler(self, request) -> web.Response:
        """Metrics endpoint - returns application metrics."""
        try:
            # Return prometheus-style metrics or JSON metrics
            if request.headers.get('Accept', '').startswith('text/plain'):
                # If client wants prometheus format
                from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
                data = generate_latest()
                return web.Response(
                    body=data,
                    content_type=CONTENT_TYPE_LATEST
                )
            else:
                # Return JSON metrics
                metrics_summary = metrics.get_metrics_summary()
                system_metrics = monitoring_service.get_system_metrics()
                
                response_data = {
                    "metrics": metrics_summary,
                    "system": system_metrics,
                    "timestamp": datetime.now().isoformat(),
                    "version": self.get_version()
                }
                return web.json_response(response_data)
                
        except Exception as e:
            logger.error(f"Metrics retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
    
    async def info_handler(self, request) -> web.Response:
        """Info endpoint - returns application information."""
        try:
            response_data = {
                "name": "qwen-code-py",
                "version": self.get_version(),
                "description": "AI-powered coding assistant CLI tool",
                "author": "Qwen Team",
                "license": "Apache-2.0",
                "uptime_seconds": metrics.get_uptime_seconds(),
                "timestamp": datetime.now().isoformat()
            }
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"Info retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
    
    async def status_handler(self, request) -> web.Response:
        """Status endpoint - returns detailed application status."""
        try:
            health_status = await monitoring_service.get_current_health()
            system_metrics = monitoring_service.get_system_metrics()
            
            response_data = {
                "status": health_status.status,
                "health": {
                    "overall_status": health_status.status,
                    "checks": health_status.checks,
                    "details": health_status.details
                },
                "system": system_metrics,
                "metrics": metrics.get_metrics_summary(),
                "timestamp": datetime.now().isoformat(),
                "version": self.get_version(),
                "app_initialized": self.app_instance.is_initialized()
            }
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"Status retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
    
    async def ping_handler(self, request) -> web.Response:
        """Simple ping endpoint."""
        try:
            response_data = {
                "message": "pong",
                "timestamp": datetime.now().isoformat(),
                "version": self.get_version()
            }
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"Ping failed: {str(e)}")
            return web.json_response({"error": str(e)}, status=503)
    
    async def stats_handler(self, request) -> web.Response:
        """Statistics endpoint - returns usage and performance statistics."""
        try:
            # Get application statistics
            stats = {
                "uptime_seconds": metrics.get_uptime_seconds(),
                "request_count": 0,  # This would need to be tracked properly
                "error_count": 0,    # This would need to be tracked properly
                "active_sessions": 0, # Would need to be updated based on actual sessions
                "version": self.get_version(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Add system metrics
            system_metrics = monitoring_service.get_system_metrics()
            stats["system"] = system_metrics
            
            return web.json_response(stats)
            
        except Exception as e:
            logger.error(f"Stats retrieval failed: {str(e)}")
            return web.json_response({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=503)
    
    def get_version(self) -> str:
        """Get the application version."""
        try:
            from qwen_code import __version__
            return __version__
        except ImportError:
            return "unknown"
    
    async def start(self):
        """Start the health check server."""
        self.runner = web.AppRunner(self.web_app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        
        logger.info(f"Health check server started on port {self.port}")
        logger.info(f"Available endpoints: /health, /health/live, /health/ready, /metrics, /info, /status, /ping, /stats")
    
    async def stop(self):
        """Stop the health check server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("Health check server stopped")


async def run_server(app: QwenCodeApplication, port: int = 8000):
    """Run the health check server."""
    server = HealthCheckServer(app, port)
    
    try:
        await server.start()
        
        # Keep the server running
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        await server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qwen Code Health Check Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()
    
    # Initialize the Qwen Code application
    qwen_app = QwenCodeApplication()
    asyncio.run(qwen_app.initialize())
    
    # Start the server
    asyncio.run(run_server(qwen_app, args.port))