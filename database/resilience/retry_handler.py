"""
Advanced retry handler with exponential backoff and jitter for database operations.

This module provides intelligent retry logic for database operations with
sophisticated backoff strategies, exception filtering, and metrics tracking.
"""

import asyncio
import random
import time
from typing import Any, Callable, List, Optional, Type, Union, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import asyncpg


class BackoffStrategy(Enum):
    """Backoff strategy types."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Retry configuration settings."""
    max_attempts: int = 3
    base_delay: float = 1.0              # Base delay in seconds
    max_delay: float = 60.0              # Maximum delay in seconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    jitter_factor: float = 0.1           # Jitter factor (0.0 - 1.0)
    timeout_per_attempt: float = 30.0    # Timeout per attempt
    retry_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        asyncpg.ConnectionDoesNotExistError,
        asyncpg.ConnectionFailureError,
        asyncpg.InterfaceError,
        asyncpg.PostgresConnectionError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError
    ])
    stop_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        # asyncpg.SyntaxError,  # Не существует в asyncpg
        asyncpg.DataError,
        asyncpg.IntegrityConstraintViolationError,
        asyncpg.InvalidAuthorizationSpecificationError
    ])


@dataclass
class RetryAttempt:
    """Single retry attempt information."""
    attempt_number: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    exception: Optional[Exception] = None
    success: bool = False
    
    def complete(self, success: bool = True, exception: Exception = None):
        """Mark attempt as completed."""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.exception = exception


@dataclass
class RetryMetrics:
    """Retry operation metrics."""
    total_operations: int = 0
    total_attempts: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_retry_time_ms: float = 0
    average_attempts_per_operation: float = 0
    success_rate: float = 0
    most_common_exceptions: Dict[str, int] = field(default_factory=dict)
    
    def update(self, attempts: List[RetryAttempt], final_success: bool):
        """Update metrics with operation results."""
        self.total_operations += 1
        self.total_attempts += len(attempts)
        
        if final_success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        
        # Calculate total time for this operation
        if attempts:
            operation_time = sum(a.duration_ms for a in attempts if a.duration_ms)
            self.total_retry_time_ms += operation_time
        
        # Update averages
        self.average_attempts_per_operation = self.total_attempts / self.total_operations
        self.success_rate = (self.successful_operations / self.total_operations) * 100
        
        # Track exceptions
        for attempt in attempts:
            if attempt.exception:
                exc_name = type(attempt.exception).__name__
                self.most_common_exceptions[exc_name] = self.most_common_exceptions.get(exc_name, 0) + 1


