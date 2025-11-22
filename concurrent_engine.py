"""
Concurrent Processing Engine with Domain Rate Limiting

Implements asyncio-based concurrent task processing with per-domain
rate limiting and circuit breaker pattern for robust scraping.

FIXED (Second-Pass Audit):
- Corrupted docstring in DomainRateLimiter.__init__
- defaultdict(asyncio.Lock) race condition - replaced with factory method
"""

import asyncio
import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

logger = logging.getLogger("ConcurrentEngine")


class DomainRateLimiter:
    """
    Per-domain rate limiter to respect server load.
    
    Ensures requests to the same domain are spaced appropriately.
    """
    
    def __init__(self, delay_seconds: float = 1.0):
        """
        Initialize domain rate limiter.
        
        Args:
            delay_seconds: Minimum delay between requests to same domain
        """
        self.delay_seconds = delay_seconds
        self.last_access: Dict[str, float] = {}
        
        # ╔═══════════════════════════════════════════════════════════════╗
        # ║ CRITICAL FIX: Removed defaultdict(asyncio.Lock) race         ║
        # ║ Using factory method with lock protection instead            ║
        # ╚═══════════════════════════════════════════════════════════════╝
        self.locks: Dict[str, asyncio.Lock] = {}
        self._locks_creation_lock = asyncio.Lock()
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return "unknown"
    
    async def _get_lock(self, domain: str) -> asyncio.Lock:
        """
        Get or create lock for domain (thread-safe).
        
        Prevents race condition where multiple coroutines
        create different locks for the same domain.
        
        Args:
            domain: Domain name
            
        Returns:
            asyncio.Lock for the domain
        """
        # Fast path: lock already exists
        if domain in self.locks:
            return self.locks[domain]
        
        # Slow path: need to create lock with protection
        async with self._locks_creation_lock:
            # Double-check after acquiring lock (another coroutine might have created it)
            if domain not in self.locks:
                self.locks[domain] = asyncio.Lock()
            return self.locks[domain]
    
    async def acquire(self, url: str):
        """
        Wait if necessary before allowing request to domain.
        
        Args:
            url: Target URL
        """
        domain = self._get_domain(url)
        
        # Get domain-specific lock safely
        domain_lock = await self._get_lock(domain)
        
        async with domain_lock:
            if domain in self.last_access:
                elapsed = time.time() - self.last_access[domain]
                if elapsed < self.delay_seconds:
                    wait_time = self.delay_seconds - elapsed
                    logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            self.last_access[domain] = time.time()


class CircuitBreaker:
    """
    Circuit breaker pattern to stop hammering failing domains.
    
    Opens circuit after consecutive failures, preventing resource waste.
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 300):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures: Dict[str, int] = defaultdict(int)
        self.opened_at: Dict[str, float] = {}
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return "unknown"
    
    def is_open(self, url: str) -> bool:
        """Check if circuit is open for this URL's domain."""
        domain = self._get_domain(url)
        
        if domain not in self.opened_at:
            return False
        
        # Check if timeout expired
        if time.time() - self.opened_at[domain] > self.timeout:
            # Reset circuit
            logger.info(f"Circuit breaker reset for {domain}")
            del self.opened_at[domain]
            self.failures[domain] = 0
            return False
        
        return True
    
    def record_success(self, url: str):
        """Record successful request."""
        domain = self._get_domain(url)
        self.failures[domain] = 0
        if domain in self.opened_at:
            del self.opened_at[domain]
    
    def record_failure(self, url: str):
        """Record failed request."""
        domain = self._get_domain(url)
        self.failures[domain] += 1
        
        if self.failures[domain] >= self.failure_threshold:
            self.opened_at[domain] = time.time()
            logger.warning(f"Circuit breaker OPENED for {domain} after {self.failures[domain]} failures")


class ConcurrentProcessor:
    """
    Manages concurrent task processing with semaphore-based concurrency control.
    """
    
    def __init__(
        self, 
        worker_count: int, 
        rate_limit_delay: float,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize concurrent processor.
        
        Args:
            worker_count: Maximum concurrent workers
            rate_limit_delay: Per-domain delay in seconds
            circuit_breaker: Optional circuit breaker instance
        """
        self.semaphore = asyncio.Semaphore(worker_count)
        self.rate_limiter = DomainRateLimiter(rate_limit_delay)
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.active_tasks: List[asyncio.Task] = []
    
    async def process_task(
        self,
        task_id: int,
        url: str,
        worker_func,
        *args,
        **kwargs
    ) -> tuple[int, Any, Optional[Exception]]:
        """
        Process a single task with concurrency control.
        
        Args:
            task_id: Task identifier
            url: Target URL
            worker_func: Async function to execute
            *args, **kwargs: Arguments for worker_func
            
        Returns:
            Tuple of (task_id, result, error)
        """
        # Check circuit breaker
        if self.circuit_breaker.is_open(url):
            logger.warning(f"Circuit breaker open for {url}, skipping")
            return (task_id, None, Exception("Circuit breaker open"))
        
        async with self.semaphore:
            try:
                # Rate limiting
                await self.rate_limiter.acquire(url)
                
                # Execute worker
                result = await worker_func(*args, **kwargs)
                
                # Record success
                self.circuit_breaker.record_success(url)
                
                return (task_id, result, None)
                
            except Exception as e:
                # Record failure
                self.circuit_breaker.record_failure(url)
                logger.error(f"Task {task_id} failed: {e}")
                return (task_id, None, e)
    
    async def process_batch(
        self,
        tasks: List[tuple],
        worker_func
    ) -> List[tuple]:
        """
        Process multiple tasks concurrently.
        
        Args:
            tasks: List of (task_id, url, *args) tuples
            worker_func: Async worker function
            
        Returns:
            List of (task_id, result, error) tuples
        """
        coroutines = [
            self.process_task(task_id, url, worker_func, *args)
            for task_id, url, *args in tasks
        ]
        
        results = await asyncio.gather(*coroutines, return_exceptions=False)
        return results
