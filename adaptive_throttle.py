"""
Adaptive Rate Limiting

Automatically adjusts request rate based on server response times.
Implements AIMD (Additive Increase Multiplicative Decrease) algorithm.
"""

import logging
import time
import asyncio
from typing import Dict
from collections import deque
from urllib.parse import urlparse

logger = logging.getLogger("AdaptiveThrottle")


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter using AIMD algorithm.
    
    Adjusts delay based on:
    - Response time (slow = increase delay)
    - Error rate (errors = increase delay)
    - Success rate (success = decrease delay)
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        min_delay: float = 0.1,
        max_delay: float = 10.0,
        target_response_time: float = 2.0
    ):
        """
        Initialize adaptive rate limiter.
        
        Args:
           initial_delay: Starting delay in seconds
            min_delay: Minimum delay
            max_delay: Maximum delay
            target_response_time: Target server response time
        """
        self.initial_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.target_response_time = target_response_time
        
        # Per-domain delays
        self.delays: Dict[str, float] = {}
        
        # Response time tracking (last 10 requests)
        self.response_times: Dict[str, deque] = {}
        
        # Error tracking
        self.error_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc
    
    def _get_current_delay(self, domain: str) -> float:
        """Get current delay for domain."""
        if domain not in self.delays:
            self.delays[domain] = self.initial_delay
        return self.delays[domain]
    
    def _get_avg_response_time(self, domain: str) -> float:
        """Get average response time for domain."""
        if domain not in self.response_times or not self.response_times[domain]:
            return 0.0
        return sum(self.response_times[domain]) / len(self.response_times[domain])
    
    async def acquire(self, url: str) -> float:
        """
        Wait before allowing request.
        
        Args:
            url: Target URL
            
        Returns:
            Current delay value
        """
        domain = self._get_domain(url)
        delay = self._get_current_delay(domain)
        
        logger.debug(f"Rate limiting {domain}: waiting {delay:.2f}s")
        await asyncio.sleep(delay)
        
        return delay
    
    def record_response(self, url: str, response_time: float, success: bool = True):
        """
        Record response and adjust delay.
        
        Args:
            url: Request URL
            response_time: Response time in seconds
            success: Whether request succeeded
        """
        domain = self._get_domain(url)
        
        # Initialize tracking
        if domain not in self.response_times:
            self.response_times[domain] = deque(maxlen=10)
        if domain not in self.error_counts:
            self.error_counts[domain] = 0
        if domain not in self.success_counts:
            self.success_counts[domain] = 0
        
        # Record response time
        self.response_times[domain].append(response_time)
        
        # Update counters
        if success:
            self.success_counts[domain] += 1
        else:
            self.error_counts[domain] += 1
        
        # Adjust delay
        self._adjust_delay(domain)
    
    def _adjust_delay(self, domain: str):
        """
        Adjust delay for domain using AIMD.
        
        AIMD Algorithm:
        - Additive Increase: Slowly increase on success (if fast)
        - Multiplicative Decrease: Rapidly decrease on error/slowness
        """
        current_delay = self._get_current_delay(domain)
        avg_response_time = self._get_avg_response_time(domain)
        
        total_requests = self.success_counts.get(domain, 0) + self.error_counts.get(domain, 0)
        error_rate = self.error_counts.get(domain, 0) / total_requests if total_requests > 0 else 0
        
        # Decision logic
        if error_rate > 0.1:  # >10% error rate
            # Multiplicative increase
            new_delay = min(current_delay * 2.0, self.max_delay)
            logger.warning(f"{domain}: High error rate ({error_rate:.1%}), increasing delay to {new_delay:.2f}s")
        
        elif avg_response_time > self.target_response_time:
            # Server is slow, increase delay
            new_delay = min(current_delay * 1.5, self.max_delay)
            logger.info(f"{domain}: Slow response ({avg_response_time:.2f}s), increasing delay to {new_delay:.2f}s")
        
        elif avg_response_time < self.target_response_time * 0.5:
            # Server is fast, decrease delay (additive)
            new_delay = max(current_delay - 0.1, self.min_delay)
            logger.info(f"{domain}: Fast response ({avg_response_time:.2f}s), decreasing delay to {new_delay:.2f}s")
        
        else:
            # Optimal range, no change
            new_delay = current_delay
        
        self.delays[domain] = new_delay
    
    def get_stats(self, domain: str = None) -> dict:
        """Get statistics for domain or all domains."""
        if domain:
            return {
                'delay': self.delays.get(domain, self.initial_delay),
                'avg_response_time': self._get_avg_response_time(domain),
                'errors': self.error_counts.get(domain, 0),
                'successes': self.success_counts.get(domain, 0)
            }
        else:
            return {
                'domains': list(self.delays.keys()),
                'delays': dict(self.delays)
            }
