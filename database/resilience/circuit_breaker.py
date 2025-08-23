"""
Circuit Breaker pattern implementation for database resilience.

This module provides circuit breaker functionality to protect against
cascading failures and provide graceful degradation for trading systems.
"""

import asyncio
import time
from typing import Any, Callable, Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import json


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5           # Failures before opening
    recovery_timeout: int = 60           # Seconds to wait before half-open
    success_threshold: int = 3           # Successes to close from half-open
    timeout: float = 30.0                # Request timeout in seconds
    expected_exception: type = Exception # Exception type to count as failure


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    rejected_requests: int = 0
    state_changes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    average_response_time: float = 0.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class DatabaseCircuitBreaker:
    """
    Circuit breaker for database operations.
    
    Protects against:
    - Database connection failures
    - Slow query timeouts
    - Resource exhaustion
    - Cascading failures
    
    Provides:
    - Automatic failure detection
    - Graceful degradation
    - Recovery testing
    - Detailed metrics
    """
    
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig = None,
        fallback_handler: Optional[Callable] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker identifier
            config: Configuration settings
            fallback_handler: Optional fallback function for open circuit
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback_handler = fallback_handler
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.next_attempt_time: Optional[datetime] = None
        
        # Metrics
        self.metrics = CircuitMetrics()
        
        # Response time tracking
        self._response_times: List[float] = []
        self._max_response_times = 100  # Keep last 100 response times
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._check_circuit_state()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is None:
            await self._record_success()
        else:
            await self._record_failure(exc_val)
        return False  # Don't suppress exceptions
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: When circuit is open
            TimeoutError: When function times out
            Exception: Original function exceptions
        """
        async with self._lock:
            await self._check_circuit_state()
            
            if self.state == CircuitState.OPEN:
                self.metrics.rejected_requests += 1
                
                if self.fallback_handler:
                    logger.info(f"Circuit '{self.name}' is open, using fallback")
                    return await self.fallback_handler(*args, **kwargs)
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is open. "
                        f"Next attempt in {self._time_until_next_attempt()} seconds"
                    )
        
        # Execute function with timeout
        start_time = time.time()
        
        try:
            self.metrics.total_requests += 1
            
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            # Record success
            execution_time = time.time() - start_time
            await self._record_success(execution_time)
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self.metrics.timeout_requests += 1
            await self._record_failure(
                TimeoutError(f"Operation timed out after {execution_time:.2f}s")
            )
            raise
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Only count expected exceptions as failures
            if isinstance(e, self.config.expected_exception):
                await self._record_failure(e)
            else:
                # Unexpected exceptions don't affect circuit state
                logger.warning(f"Unexpected exception in circuit '{self.name}': {e}")
            
            raise
    
    async def _check_circuit_state(self):
        """Check and update circuit state based on current conditions."""
        current_time = datetime.now()
        
        if self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if (self.next_attempt_time and 
                current_time >= self.next_attempt_time):
                await self._transition_to_half_open()
                
        elif self.state == CircuitState.HALF_OPEN:
            # In half-open state, we allow limited requests to test recovery
            pass
    
    async def _record_success(self, execution_time: float = 0):
        """Record successful operation."""
        async with self._lock:
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = datetime.now()
            
            # Update response time tracking
            if execution_time > 0:
                self._response_times.append(execution_time)
                if len(self._response_times) > self._max_response_times:
                    self._response_times.pop(0)
                
                # Update average response time
                self.metrics.average_response_time = sum(self._response_times) / len(self._response_times)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                
                # If we have enough successes, close the circuit
                if self.success_count >= self.config.success_threshold:
                    await self._transition_to_closed()
            
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    async def _record_failure(self, exception: Exception):
        """Record failed operation."""
        async with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = datetime.now()
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            logger.warning(
                f"Circuit '{self.name}' recorded failure #{self.failure_count}: {exception}"
            )
            
            if self.state == CircuitState.CLOSED:
                # Check if we should open the circuit
                if self.failure_count >= self.config.failure_threshold:
                    await self._transition_to_open()
                    
            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens the circuit
                await self._transition_to_open()
    
    async def _transition_to_open(self):
        """Transition circuit to open state."""
        self.state = CircuitState.OPEN
        self.metrics.state_changes += 1
        self.next_attempt_time = datetime.now() + timedelta(seconds=self.config.recovery_timeout)
        
        logger.error(
            f"Circuit breaker '{self.name}' opened due to {self.failure_count} failures. "
            f"Next attempt at {self.next_attempt_time}"
        )
    
    async def _transition_to_half_open(self):
        """Transition circuit to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.metrics.state_changes += 1
        self.success_count = 0
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to half-open for testing")
    
    async def _transition_to_closed(self):
        """Transition circuit to closed state."""
        self.state = CircuitState.CLOSED
        self.metrics.state_changes += 1
        self.failure_count = 0
        self.success_count = 0
        self.next_attempt_time = None
        
        logger.info(f"Circuit breaker '{self.name}' closed - service recovered")
    
    def _time_until_next_attempt(self) -> int:
        """Calculate seconds until next attempt is allowed."""
        if not self.next_attempt_time:
            return 0
        
        remaining = (self.next_attempt_time - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    async def force_open(self):
        """Manually force circuit to open state."""
        async with self._lock:
            await self._transition_to_open()
            logger.warning(f"Circuit breaker '{self.name}' manually forced open")
    
    async def force_close(self):
        """Manually force circuit to closed state."""
        async with self._lock:
            await self._transition_to_closed()
            logger.warning(f"Circuit breaker '{self.name}' manually forced closed")
    
    async def reset(self):
        """Reset circuit breaker to initial state."""
        async with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.next_attempt_time = None
            self._response_times.clear()
            
            # Reset metrics
            self.metrics = CircuitMetrics()
            
            logger.info(f"Circuit breaker '{self.name}' reset to initial state")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "next_attempt_time": self.next_attempt_time.isoformat() if self.next_attempt_time else None,
            "time_until_next_attempt": self._time_until_next_attempt(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            },
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "timeout_requests": self.metrics.timeout_requests,
                "rejected_requests": self.metrics.rejected_requests,
                "failure_rate": self.metrics.failure_rate,
                "success_rate": self.metrics.success_rate,
                "state_changes": self.metrics.state_changes,
                "average_response_time": self.metrics.average_response_time,
                "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "last_success_time": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None
            }
        }


