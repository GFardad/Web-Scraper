"""
Memory Leak Detection & Profiling

Monitors memory usage and detects leaks in long-running scraping jobs.
"""

import logging
import psutil
import tracemalloc
from typing import Dict, List, Tuple
from collections import deque
from datetime import datetime

logger = logging.getLogger("MemoryProfiler")


class MemoryProfiler:
    """Real-time memory profiling and leak detection."""
    
    def __init__(self, leak_threshold_mb: int = 100, history_size: int = 100):
        """
        Initialize memory profiler.
        
        Args:
            leak_threshold_mb: MB growth to consider as leak
            history_size: Number of snapshots to keep
        """
        self.leak_threshold_mb = leak_threshold_mb
        self.history: deque = deque(maxlen=history_size)
        self.initial_memory = None
        self.tracemalloc_started = False
    
    def start(self):
        """Start memory tracking."""
        try:
            tracemalloc.start()
            self.tracemalloc_started = True
            self.initial_memory = self.get_current_memory()
            logger.info(f"Memory profiler started (initial: {self.initial_memory:.1f} MB)")
        except Exception as e:
            logger.warning(f"tracemalloc start failed: {e}")
    
    def stop(self):
        """Stop memory tracking."""
        if self.tracemalloc_started:
            tracemalloc.stop()
            self.tracemalloc_started = False
            logger.info("Memory profiler stopped")
    
    def get_current_memory(self) -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Memory usage in MB
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            return 0.0
    
    def take_snapshot(self) -> Dict[str, any]:
        """
        Record memory snapshot.
        
        Returns:
            Snapshot data
        """
        snapshot = {
            'timestamp': datetime.now(),
            'memory_mb': self.get_current_memory(),
            'growth_mb': 0.0
        }
        
        if self.initial_memory:
            snapshot['growth_mb'] = snapshot['memory_mb'] - self.initial_memory
        
        self.history.append(snapshot)
        return snapshot
    
    def detect_leak(self) -> Tuple[bool, float]:
        """
        Detect memory leak based on growth trend.
        
        Returns:
            Tuple of (is_leaking, growth_rate_mb_per_snapshot)
        """
        if len(self.history) < 10:
            return False, 0.0
        
        # Calculate growth rate (linear regression would be better)
        recent = list(self.history)[-10:]
        first_mem = recent[0]['memory_mb']
        last_mem = recent[-1]['memory_mb']
        
        growth = last_mem - first_mem
        growth_rate = growth / len(recent)
        
        # Check if growth exceeds threshold
        total_growth = last_mem - self.initial_memory if self.initial_memory else 0
        is_leaking = total_growth > self.leak_threshold_mb
        
        if is_leaking:
            logger.warning(f"Memory leak detected! Growth: {total_growth:.1f} MB, Rate: {growth_rate:.2f} MB/snapshot")
        
        return is_leaking, growth_rate
    
    def get_top_allocations(self, limit: int = 10) -> List[str]:
        """
        Get top memory allocations (requires tracemalloc).
        
        Args:
            limit: Number of top allocations to return
            
        Returns:
            List of allocation descriptions
        """
        if not self.tracemalloc_started:
            return ["tracemalloc not started"]
        
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            allocations = []
            for stat in top_stats[:limit]:
                allocations.append(f"{stat.filename}:{stat.lineno}: {stat.size / 1024:.1f} KB")
            
            return allocations
        except Exception as e:
            logger.error(f"Failed to get allocations: {e}")
            return []
    
    def get_report(self) -> Dict[str, any]:
        """
        Get comprehensive memory report.
        
        Returns:
            Memory report dict
        """
        current_mem = self.get_current_memory()
        is_leaking, growth_rate = self.detect_leak()
        
        report = {
            'current_memory_mb': current_mem,
            'initial_memory_mb': self.initial_memory,
            'total_growth_mb': current_mem - self.initial_memory if self.initial_memory else 0,
            'is_leaking': is_leaking,
            'growth_rate_mb_per_snapshot': growth_rate,
            'snapshots_recorded': len(self.history),
            'top_allocations': self.get_top_allocations()
        }
        
        return report
    
    def should_restart(self) -> bool:
        """
        Determine if process should restart due to memory issues.
        
        Returns:
            True if restart recommended
        """
        is_leaking, _ = self.detect_leak()
        current_mem = self.get_current_memory()
        
        # Restart if leaking or absolute memory too high (>2GB)
        if is_leaking and current_mem > 2048:
            logger.critical(f"Restart recommended: Memory at {current_mem:.1f} MB with leak detected")
            return True
        
        return False
        

# Global instance
memory_profiler = MemoryProfiler()
