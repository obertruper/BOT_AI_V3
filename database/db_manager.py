"""
Centralized Database Manager - the main facade for all database operations.

This module provides a unified interface for database access, combining
connection management, transactions, repositories, and monitoring.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncpg
from loguru import logger
from contextlib import asynccontextmanager

from database.connections.postgres import AsyncPGPool
from database.connections.transaction_manager import TransactionManager, UnitOfWork
from database.repositories.ml_prediction_repository import MLPredictionRepository
from database.repositories.position_repository import PositionRepository
from database.optimization.query_optimizer import QueryOptimizer
from database.monitoring.monitoring_service import DatabaseMonitoringService
from database.resilience.circuit_breaker import DatabaseCircuitBreaker, circuit_breaker_manager
from database.resilience.retry_handler import DatabaseRetryHandler, retry_manager


class DBManager:
    """
    Centralized Database Manager - Singleton pattern implementation.
    
    This class serves as the main entry point for all database operations,
    providing:
    - Connection pool management
    - Transaction coordination
    - Repository access
    - Monitoring and metrics
    - Health checks
    
    Usage:
        db = await DBManager.initialize()
        
        # Simple operation
        position = await db.positions.get_open_positions()
        
        # Transaction operation
        async with db.transaction() as conn:
            order_id = await db.orders.create(order_data, conn)
            position_id = await db.positions.open_position(position_data, order_id, conn)
    """
    
    _instance: Optional['DBManager'] = None
    _initialized: bool = False
    _lock = asyncio.Lock()
    
    def __init__(self):
        """Private constructor - use initialize() instead."""
        if DBManager._instance is not None:
            raise RuntimeError("Use DBManager.initialize() to get instance")
        
        self.pool: Optional[asyncpg.Pool] = None
        self.transaction_manager: Optional[TransactionManager] = None
        
        # Core components
        self.query_optimizer: Optional[QueryOptimizer] = None
        self.monitoring_service: Optional[DatabaseMonitoringService] = None
        
        # Repositories
        self.ml_predictions: Optional[MLPredictionRepository] = None
        self.positions: Optional[PositionRepository] = None
        self.orders: Optional = None
        self.trades: Optional = None  
        self.signals: Optional = None
        
        # Metrics
        self._query_count = 0
        self._error_count = 0
        self._start_time = datetime.now()
    
    @classmethod
    async def initialize(cls) -> 'DBManager':
        """
        Initialize or get the singleton DBManager instance.
        
        Returns:
            Initialized DBManager instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._setup()
        
        return cls._instance
    
    async def _setup(self):
        """Setup database connections and repositories."""
        try:
            # Get connection pool from existing AsyncPGPool
            self.pool = await AsyncPGPool.get_pool()
            
            # Initialize transaction manager
            self.transaction_manager = TransactionManager(self.pool)
            
            # Initialize core components
            self.query_optimizer = QueryOptimizer(self.pool)
            self.monitoring_service = DatabaseMonitoringService(self.pool)
            
            # Initialize repositories with optimized components
            self.ml_predictions = MLPredictionRepository(self.pool, self.transaction_manager)
            self.positions = PositionRepository(self.pool, self.transaction_manager)
            
            # Initialize other repositories
            from database.repositories.order_repository import OrderRepository
            from database.repositories.trade_repository import TradeRepository
            from database.repositories.signal_repository import SignalRepository
            
            self.orders = OrderRepository(self.pool, self.transaction_manager)
            self.trades = TradeRepository(self.pool, self.transaction_manager)
            self.signals = SignalRepository(self.pool, self.transaction_manager)
            
            # Setup circuit breakers for critical operations
            self._setup_circuit_breakers()
            
            # Setup retry handlers
            self._setup_retry_handlers()
            
            # Start monitoring
            await self.monitoring_service.start_monitoring()
            
            self._initialized = True
            logger.info("DBManager initialized successfully with enhanced resilience features")
            
        except Exception as e:
            logger.error(f"Failed to initialize DBManager: {e}")
            await self._cleanup_on_error()
            raise
    
    def _setup_circuit_breakers(self):
        """Setup circuit breakers for database operations."""
        from database.resilience.circuit_breaker import CircuitBreakerConfig
        
        # Connection circuit breaker
        circuit_breaker_manager.create_breaker(
            "db_connection",
            config=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30)
        )
        
        # Query execution circuit breaker
        circuit_breaker_manager.create_breaker(
            "db_query",
            config=CircuitBreakerConfig(failure_threshold=10, recovery_timeout=60)
        )
        
        # Transaction circuit breaker
        circuit_breaker_manager.create_breaker(
            "db_transaction",
            config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=45)
        )
    
    def _setup_retry_handlers(self):
        """Setup retry handlers for database operations."""
        # Handlers are automatically created by retry_manager with default configs
        retry_manager.get_or_create_handler("connection")
        retry_manager.get_or_create_handler("query")
        retry_manager.get_or_create_handler("transaction")
        retry_manager.get_or_create_handler("bulk_operation")
    
    async def _cleanup_on_error(self):
        """Cleanup resources on initialization error."""
        try:
            if self.monitoring_service:
                await self.monitoring_service.stop_monitoring()
            if self.query_optimizer:
                await self.query_optimizer.cleanup()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
    
    @classmethod
    async def get_instance(cls) -> 'DBManager':
        """
        Get the singleton instance (alias for initialize).
        
        Returns:
            DBManager instance
        """
        return await cls.initialize()
    
    @asynccontextmanager
    async def transaction(self, isolation_level: str = "read_committed"):
        """
        Get a transaction context for atomic operations.
        
        Args:
            isolation_level: Transaction isolation level
        
        Yields:
            Database connection within transaction
        
        Example:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO orders ...")
                await conn.execute("INSERT INTO trades ...")
        """
        if not self.transaction_manager:
            raise RuntimeError("DBManager not initialized")
        
        async with self.transaction_manager.transaction(isolation_level) as conn:
            self._query_count += 1
            yield conn
    
    async def execute_in_transaction(
        self,
        operations: List[callable],
        isolation_level: str = "read_committed",
        max_retries: int = 3
    ) -> List[Any]:
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of async callables
            isolation_level: Transaction isolation level
            max_retries: Max retry attempts for deadlock
        
        Returns:
            List of operation results
        """
        if not self.transaction_manager:
            raise RuntimeError("DBManager not initialized")
        
        try:
            results = await self.transaction_manager.execute_in_transaction(
                operations,
                isolation_level,
                max_retries
            )
            self._query_count += len(operations)
            return results
        except Exception as e:
            self._error_count += 1
            logger.error(f"Transaction failed: {e}")
            raise
    
    def create_unit_of_work(self) -> UnitOfWork:
        """
        Create a Unit of Work for complex business transactions.
        
        Returns:
            UnitOfWork instance
        
        Example:
            uow = db.create_unit_of_work()
            uow.register_operation(lambda conn: create_order(conn, order_data))
            uow.register_operation(lambda conn: create_trade(conn, trade_data))
            results = await uow.commit()
        """
        if not self.transaction_manager:
            raise RuntimeError("DBManager not initialized")
        
        return UnitOfWork(self.transaction_manager)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.
        
        Returns:
            Health status dictionary
        """
        try:
            # Check pool connectivity
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            # Get pool stats
            pool_stats = {
                "size": self.pool._size if hasattr(self.pool, '_size') else 0,
                "free": self.pool._free.qsize() if hasattr(self.pool, '_free') else 0,
                "used": self.pool._size - self.pool._free.qsize() if hasattr(self.pool, '_size') else 0
            }
            
            # Get transaction stats
            txn_stats = await self.transaction_manager.get_transaction_stats()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "pool": pool_stats,
                "transactions": txn_stats,
                "metrics": {
                    "total_queries": self._query_count,
                    "total_errors": self._error_count,
                    "uptime_seconds": (datetime.now() - self._start_time).total_seconds()
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "connection_pool": {
                "size": self.pool._size if hasattr(self.pool, '_size') else 0,
                "active": self.pool._size - self.pool._free.qsize() if hasattr(self.pool, '_size') else 0,
                "idle": self.pool._free.qsize() if hasattr(self.pool, '_free') else 0
            },
            "queries": {
                "total": self._query_count,
                "errors": self._error_count,
                "success_rate": ((self._query_count - self._error_count) / self._query_count * 100) 
                                if self._query_count > 0 else 100
            },
            "uptime": {
                "started": self._start_time.isoformat(),
                "duration_seconds": (datetime.now() - self._start_time).total_seconds()
            }
        }
        
        # Add component-specific stats
        if self.query_optimizer:
            stats["query_optimizer"] = await self.query_optimizer.get_query_stats()
        
        if self.monitoring_service:
            monitoring_status = await self.monitoring_service.get_current_status()
            stats["monitoring"] = monitoring_status
        
        # Add circuit breaker stats
        circuit_breaker_health = await circuit_breaker_manager.get_health_summary()
        stats["circuit_breakers"] = circuit_breaker_health
        
        # Add retry handler stats
        retry_summary = retry_manager.get_summary()
        stats["retry_handlers"] = retry_summary
        
        # Add repository-specific stats
        if self.positions:
            stats["positions"] = await self.positions.get_position_stats()
        
        if self.ml_predictions:
            stats["ml_predictions"] = await self.ml_predictions.get_prediction_stats()
        
        return stats
    
    async def execute(self, query: str, *params) -> Any:
        """
        Execute a query and return the result.
        
        Args:
            query: SQL query to execute
            *params: Query parameters
            
        Returns:
            Query execution result
        """
        if not self.pool:
            raise RuntimeError("DBManager not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *params)
                self._query_count += 1
                return result
        except Exception as e:
            self._error_count += 1
            logger.error(f"Execute query failed: {e}")
            raise
    
    async def fetch_all(self, query: str, *params) -> List[Dict[str, Any]]:
        """
        Fetch all records from a query.
        
        Args:
            query: SQL query to execute
            *params: Query parameters
            
        Returns:
            List of records as dictionaries
        """
        if not self.pool:
            raise RuntimeError("DBManager not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                self._query_count += 1
                return [dict(row) for row in rows]
        except Exception as e:
            self._error_count += 1
            logger.error(f"Fetch all query failed: {e}")
            raise
    
    async def fetch_one(self, query: str, *params) -> Optional[Dict[str, Any]]:
        """
        Fetch one record from a query.
        
        Args:
            query: SQL query to execute
            *params: Query parameters
            
        Returns:
            Single record as dictionary or None
        """
        if not self.pool:
            raise RuntimeError("DBManager not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)
                self._query_count += 1
                return dict(row) if row else None
        except Exception as e:
            self._error_count += 1
            logger.error(f"Fetch one query failed: {e}")
            raise

    async def cleanup(self):
        """
        Cleanup database resources.
        
        Should be called on application shutdown.
        """
        try:
            # Stop monitoring service
            if self.monitoring_service:
                await self.monitoring_service.stop_monitoring()
            
            # Cleanup query optimizer
            if self.query_optimizer:
                await self.query_optimizer.cleanup()
            
            # Flush any buffered ML predictions
            if self.ml_predictions:
                await self.ml_predictions.flush_buffer()
            
            # Close connection pool
            if self.pool:
                await AsyncPGPool.close_pool()
            
            logger.info("DBManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during DBManager cleanup: {e}")
    
    @classmethod
    async def shutdown(cls):
        """
        Shutdown the DBManager singleton.
        """
        if cls._instance:
            await cls._instance.cleanup()
            cls._instance = None
            cls._initialized = False
            logger.info("DBManager shutdown completed")


# Convenience functions for backward compatibility
async def get_db() -> DBManager:
    """
    Get database manager instance.
    
    Returns:
        DBManager instance
    """
    return await DBManager.initialize()


async def get_session():
    """
    Get a database connection from the pool.
    
    Returns:
        Database connection
    
    Note: This is for backward compatibility. 
    Prefer using DBManager.transaction() for new code.
    """
    db = await get_db()
    return await db.pool.acquire()


# Example usage patterns
async def example_simple_query():
    """Example of simple repository usage."""
    db = await get_db()
    
    # Get open positions
    positions = await db.positions.get_open_positions()
    
    # Log ML prediction
    from database.models.ml_predictions import MLPrediction
    prediction = MLPrediction(
        symbol="BTC/USDT",
        prediction="BUY",
        confidence=0.85
    )
    await db.ml_predictions.log_prediction(prediction)


async def example_transaction():
    """Example of transaction usage."""
    db = await get_db()
    
    # Method 1: Using context manager
    async with db.transaction() as conn:
        await conn.execute("INSERT INTO orders ...")
        await conn.execute("INSERT INTO trades ...")
    
    # Method 2: Using execute_in_transaction
    async def create_order(conn):
        return await conn.fetchval("INSERT INTO orders ... RETURNING id")
    
    async def create_trade(conn):
        return await conn.fetchval("INSERT INTO trades ... RETURNING id")
    
    results = await db.execute_in_transaction([create_order, create_trade])
    
    # Method 3: Using Unit of Work
    uow = db.create_unit_of_work()
    uow.register_operation(create_order)
    uow.register_operation(create_trade)
    results = await uow.commit()


async def example_bulk_operations():
    """Example of bulk operations."""
    db = await get_db()
    
    # Bulk insert ML predictions
    predictions = [
        MLPrediction(symbol="BTC/USDT", prediction="BUY", confidence=0.8),
        MLPrediction(symbol="ETH/USDT", prediction="SELL", confidence=0.75),
        # ... more predictions
    ]
    
    ids = await db.ml_predictions.log_predictions_batch(predictions)
    
    # Bulk update positions
    updates = [
        (1, {"current_price": 50000, "pnl": 500}),
        (2, {"current_price": 3000, "pnl": -50}),
    ]
    
    count = await db.positions.update_positions_batch(updates)