class DatabaseRetryHandler:
    """
    Intelligent retry handler for database operations.
    
    Features:
    - Multiple backoff strategies
    - Exception-based retry logic
    - Comprehensive metrics
    - Circuit breaker integration
    - Deadlock detection and handling
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[RetryConfig] = None
    ):
        """
        Initialize retry handler.
        
        Args:
            name: Handler identifier
            config: Retry configuration
        """
        self.name = name
        self.config = config or RetryConfig()
        self.metrics = RetryMetrics()
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"Retry handler '{name}' initialized with {self.config.max_attempts} max attempts")
    
    def _validate_config(self):
        """Validate retry configuration."""
        if self.config.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        
        if self.config.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        
        if self.config.max_delay < self.config.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        
        if not 0 <= self.config.jitter_factor <= 1:
            raise ValueError("jitter_factor must be between 0 and 1")
    
    def _calculate_delay(self, attempt_number: int) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            attempt_number: Current attempt number (1-based)
        
        Returns:
            Delay in seconds
        """
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.base_delay
            
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay * attempt_number
            
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** (attempt_number - 1))
            
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            base_delay = self.config.base_delay * (2 ** (attempt_number - 1))
            jitter = base_delay * self.config.jitter_factor * random.random()
            delay = base_delay + jitter
        
        else:
            delay = self.config.base_delay
        
        # Cap at maximum delay
        return min(delay, self.config.max_delay)
    
    def _should_retry(self, exception: Exception, attempt_number: int) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            exception: Exception that occurred
            attempt_number: Current attempt number
        
        Returns:
            True if should retry
        """
        # Check if we've exceeded max attempts
        if attempt_number >= self.config.max_attempts:
            return False
        
        # Check if exception is in stop list (never retry)
        for stop_exc in self.config.stop_exceptions:
            if isinstance(exception, stop_exc):
                logger.debug(f"Not retrying due to stop exception: {type(exception).__name__}")
                return False
        
        # Check if exception is in retry list
        for retry_exc in self.config.retry_exceptions:
            if isinstance(exception, retry_exc):
                return True
        
        # Default: don't retry unknown exceptions
        logger.debug(f"Not retrying unknown exception: {type(exception).__name__}")
        return False
    
    def _is_deadlock_error(self, exception: Exception) -> bool:
        """Check if exception is a deadlock error."""
        if isinstance(exception, asyncpg.DeadlockDetectedError):
            return True
        
        # Check error message for deadlock indicators
        error_msg = str(exception).lower()
        deadlock_indicators = ['deadlock', 'lock wait timeout', 'concurrent update']
        
        return any(indicator in error_msg for indicator in deadlock_indicators)
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: Last exception if all retries failed
        """
        attempts: List[RetryAttempt] = []
        last_exception = None
        
        for attempt_number in range(1, self.config.max_attempts + 1):
            attempt = RetryAttempt(
                attempt_number=attempt_number,
                start_time=datetime.now()
            )
            attempts.append(attempt)
            
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_per_attempt
                )
                
                # Success!
                attempt.complete(success=True)
                self.metrics.update(attempts, final_success=True)
                
                if attempt_number > 1:
                    logger.info(
                        f"Retry handler '{self.name}' succeeded on attempt {attempt_number}"
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                attempt.complete(success=False, exception=e)
                
                # Log the failure
                logger.warning(
                    f"Retry handler '{self.name}' attempt {attempt_number} failed: "
                    f"{type(e).__name__}: {e}"
                )
                
                # Check if we should retry
                if not self._should_retry(e, attempt_number):
                    break
                
                # Special handling for deadlocks
                if self._is_deadlock_error(e):
                    # Add extra delay for deadlocks
                    base_delay = self._calculate_delay(attempt_number)
                    deadlock_delay = base_delay + random.uniform(0.1, 1.0)
                    
                    logger.info(
                        f"Deadlock detected, waiting {deadlock_delay:.2f}s before retry"
                    )
                    await asyncio.sleep(deadlock_delay)
                else:
                    # Normal retry delay
                    delay = self._calculate_delay(attempt_number)
                    
                    if attempt_number < self.config.max_attempts:
                        logger.info(
                            f"Retrying in {delay:.2f}s (attempt {attempt_number + 1}/"
                            f"{self.config.max_attempts})"
                        )
                        await asyncio.sleep(delay)
        
        # All retries failed
        self.metrics.update(attempts, final_success=False)
        
        logger.error(
            f"Retry handler '{self.name}' failed after {len(attempts)} attempts. "
            f"Last error: {type(last_exception).__name__}: {last_exception}"
        )
        
        raise last_exception
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry handler metrics."""
        return {
            "name": self.name,
            "config": {
                "max_attempts": self.config.max_attempts,
                "base_delay": self.config.base_delay,
                "max_delay": self.config.max_delay,
                "backoff_strategy": self.config.backoff_strategy.value,
                "timeout_per_attempt": self.config.timeout_per_attempt
            },
            "metrics": {
                "total_operations": self.metrics.total_operations,
                "total_attempts": self.metrics.total_attempts,
                "successful_operations": self.metrics.successful_operations,
                "failed_operations": self.metrics.failed_operations,
                "success_rate": self.metrics.success_rate,
                "average_attempts_per_operation": self.metrics.average_attempts_per_operation,
                "total_retry_time_ms": self.metrics.total_retry_time_ms,
                "most_common_exceptions": self.metrics.most_common_exceptions
            }
        }
    
    def reset_metrics(self):
        """Reset metrics to initial state."""
        self.metrics = RetryMetrics()
        logger.info(f"Reset metrics for retry handler '{self.name}'")


class DatabaseRetryManager:
    """
    Manager for multiple retry handlers.
    
    Manages retry handlers for different database operations:
    - Connection establishment
    - Query execution
    - Transaction operations
    - Bulk operations
    """
    
    def __init__(self):
        """Initialize retry manager."""
        self._handlers: Dict[str, DatabaseRetryHandler] = {}
        self._default_configs: Dict[str, RetryConfig] = self._create_default_configs()
    
    def _create_default_configs(self) -> Dict[str, RetryConfig]:
        """Create default retry configurations for common operations."""
        return {
            "connection": RetryConfig(
                max_attempts=5,
                base_delay=0.5,
                max_delay=10.0,
                backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER
            ),
            "query": RetryConfig(
                max_attempts=3,
                base_delay=0.1,
                max_delay=5.0,
                backoff_strategy=BackoffStrategy.EXPONENTIAL
            ),
            "transaction": RetryConfig(
                max_attempts=5,
                base_delay=0.2,
                max_delay=8.0,
                backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER
            ),
            "bulk_operation": RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                backoff_strategy=BackoffStrategy.LINEAR
            )
        }
    
    def create_handler(
        self,
        name: str,
        config: Optional[RetryConfig] = None
    ) -> DatabaseRetryHandler:
        """
        Create a new retry handler.
        
        Args:
            name: Handler name
            config: Configuration (uses default if None)
        
        Returns:
            Created retry handler
        """
        if name in self._handlers:
            raise ValueError(f"Retry handler '{name}' already exists")
        
        # Use default config for known operation types
        if config is None and name in self._default_configs:
            config = self._default_configs[name]
        
        handler = DatabaseRetryHandler(name, config)
        self._handlers[name] = handler
        
        logger.info(f"Created retry handler: {name}")
        return handler
    
    def get_handler(self, name: str) -> Optional[DatabaseRetryHandler]:
        """Get retry handler by name."""
        return self._handlers.get(name)
    
    def get_or_create_handler(
        self,
        name: str,
        config: Optional[RetryConfig] = None
    ) -> DatabaseRetryHandler:
        """Get existing or create new retry handler."""
        if name in self._handlers:
            return self._handlers[name]
        
        return self.create_handler(name, config)
    
    def list_handlers(self) -> List[str]:
        """List all retry handler names."""
        return list(self._handlers.keys())
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all retry handlers."""
        return {
            name: handler.get_metrics()
            for name, handler in self._handlers.items()
        }
    
    def reset_all_metrics(self):
        """Reset metrics for all handlers."""
        for handler in self._handlers.values():
            handler.reset_metrics()
        
        logger.info(f"Reset metrics for {len(self._handlers)} retry handlers")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all retry handlers."""
        all_metrics = self.get_all_metrics()
        
        total_operations = sum(m["metrics"]["total_operations"] for m in all_metrics.values())
        total_failures = sum(m["metrics"]["failed_operations"] for m in all_metrics.values())
        
        # Find handler with highest failure rate
        worst_handler = None
        worst_failure_rate = 0
        for name, metrics in all_metrics.items():
            failure_rate = 100 - metrics["metrics"]["success_rate"]
            if failure_rate > worst_failure_rate:
                worst_failure_rate = failure_rate
                worst_handler = name
        
        return {
            "total_handlers": len(self._handlers),
            "total_operations": total_operations,
            "total_failures": total_failures,
            "overall_failure_rate": (total_failures / total_operations * 100) if total_operations > 0 else 0,
            "worst_performing_handler": {
                "name": worst_handler,
                "failure_rate": worst_failure_rate
            } if worst_handler else None
        }


# Global retry manager instance
retry_manager = DatabaseRetryManager()


# Convenience decorator
def with_retry(
    name: str,
    config: Optional[RetryConfig] = None
):
    """
    Decorator to add retry logic to functions.
    
    Args:
        name: Retry handler name
        config: Retry configuration
    
    Example:
        @with_retry("database_query", config=RetryConfig(max_attempts=5))
        async def execute_query(query):
            # Database operation
            pass
    """
    def decorator(func):
        handler = retry_manager.get_or_create_handler(name, config)
        
        async def wrapper(*args, **kwargs):
            return await handler.execute(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Common retry configurations
CRITICAL_OPERATION_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER
)

FAST_OPERATION_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.1,
    max_delay=2.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL
)

BULK_OPERATION_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=60.0,
    backoff_strategy=BackoffStrategy.LINEAR
)