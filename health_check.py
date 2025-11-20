"""
Health Check Endpoint

Provides HTTP endpoint for monitoring system health.
Returns status of all critical components.
"""

import logging
import time
import asyncio
from typing import Dict, Any
from aiohttp import web
import psutil

logger = logging.getLogger("HealthCheck")

# Track system start time
START_TIME = time.time()


class HealthCheckServer:
    """HTTP server for health checks."""
    
    def __init__(self, port: int = 8080):
        """
        Initialize health check server.
        
        Args:
            port: Port to run server on
        """
        self.port = port
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/metrics', self.metrics_handler)
        
        # External status checkers (set by main app)
        self.db_checker = None
        self.queue_size_fn = None
        self.active_tasks_fn = None
    
    async def health_handler(self, request):
        """Handle /health endpoint."""
        try:
            health_status = await self.get_health_status()
            
            if health_status['status'] == 'healthy':
                return web.json_response(health_status, status=200)
            else:
                return web.json_response(health_status, status=503)
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    async def metrics_handler(self, request):
        """Handle /metrics endpoint (Prometheus format)."""
        from metrics import MetricsCollector
        metrics_data = MetricsCollector.get_metrics()
        return web.Response(text=metrics_data.decode(), content_type='text/plain')
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'uptime_seconds': int(time.time() - START_TIME),
            'components': {}
        }
        
        # Database check
        if self.db_checker:
            try:
                db_healthy = await self.db_checker()
                status['components']['database'] = 'connected' if db_healthy else 'disconnected'
                if not db_healthy:
                    status['status'] = 'degraded'
            except:
                status['components']['database'] = 'error'
                status['status'] = 'unhealthy'
        else:
            status['components']['database'] = 'not_configured'
        
        # Queue size
        if self.queue_size_fn:
            try:
                queue_size = self.queue_size_fn()
                status['queue_size'] = queue_size
                if queue_size > 1000:
                    status['status'] = 'degraded'
            except:
                pass
        
        # Active tasks
        if self.active_tasks_fn:
            try:
                status['active_tasks'] = self.active_tasks_fn()
            except:
                pass
        
        # System resources
        try:
            status['system'] = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
            
            # Mark as degraded if resources critical
            if (status['system']['memory_percent'] > 90 or 
                status['system']['disk_percent'] > 90):
                status['status'] = 'degraded'
                
        except:
            pass
        
        return status
    
    async def start(self):
        """Start health check server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Health check server running on http://0.0.0.0:{self.port}/health")
    
    def set_db_checker(self, checker):
        """Set database health checker function."""
        self.db_checker = checker
    
    def set_queue_size_fn(self, fn):
        """Set queue size getter function."""
        self.queue_size_fn = fn
    
    def set_active_tasks_fn(self, fn):
        """Set active tasks getter function."""
        self.active_tasks_fn = fn


# Singleton instance
health_server = HealthCheckServer()


async def start_health_server(port: int = 8080):
    """Start health check server."""
    global health_server
    health_server = HealthCheckServer(port)
    await health_server.start()
