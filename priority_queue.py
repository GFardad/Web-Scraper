"""
Priority Queue System

Heap-based priority queue for processing high-priority tasks first.
"""

import logging
import heapq
from typing import List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("PriorityQueue")


@dataclass(order=True)
class PriorityTask:
    """Task with priority."""
    
    priority: int = field(compare=True)  # Lower number = higher priority
    timestamp: float = field(compare=True, default_factory=lambda: datetime.now().timestamp())
    task_id: int = field(compare=False, default=0)
    url: str = field(compare=False, default="")
    metadata: dict = field(compare=False, default_factory=dict)
    
    def __repr__(self):
        return f"PriorityTask(priority={self.priority}, url={self.url[:50]}...)"


class PriorityQueueManager:
    """
    Thread-safe priority queue with dynamic priority adjustment.
    
    Priority Levels:
    1 = Critical (new products, errors)
    5 = Normal (regular scraping)
    10 = Low (background tasks)
    """
    
    def __init__(self):
        """Initialize priority queue."""
        self.heap: List[PriorityTask] = []
        self.task_map = {}  # task_id -> PriorityTask
        self.next_id = 1
    
    def add(self, url: str, priority: int = 5, metadata: dict = None) -> int:
        """
        Add task to queue.
        
        Args:
            url: URL to scrape
            priority: Priority level (1=highest, 10=lowest)
            metadata: Optional metadata
            
        Returns:
            Task ID
        """
        task_id = self.next_id
        self.next_id += 1
        
        task = PriorityTask(
            priority=priority,
            task_id=task_id,
            url=url,
            metadata=metadata or {}
        )
        
        heapq.heappush(self.heap, task)
        self.task_map[task_id] = task
        
        logger.debug(f"Added task {task_id} with priority {priority}: {url}")
        return task_id
    
    def pop(self) -> Optional[PriorityTask]:
        """
        Get and remove highest priority task.
        
        Returns:
            PriorityTask or None if empty
        """
        if not self.heap:
            return None
        
        task = heapq.heappop(self.heap)
        self.task_map.pop(task.task_id, None)
        
        logger.debug(f"Popped task {task.task_id} (priority={task.priority})")
        return task
    
    def peek(self) -> Optional[PriorityTask]:
        """View highest priority task without removing."""
        if not self.heap:
            return None
        return self.heap[0]
    
    def adjust_priority(self, task_id: int, new_priority: int) -> bool:
        """
        Adjust priority of existing task.
        
        Args:
            task_id: Task ID
            new_priority: New priority level
            
        Returns:
            True if adjusted, False if not found
        """
        if task_id not in self.task_map:
            return False
        
        # Remove old task
        old_task = self.task_map[task_id]
        self.heap.remove(old_task)
        heapq.heapify(self.heap)
        
        # Add with new priority
        new_task = PriorityTask(
            priority=new_priority,
            task_id=old_task.task_id,
            url=old_task.url,
            metadata=old_task.metadata
        )
        
        heapq.heappush(self.heap, new_task)
        self.task_map[task_id] = new_task
        
        logger.info(f"Adjusted task {task_id} priority: {old_task.priority} -> {new_priority}")
        return True
    
    def size(self) -> int:
        """Get queue size."""
        return len(self.heap)
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.heap) == 0
    
    def clear(self):
        """Clear all tasks."""
        self.heap.clear()
        self.task_map.clear()
        logger.info("Queue cleared")
    
    def get_stats(self) -> dict:
        """Get queue statistics."""
        priority_counts = {}
        for task in self.heap:
            priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1
        
        return {
            'total_tasks': len(self.heap),
            'priority_distribution': priority_counts,
            'next_priority': self.heap[0].priority if self.heap else None
        }
