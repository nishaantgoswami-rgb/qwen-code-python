"""Monitoring and health check functionality for Qwen Code CLI."""

import asyncio
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
import logging

from qwen_code.utils.metrics import metrics

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Represents the health status of the application."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    checks: Dict[str, Any]
    details: Dict[str, Any]


class HealthChecker:
    """Performs health checks for the Qwen Code CLI application."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.checks = {}
        
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resources (CPU, memory, disk)."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Convert bytes to GB for disk
            total_disk_gb = disk.total / (1024**3)
            free_disk_gb = disk.free / (1024**3)
            
            resources_status = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": free_disk_gb,
                "disk_total_gb": total_disk_gb
            }
            
            # Check for issues
            issues = []
            if cpu_percent > 80:
                issues.append(f"High CPU usage: {cpu_percent}%")
                resources_status["status"] = "degraded"
            if memory.percent > 85:
                issues.append(f"High memory usage: {memory.percent}%")
                resources_status["status"] = "degraded"
            if disk.percent > 90:
                issues.append(f"Low disk space: {disk.percent}% used")
                resources_status["status"] = "degraded"
                
            resources_status["issues"] = issues
            return resources_status
            
        except Exception as e:
            logger.error(f"Error checking system resources: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_config_access(self) -> Dict[str, Any]:
        """Check if configuration can be accessed properly."""
        try:
            from qwen_code.config.settings import Config
            config = Config()
            await config.load()
            
            config_status = {
                "status": "healthy",
                "config_loaded": True,
                "config_path": str(config.config_path) if config.config_path else "Not set"
            }
            
            return config_status
            
        except Exception as e:
            logger.error(f"Error checking config access: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_database_connection(self) -> Dict[str, Any]:
        """Check database connection."""
        try:
            from qwen_code.db.manager import DatabaseManager
            from pathlib import Path
            
            db_path = Path.home() / ".qwen" / "sessions.db"
            if not db_path.exists():
                # Database doesn't exist yet, which is OK for a fresh installation
                db_status = {
                    "status": "healthy",
                    "exists": False,
                    "path": str(db_path)
                }
            else:
                # Test actual connection
                db_manager = DatabaseManager(db_path)
                await db_manager.initialize()
                
                # Perform a simple query
                async with db_manager.get_connection() as conn:
                    cursor = await conn.execute("SELECT 1")
                    await cursor.fetchone()
                
                db_status = {
                    "status": "healthy",
                    "exists": True,
                    "path": str(db_path),
                    "connection_ok": True
                }
            
            return db_status
            
        except Exception as e:
            logger.error(f"Error checking database connection: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_external_connectivity(self) -> Dict[str, Any]:
        """Check external connectivity for AI services."""
        try:
            import aiohttp
            # Test basic connectivity
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Test connection to a basic endpoint
                async with session.get('https://httpbin.org/get') as response:
                    connectivity_status = {
                        "status": "healthy" if response.status == 200 else "degraded",
                        "response_code": response.status,
                        "connectivity_ok": response.status == 200
                    }
                    return connectivity_status
            
        except Exception as e:
            logger.warning(f"External connectivity check failed: {str(e)}")
            # Connectivity issues don't necessarily make the app unhealthy,
            # since it might be working in offline mode
            return {
                "status": "degraded",  # Not unhealthy, just degraded
                "error": str(e),
                "connectivity_ok": False
            }
    
    async def check_application_health(self) -> HealthStatus:
        """Perform all health checks and return overall status."""
        # Run all checks concurrently
        check_results = await asyncio.gather(
            self.check_system_resources(),
            self.check_config_access(),
            self.check_database_connection(),
            self.check_external_connectivity(),
            return_exceptions=True
        )
        
        # Process results
        check_names = [
            "system_resources",
            "config_access", 
            "database_connection",
            "external_connectivity"
        ]
        
        checks = {}
        overall_status = "healthy"
        
        for i, result in enumerate(check_names):
            if isinstance(check_results[i], Exception):
                checks[result] = {
                    "status": "unhealthy",
                    "error": str(check_results[i])
                }
                overall_status = "unhealthy"
            else:
                checks[result] = check_results[i]
                # Update overall status based on individual check
                if check_results[i]["status"] == "unhealthy" and overall_status != "unhealthy":
                    overall_status = "unhealthy"
                elif check_results[i]["status"] == "degraded" and overall_status == "healthy":
                    overall_status = "degraded"
        
        # Create detailed status information
        details = {
            "uptime": str(datetime.now() - self.start_time),
            "metrics_summary": metrics.get_metrics_summary(),
            "pid": os.getpid(),
            "process_name": "qwen-code-py"
        }
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.now(),
            checks=checks,
            details=details
        )


class MonitoringService:
    """Main monitoring service that coordinates health checks and metrics."""
    
    def __init__(self):
        self.health_checker = HealthChecker()
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self, check_interval: int = 300):  # 5 minutes
        """Start periodic monitoring in the background."""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(check_interval)
        )
        logger.info(f"Started monitoring with {check_interval}s interval")
    
    async def stop_monitoring(self):
        """Stop the monitoring service."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.is_monitoring = False
        logger.info("Stopped monitoring")
    
    async def _monitoring_loop(self, interval: int):
        """Internal monitoring loop that periodically runs checks."""
        while self.is_monitoring:
            try:
                health = await self.health_checker.check_application_health()
                logger.debug(f"Health check completed: {health.status}")
                
                # Update metrics based on health status
                if health.status == "healthy":
                    metrics.set_active_sessions(1)  # Simplified for demo
                else:
                    metrics.increment_error_count("health_issue", "monitoring")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                metrics.increment_error_count("monitoring_error", "monitoring")
                await asyncio.sleep(interval)
    
    async def get_current_health(self) -> HealthStatus:
        """Get the current health status of the application."""
        return await self.health_checker.check_application_health()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "timestamp": datetime.now().isoformat()
        }


# Global monitoring service instance
monitoring_service = MonitoringService()