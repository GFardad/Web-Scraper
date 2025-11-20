"""
Adaptive Throttling Module

Implements AIMD (Additive Increase, Multiplicative Decrease) algorithm
to dynamically adjust request delays based on server response times and errors.

Features:
- Automatic delay adjustment based on success/failure
- Per-domain throttling state
- Hot-reloadable configuration
- Thread-safe state management
"""

import logging
import time
import threading
from typing import Dict, Optional
from urllib.parse import urlparse
from config_manager import get_config

logger = logging.getLogger(__name__)

class AdaptiveThrottler:
    """
    Manages dynamic delays for scraping requests using AIMD algorithm.
    
    Logic:
    - On Success: Decrease delay linearly (Additive Decrease)
    - On Failure (429/5xx): Increase delay exponentially (Multiplicative Increase)
    - Respects min/max delay bounds from config
    """
    
    def __init__(self):
        self.config = get_config()
        self._lock = threading.Lock()
        self._domain_delays: Dict[str, float] = {}
        self._success_counts: Dict[str, int] = {}
        
        # Load initial config
        self._load_config()
        
        # Register for config updates
        self.config.register_callback(self._on_config_change)
        
    def _load_config(self):
        """Load throttling parameters from config."""
        throttle_config = self.config.get('scraper.rate_limiting', {})
        adaptive_config = throttle_config.get('adaptive', {})
        
        self.enabled = adaptive_config.get('enabled', True)
        self.base_delay = float(throttle_config.get('base_delay', 2.0))
        self.max_delay = float(throttle_config.get('max_delay', 30.0))
        self.min_delay = float(throttle_config.get('per_domain_delay', 1.0))
        
        self.increase_factor = float(adaptive_config.get('increase_factor', 2.0))
        self.decrease_factor = float(adaptive_config.get('decrease_factor', 0.5))
        self.success_threshold = int(adaptive_config.get('success_threshold', 5))
        
        logger.debug(f"Adaptive Throttler loaded: Enabled={self.enabled}, Base={self.base_delay}s")

    def _on_config_change(self, old_config, new_config):
        """Handle config hot-reloads."""
        logger.info("🔄 Adaptive Throttler updating config...")
        self._load_config()

    def _get_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc
        except Exception:
            return "unknown"

    def get_delay(self, url: str) -> float:
        """
        Get the current required delay for a URL.
        
        Args:
            url: The target URL
            
        Returns:
            Float delay in seconds
        """
        if not self.enabled:
            return self.base_delay
            
        domain = self._get_domain(url)
        
        with self._lock:
            return self._domain_delays.get(domain, self.base_delay)

    def record_success(self, url: str):
        """
        Record a successful request and potentially decrease delay.
        
        Args:
            url: The target URL
        """
        if not self.enabled:
            return
            
        domain = self._get_domain(url)
        
        with self._lock:
            # Initialize if missing
            if domain not in self._domain_delays:
                self._domain_delays[domain] = self.base_delay
                self._success_counts[domain] = 0
            
            # Increment success streak
            self._success_counts[domain] += 1
            
            # Check if we should decrease delay
            if self._success_counts[domain] >= self.success_threshold:
                current_delay = self._domain_delays[domain]
                # Additive Decrease
                new_delay = max(self.min_delay, current_delay - self.decrease_factor)
                
                if new_delay < current_delay:
                    logger.debug(f"📉 Decreasing delay for {domain}: {current_delay:.2f}s -> {new_delay:.2f}s")
                    self._domain_delays[domain] = new_delay
                    self._success_counts[domain] = 0  # Reset counter

    def record_failure(self, url: str, status_code: Optional[int] = None):
        """
        Record a failed request and increase delay.
        
        Args:
            url: The target URL
            status_code: HTTP status code (optional)
        """
        if not self.enabled:
            return
            
        domain = self._get_domain(url)
        
        # Only throttle on specific errors (429 Too Many Requests, 5xx Server Errors)
        should_throttle = True
        if status_code:
            if status_code == 404:
                should_throttle = False  # Don't throttle on Not Found
            elif status_code < 400:
                should_throttle = False
        
        if not should_throttle:
            return

        with self._lock:
            # Initialize if missing
            if domain not in self._domain_delays:
                self._domain_delays[domain] = self.base_delay
            
            current_delay = self._domain_delays[domain]
            
            # Multiplicative Increase
            new_delay = min(self.max_delay, current_delay * self.increase_factor)
            
            if new_delay > current_delay:
                logger.warning(f"📈 Throttling {domain}: {current_delay:.2f}s -> {new_delay:.2f}s (Status: {status_code})")
                self._domain_delays[domain] = new_delay
                self._success_counts[domain] = 0  # Reset success streak

    def sleep(self, url: str):
        """
        Sleep for the calculated delay period.
        
        Args:
            url: The target URL
        """
        delay = self.get_delay(url)
        if delay > 0:
            time.sleep(delay)

# Singleton instance
_throttler = None

def get_adaptive_throttler() -> AdaptiveThrottler:
    """Get singleton throttler instance."""
    global _throttler
    if _throttler is None:
        _throttler = AdaptiveThrottler()
    return _throttler
