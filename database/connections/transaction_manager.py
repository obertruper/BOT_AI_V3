"""
Transaction Manager with Unit of Work pattern for atomic database operations.

This module provides transaction management capabilities to ensure data consistency
across multiple database operations, particularly critical for trading operations
where order and trade records must be created atomically.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Callable, Any, Optional, Dict, TypeVar
import asyncpg
from loguru import logger
import time
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class TransactionState(Enum):
    """Transaction lifecycle states."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionMetrics:
    """Metrics for transaction monitoring."""
    transaction_id: str
    start_time: float
    end_time: Optional[float] = None
    state: TransactionState = TransactionState.PENDING
    operations_count: int = 0
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate transaction duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None


class TransactionManager:
    """
    Manages database transactions with Unit of Work pattern.
    
    Features:
    - Atomic execution of multiple operations
    - Automatic rollback on failure
    - Transaction metrics and monitoring
    - Nested transaction support (savepoints)
    - Deadlock detection and retry
    """
    
    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize TransactionManager with connection pool.
        
        Args:
            pool: AsyncPG connection pool
        """
        self.pool = pool
        self._active_transactions: Dict[str, TransactionMetrics] = {}
        self._transaction_counter = 0
        self._lock = asyncio.Lock()
        
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID."""
        self._transaction_counter += 1
        return f"txn_{int(time.time())}_{self._transaction_counter}"
    
    @asynccontextmanager
    async def transaction(self, isolation_level: str = "read_committed"):
        """
        Context manager for database transaction.
        
        Args:
            isolation_level: Transaction isolation level
                - "read_committed" (default)
                - "repeatable_read"
                - "serializable"
        
        Usage:
            async with transaction_manager.transaction() as conn:
                await conn.execute("INSERT INTO orders ...")
                await conn.execute("INSERT INTO trades ...")
        """
        transaction_id = self._generate_transaction_id()
        metrics = TransactionMetrics(
            transaction_id=transaction_id,
            start_time=time.time()
        )
        
        async with self._lock:
            self._active_transactions[transaction_id] = metrics
        
        conn: Optional[asyncpg.Connection] = None
        
        try:
            # Acquire connection from pool
            conn = await self.pool.acquire()
            
            # Set isolation level
            await conn.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level.upper().replace('_', ' ')}")
            
            # Start transaction
            metrics.state = TransactionState.ACTIVE
            transaction = conn.transaction()
            await transaction.start()
            
            logger.debug(f"Transaction {transaction_id} started with isolation level: {isolation_level}")
            
            yield conn
            
            # Commit transaction
            await transaction.commit()
            metrics.state = TransactionState.COMMITTED
            metrics.end_time = time.time()
            
            logger.debug(f"Transaction {transaction_id} committed successfully in {metrics.duration_ms:.2f}ms")
            
        except asyncpg.DeadlockDetectedError as e:
            # Handle deadlock
            metrics.state = TransactionState.FAILED
            metrics.error = f"Deadlock detected: {str(e)}"
            metrics.end_time = time.time()
            
            if conn and transaction:
                await transaction.rollback()
                
            logger.error(f"Transaction {transaction_id} deadlock detected: {e}")
            raise
            
        except Exception as e:
            # Rollback on any error
            metrics.state = TransactionState.ROLLED_BACK
            metrics.error = str(e)
            metrics.end_time = time.time()
            
            if conn and transaction:
                await transaction.rollback()
                
            logger.error(f"Transaction {transaction_id} rolled back due to error: {e}")
            raise
            
        finally:
            # Release connection back to pool
            if conn:
                await self.pool.release(conn)
                
            # Clean up metrics after delay (for monitoring)
            asyncio.create_task(self._cleanup_transaction_metrics(transaction_id))
    
    async def _cleanup_transaction_metrics(self, transaction_id: str, delay: int = 60):
        """
        Clean up transaction metrics after delay.
        
        Args:
            transaction_id: Transaction identifier
            delay: Seconds to wait before cleanup
        """
        await asyncio.sleep(delay)
        async with self._lock:
            self._active_transactions.pop(transaction_id, None)
    
    async def execute_in_transaction(
        self,
        operations: List[Callable[[asyncpg.Connection], Any]],
        isolation_level: str = "read_committed",
        max_retries: int = 3
    ) -> List[Any]:
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of async functions that accept connection
            isolation_level: Transaction isolation level
            max_retries: Maximum retry attempts for deadlock
        
        Returns:
            List of operation results
        
        Usage:
            async def create_order(conn):
                return await conn.fetchval("INSERT INTO orders ... RETURNING id")
            
            async def create_trade(conn, order_id):
                return await conn.fetchval("INSERT INTO trades ... RETURNING id")
            
            results = await manager.execute_in_transaction([
                create_order,
                lambda conn: create_trade(conn, order_id)
            ])
        """
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                results = []
                
                async with self.transaction(isolation_level) as conn:
                    for operation in operations:
                        result = await operation(conn)
                        results.append(result)
                    
                return results
                
            except asyncpg.DeadlockDetectedError as e:
                retry_count += 1
                last_error = e
                
                if retry_count < max_retries:
                    # Exponential backoff
                    wait_time = 0.1 * (2 ** retry_count)
                    logger.warning(
                        f"Deadlock detected, retrying in {wait_time}s "
                        f"(attempt {retry_count}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Max retries exceeded for transaction after {max_retries} attempts")
                    raise
                    
            except Exception as e:
                logger.error(f"Transaction failed: {e}")
                raise
        
        raise last_error
    
    @asynccontextmanager
    async def savepoint(self, conn: asyncpg.Connection, name: str):
        """
        Create a savepoint within a transaction for nested operations.
        
        Args:
            conn: Active connection within a transaction
            name: Savepoint name
        
        Usage:
            async with transaction_manager.transaction() as conn:
                await conn.execute("INSERT INTO orders ...")
                
                async with transaction_manager.savepoint(conn, "trade_creation"):
                    await conn.execute("INSERT INTO trades ...")
                    # If this fails, only rolls back to savepoint
        """
        try:
            # Create savepoint
            await conn.execute(f"SAVEPOINT {name}")
            logger.debug(f"Savepoint '{name}' created")
            
            yield conn
            
            # Release savepoint on success
            await conn.execute(f"RELEASE SAVEPOINT {name}")
            logger.debug(f"Savepoint '{name}' released")
            
        except Exception as e:
            # Rollback to savepoint on error
            await conn.execute(f"ROLLBACK TO SAVEPOINT {name}")
            logger.warning(f"Rolled back to savepoint '{name}': {e}")
            raise
    
    async def get_transaction_metrics(self) -> Dict[str, TransactionMetrics]:
        """
        Get current transaction metrics for monitoring.
        
        Returns:
            Dictionary of active transaction metrics
        """
        async with self._lock:
            return self._active_transactions.copy()
    
    async def get_transaction_stats(self) -> Dict[str, Any]:
        """
        Get transaction statistics.
        
        Returns:
            Statistics dictionary
        """
        async with self._lock:
            active_txns = list(self._active_transactions.values())
        
        if not active_txns:
            return {
                "active_transactions": 0,
                "avg_duration_ms": 0,
                "longest_duration_ms": 0,
                "failed_transactions": 0
            }
        
        completed_txns = [t for t in active_txns if t.end_time]
        failed_txns = [t for t in active_txns if t.state == TransactionState.FAILED]
        
        durations = [t.duration_ms for t in completed_txns if t.duration_ms]
        
        return {
            "active_transactions": len([t for t in active_txns if t.state == TransactionState.ACTIVE]),
            "total_transactions": self._transaction_counter,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "longest_duration_ms": max(durations) if durations else 0,
            "failed_transactions": len(failed_txns),
            "committed_transactions": len([t for t in active_txns if t.state == TransactionState.COMMITTED])
        }


class UnitOfWork:
    """
    Unit of Work pattern implementation for managing complex business transactions.
    
    This class provides a higher-level abstraction for coordinating multiple
    repository operations within a single transaction boundary.
    """
    
    def __init__(self, transaction_manager: TransactionManager):
        """
        Initialize Unit of Work.
        
        Args:
            transaction_manager: TransactionManager instance
        """
        self.transaction_manager = transaction_manager
        self._operations: List[Callable] = []
        self._conn: Optional[asyncpg.Connection] = None
        
    def register_operation(self, operation: Callable):
        """
        Register an operation to be executed in the transaction.
        
        Args:
            operation: Async callable that accepts connection
        """
        self._operations.append(operation)
        
    async def commit(self) -> List[Any]:
        """
        Execute all registered operations in a transaction.
        
        Returns:
            List of operation results
        """
        if not self._operations:
            logger.warning("No operations registered for Unit of Work")
            return []
        
        try:
            results = await self.transaction_manager.execute_in_transaction(
                self._operations,
                isolation_level="read_committed"
            )
            
            logger.info(f"Unit of Work committed {len(self._operations)} operations successfully")
            return results
            
        finally:
            # Clear operations after execution
            self._operations.clear()
    
    async def rollback(self):
        """Clear pending operations without executing."""
        operations_count = len(self._operations)
        self._operations.clear()
        logger.info(f"Unit of Work rolled back {operations_count} pending operations")


# Example usage for trading operations
async def create_order_with_trade_atomic(
    transaction_manager: TransactionManager,
    order_data: dict,
    trade_data: dict
) -> tuple[int, int]:
    """
    Create order and trade atomically.
    
    Args:
        transaction_manager: TransactionManager instance
        order_data: Order information
        trade_data: Trade information
    
    Returns:
        Tuple of (order_id, trade_id)
    """
    async def create_order(conn):
        query = """
        INSERT INTO orders (symbol, side, quantity, price, status, exchange)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """
        return await conn.fetchval(
            query,
            order_data['symbol'],
            order_data['side'],
            order_data['quantity'],
            order_data['price'],
            'pending',
            order_data['exchange']
        )
    
    async def create_trade(conn):
        query = """
        INSERT INTO trades (order_id, symbol, side, quantity, price, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """
        return await conn.fetchval(
            query,
            trade_data['order_id'],
            trade_data['symbol'],
            trade_data['side'],
            trade_data['quantity'],
            trade_data['price'],
            'executed'
        )
    
    # Execute both operations atomically
    results = await transaction_manager.execute_in_transaction([
        create_order,
        create_trade
    ])
    
    return results[0], results[1]