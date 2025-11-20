"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by temporarily blocking requests to domains
that are consistently failing.

Pattern States:
- CLOSED: Normal operation, requests allowed
- OPEN: Too many failures, requests blocked
- HALF_OPEN: Testing if service recovered

Features:
- Per-domain failure tracking
- Redis-backed state persistence
- Configurable failure threshold and cooldown
- Automatic recovery testing
"""

import logging
from enum import Enum
from typing import Optional
import time
import redis
from config_manager import get_config

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Blocking requests
    HALF_OPEN = "half_open"    # Testing recovery


class DomainCircuitBreaker:
    """
    Per-domain circuit breaker to prevent cascading failures.
    
    If a domain fails consistently (e.g., 5 times in a row), the circuit
    "opens" and blocks all requests for a cooldown period. After cooldown,
    it enters HALF_OPEN state to test if the service recovered.
    """
    
    def __init__(self):
        """Initialize circuit breaker."""
        self.config = get_config()
        
        # Load configuration
        self.enabled = self.config.get('scraper.circuit_breaker.enabled', default=True)
        self.failure_threshold = self.config.get('scraper.circuit_breaker.failure_threshold', default=5)
        self.cooldown_period = self.config.get('scraper.circuit_breaker.cooldown_period', default=300)  # 5 minutes
        self.half_open_max_calls = self.config.get('scraper.circuit_breaker.half_open_max_calls', default=3)
        
        # Connect to Redis
        redis_url = self.config.get('databases.redis.url', default='redis://localhost:6379/0')
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        
        logger.info(f"Circuit Breaker initialized: {'Enabled' if self.enabled else 'Disabled'}")
        logger.info(f"  Failure Threshold: {self.failure_threshold}")
        logger.info(f"  Cooldown Period: {self.cooldown_period}s")
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    
    def _get_state_key(self, domain: str) -> str:
        """Get Redis key for circuit state."""
        return f"circuit:{domain}:state"
    
    def _get_failures_key(self, domain: str) -> str:
        """Get Redis key for failure count."""
        return f"circuit:{domain}:failures"
    
    def _get_last_failure_key(self, domain: str) -> str:
        """Get Redis key for last failure timestamp."""
        return f"circuit:{domain}:last_failure"
    
    def _get_half_open_calls_key(self, domain: str) -> str:
        """Get Redis key for half-open call count."""
        return f"circuit:{domain}:half_open_calls"
    
    def get_state(self, url: str) -> CircuitState:
        """
        Get current circuit state for domain.
        
        Args:
            url: Target URL
            
        Returns:
            Current CircuitState
        """
        if not self.enabled:
            return CircuitState.CLOSED
        
        domain = self._get_domain(url)
        state_key = self._get_state_key(domain)
        
        state_str = self.redis_client.get(state_key)
        
        if state_str == CircuitState.OPEN.value:
            # Check if cooldown period elapsed
            last_failure_key = self._get_last_failure_key(domain)
            last_failure_time = self.redis_client.get(last_failure_key)
            
            if last_failure_time:
                elapsed = time.time() - float(last_failure_time)
                
                if elapsed >= self.cooldown_period:
                    # Move to HALF_OPEN state
                    self._set_state(domain, CircuitState.HALF_OPEN)
                    logger.info(f"🔄 Circuit HALF_OPEN for {domain} (testing recovery)")
                    return CircuitState.HALF_OPEN
            
            return CircuitState.OPEN
        
        elif state_str == CircuitState.HALF_OPEN.value:
            return CircuitState.HALF_OPEN
        
        else:
            # Default to CLOSED
            return CircuitState.CLOSED
    
    def _set_state(self, domain: str, state: CircuitState):
        """Set circuit state in Redis."""
        state_key = self._get_state_key(domain)
        self.redis_client.set(state_key, state.value)
    
    def is_allowed(self, url: str) -> bool:
        """
        Check if request to URL is allowed.
        
        Args:
            url: Target URL
            
        Returns:
            True if request allowed, False if circuit is open
        """
        state = self.get_state(url)
        
        if state == CircuitState.OPEN:
            domain = self._get_domain(url)
            logger.warning(f"⛔ Circuit OPEN for {domain} - request blocked")
            return False
        
        elif state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            domain = self._get_domain(url)
            calls_key = self._get_half_open_calls_key(domain)
            
            # Increment call count
            calls = self.redis_client.incr(calls_key)
            
            if calls > self.half_open_max_calls:
                logger.warning(f"⚠️  Half-open limit reached for {domain}")
                return False
        
        return True
    
    def record_success(self, url: str):
        """
        Record successful request.
        
        Resets failure count and closes circuit if it was open.
        
        Args:
            url: Target URL that succeeded
        """
        if not self.enabled:
            return
        
        domain = self._get_domain(url)
        
        # Reset failure count
        failures_key = self._get_failures_key(domain)
        self.redis_client.delete(failures_key)
        
        # Get current state
        current_state = self.get_state(url)
        
        if current_state in [CircuitState.OPEN, CircuitState.HALF_OPEN]:
            # Close circuit on success
            self._set_state(domain, CircuitState.CLOSED)
            
            # Reset half-open call count
            calls_key = self._get_half_open_calls_key(domain)
            self.redis_client.delete(calls_key)
            
            logger.info(f"✅ Circuit CLOSED for {domain} (recovered)")
    
    def record_failure(self, url: str, error: Optional[str] = None):
        """
        Record failed request.
        
        Increments failure count. Opens circuit if threshold exceeded.
        
        Args:
            url: Target URL that failed
            error: Optional error message
        """
        if not self.enabled:
            return
        
        domain = self._get_domain(url)
        failures_key = self._get_failures_key(domain)
        
        # Increment failure count
        failures = self.redis_client.incr(failures_key)
        
        # Record timestamp
        last_failure_key = self._get_last_failure_key(domain)
        self.redis_client.set(last_failure_key, str(time.time()))
        
        logger.warning(f"❌ Failure recorded for {domain}: {failures}/{self.failure_threshold}")
        
        # Check if threshold exceeded
        if failures >= self.failure_threshold:
            # Open circuit
            self._set_state(domain, CircuitState.OPEN)
            
            # Set expiration for automatic recovery
            state_key = self._get_state_key(domain)
            self.redis_client.expire(state_key, self.cooldown_period)
            
            logger.error(
                f"🚨 Circuit OPEN for {domain} after {failures} failures "
                f"(cooldown: {self.cooldown_period}s)"
            )
    
    def get_stats(self, url: str) -> dict:
        """
        Get circuit breaker statistics for domain.
        
        Args:
            url: Target URL
            
        Returns:
            Dictionary with circuit stats
        """
        domain = self._get_domain(url)
        
        failures_key = self._get_failures_key(domain)
        failures = int(self.redis_client.get(failures_key) or 0)
        
        state = self.get_state(url)
        
        return {
            'domain': domain,
            'state': state.value,
            'failures': failures,
            'threshold': self.failure_threshold,
            'cooldown_period': self.cooldown_period,
            'is_allowed': self.is_allowed(url)
        }
    
    def reset(self, url: str):
        """
        Manually reset circuit for domain.
        
        Args:
            url: Target URL
        """
        domain = self._get_domain(url)
        
        # Delete all keys
        self.redis_client.delete(
            self._get_state_key(domain),
            self._get_failures_key(domain),
            self._get_last_failure_key(domain),
            self._get_half_open_calls_key(domain)
        )
        
        logger.info(f"🔄 Circuit manually reset for {domain}")


# Singleton instance
_circuit_breaker = None

def get_circuit_breaker() -> DomainCircuitBreaker:
    """Get singleton circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = DomainCircuitBreaker()
    return _circuit_breaker
