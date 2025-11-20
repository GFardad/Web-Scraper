"""Unit tests for concurrent engine."""
import pytest
import asyncio
from concurrent_engine import DomainRateLimiter, CircuitBreaker, ConcurrentProcessor


class TestDomainRateLimiter:
    """Test domain-based rate limiting."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiting enforces delays."""
        limiter = DomainRateLimiter(delay_seconds=0.5)
        
        url = "https://example.com/page1"
        
        start = asyncio.get_event_loop().time()
        await limiter.acquire(url)
        await limiter.acquire(url)
        elapsed = asyncio.get_event_loop().time() - start
        
        assert elapsed >= 0.5, "Should enforce 0.5s delay"
    
    @pytest.mark.asyncio
    async def test_different_domains(self):
        """Test that different domains don't block each other."""
        limiter = DomainRateLimiter(delay_seconds=1.0)
        
        url1 = "https://example1.com/page"
        url2 = "https://example2.com/page"
        
        start = asyncio.get_event_loop().time()
        await limiter.acquire(url1)
        await limiter.acquire(url2)
        elapsed = asyncio.get_event_loop().time() - start
        
        assert elapsed < 0.5, "Different domains should be parallel"


class TestCircuitBreaker:
    """Test circuit breaker pattern."""
    
    def test_opens_after_failures(self):
        """Test circuit opens after threshold."""
        breaker = CircuitBreaker(failure_threshold=3)
        url = "https://example.com/page"
        
        assert breaker.is_open(url) is False
        
        # Record failures
        breaker.record_failure(url)
        breaker.record_failure(url)
        assert breaker.is_open(url) is False
        
        breaker.record_failure(url)
        assert breaker.is_open(url) is True
    
    def test_resets_on_success(self):
        """Test circuit resets on success."""
        breaker = CircuitBreaker(failure_threshold=3)
        url = "https://example.com/page"
        
        breaker.record_failure(url)
        breaker.record_failure(url)
        breaker.record_success(url)
        
        assert breaker.failures[breaker._get_domain(url)] == 0


@pytest.mark.asyncio
class TestConcurrentProcessor:
    """Test concurrent processing."""
    
    async def test_concurrent_execution(self):
        """Test tasks run concurrently."""
        processor = ConcurrentProcessor(worker_count=3, rate_limit_delay=0.1)
        
        async def dummy_worker(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        tasks = [(i, f"url{i}", i) for i in range(5)]
        
        start = asyncio.get_event_loop().time()
        results = await processor.process_batch(tasks, dummy_worker)
        elapsed = asyncio.get_event_loop().time() - start
        
        assert len(results) == 5
        # With 3 workers and 5 tasks, should take ~0.2s not 0.5s
        assert elapsed < 0.4, "Should run concurrently"
