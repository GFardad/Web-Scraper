"""
Prometheus Metrics for Scraper Monitoring

Exposes metrics for Grafana dashboards.
"""

import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import REGISTRY

logger = logging.getLogger("Metrics")

# Performance metrics
requests_total = Counter(
    'scraper_requests_total',
    'Total scraping requests',
    ['status', 'site']
)

response_time = Histogram(
    'scraper_response_seconds',
    'Response time in seconds',
    ['site']
)

# Business metrics
products_scraped = Counter(
    'scraper_products_total',
    'Total products scraped',
    ['site', 'source']  # source: jsonld, css, etc.
)

failed_tasks = Counter(
    'scraper_failed_tasks_total',
    'Total failed tasks',
    ['reason']
)

captcha_encounters = Counter(
    'scraper_captcha_total',
    'Total CAPTCHA encounters',
    ['site', 'type']
)

# System metrics
active_tasks = Gauge(
    'scraper_active_tasks',
    'Currently active scraping tasks'
)

active_proxies = Gauge(
    'scraper_active_proxies',
    'Number of active proxies'
)

queue_size = Gauge(
    'scraper_queue_size',
    'Number of tasks in queue'
)


class MetricsCollector:
    """Helper class for metrics collection."""
    
    @staticmethod
    def record_request(site: str, status: str):
        """Record a scraping request."""
        requests_total.labels(status=status, site=site).inc()
    
    @staticmethod
    def record_response_time(site: str, duration: float):
        """Record response time."""
        response_time.labels(site=site).observe(duration)
    
    @staticmethod
    def record_product(site: str, source: str):
        """Record a scraped product."""
        products_scraped.labels(site=site, source=source).inc()
    
    @staticmethod
    def record_failure(reason: str):
        """Record a task failure."""
        failed_tasks.labels(reason=reason).inc()
    
    @staticmethod
    def record_captcha(site: str, captcha_type: str):
        """Record CAPTCHA encounter."""
        captcha_encounters.labels(site=site, type=captcha_type).inc()
    
    @staticmethod
    def set_active_tasks(count: int):
        """Set active tasks gauge."""
        active_tasks.set(count)
    
    @staticmethod
    def set_active_proxies(count: int):
        """Set active proxies gauge."""
        active_proxies.set(count)
    
    @staticmethod
    def set_queue_size(count: int):
        """Set queue size gauge."""
        queue_size.set(count)
    
    @staticmethod
    def get_metrics():
        """Get current metrics in Prometheus format."""
        return generate_latest(REGISTRY)