class DatabaseCircuitBreakerManager:
    """
    Manager for multiple database circuit breakers.
    
    Manages circuit breakers for different database operations:
    - Query execution
    - Connection acquisition
    - Transaction operations
    - Bulk operations
    """
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: Dict[str, DatabaseCircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
    
    def create_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback_handler: Optional[Callable] = None
    ) -> DatabaseCircuitBreaker:
        """
        Create a new circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Configuration (uses default if None)
            fallback_handler: Optional fallback function
        
        Returns:
            Created circuit breaker
        """
        if name in self._breakers:
            raise ValueError(f"Circuit breaker '{name}' already exists")
        
        breaker = DatabaseCircuitBreaker(
            name=name,
            config=config or self._default_config,
            fallback_handler=fallback_handler
        )
        
        self._breakers[name] = breaker
        logger.info(f"Created circuit breaker: {name}")
        
        return breaker
    
    def get_breaker(self, name: str) -> Optional[DatabaseCircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_or_create_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback_handler: Optional[Callable] = None
    ) -> DatabaseCircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name in self._breakers:
            return self._breakers[name]
        
        return self.create_breaker(name, config, fallback_handler)
    
    def list_breakers(self) -> List[str]:
        """List all circuit breaker names."""
        return list(self._breakers.keys())
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()
        
        logger.info(f"Reset {len(self._breakers)} circuit breakers")
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of all circuit breakers."""
        all_status = await self.get_all_status()
        
        total_breakers = len(all_status)
        open_breakers = len([s for s in all_status.values() if s["state"] == "open"])
        half_open_breakers = len([s for s in all_status.values() if s["state"] == "half_open"])
        
        total_requests = sum(s["metrics"]["total_requests"] for s in all_status.values())
        total_failures = sum(s["metrics"]["failed_requests"] for s in all_status.values())
        
        overall_failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        
        health_status = "healthy"
        if open_breakers > 0:
            health_status = "critical"
        elif half_open_breakers > 0 or overall_failure_rate > 10:
            health_status = "warning"
        
        return {
            "health_status": health_status,
            "total_breakers": total_breakers,
            "open_breakers": open_breakers,
            "half_open_breakers": half_open_breakers,
            "closed_breakers": total_breakers - open_breakers - half_open_breakers,
            "overall_failure_rate": overall_failure_rate,
            "total_requests": total_requests,
            "total_failures": total_failures
        }


# Global circuit breaker manager instance
circuit_breaker_manager = DatabaseCircuitBreakerManager()


# Convenience decorators
def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback_handler: Optional[Callable] = None
):
    """
    Decorator to add circuit breaker protection to functions.
    
    Args:
        name: Circuit breaker name
        config: Configuration
        fallback_handler: Fallback function
    
    Example:
        @circuit_breaker("database_query", config=CircuitBreakerConfig(failure_threshold=3))
        async def execute_query(query):
            # Database operation
            pass
    """
    def decorator(func):
        breaker = circuit_breaker_manager.get_or_create_breaker(name, config, fallback_handler)
        
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Example fallback handlers
async def read_only_fallback(*args, **kwargs):
    """Fallback for read operations - return empty result."""
    logger.warning("Using read-only fallback due to circuit breaker")
    return []


async def cache_fallback(cache_key: str):
    """Fallback that returns cached data."""
    logger.warning(f"Using cache fallback for key: {cache_key}")
    # Implementation would integrate with caching system
    return None