"""Universal Thread Pool Coordinator for PTSD Agent.

Manages ALL operations through a single thread pool:
- Discovery
- Test execution
- AI analysis
- Auto-fixes
- Cache operations
- Research queries

Features:
- Real-time chart updates
- Surgical configuration (per phase/component/pattern)
- Operation prioritization
- Thread utilization tracking
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from queue import PriorityQueue


class OperationType(Enum):
    """Types of operations that can be  executed."""
    DISCOVERY = "discovery"
    EXECUTION = "execution"
    AI_ANALYSIS = "ai"
    AUTO_FIX = "fix"
    CACHE = "cache"
    RESEARCH = "research"


class OperationPriority(Enum):
    """Priority levels for operations."""
    CRITICAL = 0  # Auto-fixes
    HIGH = 1  # Test execution
    NORMAL = 2  # Discovery
    LOW = 3  # Cache, research


@dataclass
class Operation:
    """An operation to be executed in the thread pool."""
    operation_type: OperationType
    priority: OperationPriority
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    component_name: Optional[str] = None
    phase_id: Optional[int] = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
    
    def __lt__(self, other):
        """Compare by priority for queue ordering."""
        return self.priority.value < other.priority.value


class ThreadPoolCoordinator:
    """Universal thread pool coordinator for all PTSD operations."""
    
    def __init__(
        self, 
        max_threads: int = 12,
        thread_chart=None,
        config: Optional[Dict] = None
    ):
        """Initialize thread pool coordinator.
        
        Args:
            max_threads: Maximum number of threads
            thread_chart: ThreadChartRenderer instance for visualization
            config: Configuration dict with surgical thread settings
        """
        self.max_threads = max_threads
        self.thread_chart = thread_chart
        self.config = config or {}
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=max_threads)
        
        # Active operations tracking
        self.active_operations: Dict[str, Operation] = {}
        self.active_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_operations': 0,
            'completed_operations': 0,
            'failed_operations': 0,
            'by_type': {op_type: 0 for op_type in OperationType}
        }
        
        # Surgical configuration cache
        self._thread_limits = self._build_thread_limits(config)
    
    def _build_thread_limits(self, config: Dict) -> Dict:
        """Build thread limits from surgical configuration.
        
        Args:
            config: Configuration dict
        
        Returns:
            Dict mapping (phase, component, pattern) to thread limits
        """
        limits = {}
        
        thread_config = config.get('execution', {}).get('thread_config', {})
        
        # Phase-specific limits
        for phase_id, limit in thread_config.get('phase', {}).items():
            limits[('phase', phase_id)] = limit
        
        # Component-specific limits
        for component, limit in thread_config.get('component', {}).items():
            limits[('component', component)] = limit
        
        # Pattern-based limits
        for pattern, limit in thread_config.get('pattern', {}).items():
            limits[('pattern', pattern)] = limit
        
        return limits
    
    def get_thread_limit(
        self, 
        phase_id: Optional[int] = None,
        component_name: Optional[str] = None
    ) -> int:
        """Get thread limit for specific context.
        
        Args:
            phase_id: Phase ID if applicable
            component_name: Component name if applicable
        
        Returns:
            Thread limit for this context
        """
        # Check component-specific
        if component_name:
            limit = self._thread_limits.get(('component', component_name))
            if limit:
                return limit
        
        # Check phase-specific
        if phase_id:
            limit = self._thread_limits.get(('phase', phase_id))
            if limit:
                return limit
        
        # Default
        return self.max_threads
    
    def submit(
        self,
        operation_type: OperationType,
        func: Callable,
        *args,
        priority: OperationPriority = OperationPriority.NORMAL,
        component_name: Optional[str] = None,
        phase_id: Optional[int] = None,
        **kwargs
    ) -> Future:
        """Submit an operation to the thread pool.
        
        Args:
            operation_type: Type of operation
            func: Function to execute
            *args: Positional arguments
            priority: Operation priority
            component_name: Component name (for surgical config)
            phase_id: Phase ID (for surgical config)
            **kwargs: Keyword arguments
        
        Returns:
            Future object
        """
        operation = Operation(
            operation_type=operation_type,
            priority=priority,
            func=func,
            args=args,
            kwargs=kwargs,
            component_name=component_name,
            phase_id=phase_id
        )
        
        # Wrap function to track thread activity
        def wrapped_func(*args, **kwargs):
            op_id = f"{operation_type.value}_{time.time()}"
            
            # Track active operation
            with self.active_lock:
                self.active_operations[op_id] = operation
                self.stats['total_operations'] += 1
                self.stats['by_type'][operation_type] += 1
                
                # Update thread chart with operation type counts
                if self.thread_chart:
                    # Count active threads per operation type
                    ops_by_type = {}
                    for op in self.active_operations.values():
                        op_type = op.operation_type
                        ops_by_type[op_type] = ops_by_type.get(op_type, 0) + 1
                    
                    # Feed correct format to chart
                    self.thread_chart.add_data_point(ops_by_type)
            
            try:
                result = func(*args, **kwargs)
                with self.active_lock:
                    self.stats['completed_operations'] += 1
                return result
            except Exception as e:
                with self.active_lock:
                    self.stats['failed_operations'] += 1
                raise e
            finally:
                # Remove from active
                with self.active_lock:
                    self.active_operations.pop(op_id, None)
                    
                    # Update chart
                    if self.thread_chart:
                        # Count active threads per operation type
                        ops_by_type = {}
                        for op in self.active_operations.values():
                            op_type = op.operation_type
                            ops_by_type[op_type] = ops_by_type.get(op_type, 0) + 1
                        
                        # Feed correct format to chart
                        self.thread_chart.add_data_point(ops_by_type)
        
        # Submit to executor
        future = self.executor.submit(wrapped_func, *args, **kwargs)
        return future
    
    def get_active_thread_count(self) -> int:
        """Get number of currently active threads.
        
        Returns:
            Count of active operations
        """
        with self.active_lock:
            return len(self.active_operations)
    
    def get_stats(self) -> Dict:
        """Get execution statistics.
        
        Returns:
            Statistics dictionary
        """
        with self.active_lock:
            return self.stats.copy()
    
    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool.
        
        Args:
            wait: Whether to wait for completion
        """
        self.executor.shutdown(wait=wait)
