"""
Response Time Analytics

Tracks and analyzes server response times for performance optimization.
"""

import logging
import time
from typing import Dict, List
from collections import defaultdict, deque
from statistics import mean, median
from datetime import datetime

logger = logging.getLogger("ResponseAnalytics")


class ResponseTimeAnalytics:
    """
    Advanced response time tracking and analysis.
    
    Provides insights for:
    - Performance bottlenecks
    - Server health trends
    - Optimal request timing
    """
    
    def __init__(self, history_size: int = 1000):
        """
        Initialize analytics.
        
        Args:
            history_size: Number of responses to track per domain
        """
        self.history_size = history_size
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.status_codes: Dict[str, List[int]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
    
    def record(self, domain: str, response_time: float, status_code: int, success: bool = True):
        """
        Record response metrics.
        
        Args:
            domain: Target domain
            response_time: Response time in seconds
            status_code: HTTP status code
            success: Whether request succeeded
        """
        self.response_times[domain].append({
            'time': response_time,
            'timestamp': datetime.now(),
            'status': status_code
        })
        
        self.status_codes[domain].append(status_code)
        
        if not success:
            self.error_counts[domain] += 1
        
        logger.debug(f"{domain}: {response_time:.2f}s (status={status_code})")
    
    def get_stats(self, domain: str) -> Dict:
        """Get comprehensive statistics for domain."""
        if domain not in self.response_times or not self.response_times[domain]:
            return {}
        
        times = [r['time'] for r in self.response_times[domain]]
        
        return {
            'count': len(times),
            'avg_response_time': mean(times),
            'median_response_time': median(times),
            'min_response_time': min(times),
            'max_response_time': max(times),
            'error_count': self.error_counts.get(domain, 0),
            'p95': self._percentile(times, 95),
            'p99': self._percentile(times, 99)
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_slowest_domains(self, limit: int = 10) -> List[tuple]:
        """Get slowest domains by average response time."""
        domain_avgs = []
        
        for domain in self.response_times.keys():
            stats = self.get_stats(domain)
            if stats:
                domain_avgs.append((domain, stats['avg_response_time']))
        
        domain_avgs.sort(key=lambda x: x[1], reverse=True)
        return domain_avgs[:limit]
    
    def is_healthy(self, domain: str, threshold_seconds: float = 5.0) -> bool:
        """Check if domain is responding healthily."""
        stats = self.get_stats(domain)
        if not stats:
            return True
        
        return stats['avg_response_time'] < threshold_seconds
