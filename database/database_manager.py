#!/usr/bin/env python3
"""
Database Manager for BOT Trading v3.

Provides centralized database management with TransactionManager integration
and repository initialization.
"""

import asyncio
from typing import Dict, Any, Optional
from loguru import logger

from database.connections.postgres import AsyncPGPool
from database.connections.transaction_manager import TransactionManager
from database.repositories.order_repository import OrderRepository
from database.repositories.trade_repository import TradeRepository
from database.repositories.signal_repository import SignalRepository
from database.repositories.ml_prediction_repository import MLPredictionRepository
from database.repositories.position_repository import PositionRepository


class DatabaseManager:
    """
    Central database manager for all database operations.
    
    Manages connection pools, transaction manager, and repositories
    with automatic initialization and cleanup.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DatabaseManager.
        
        Args:
            config: Database configuration (optional)
        """
        self.config = config or {}
        self.pool = None
        self.transaction_manager = None
        
        # Repositories
        self.order_repository: Optional[OrderRepository] = None
        self.trade_repository: Optional[TradeRepository] = None
        self.signal_repository: Optional[SignalRepository] = None
        self.ml_prediction_repository: Optional[MLPredictionRepository] = None
        self.position_repository: Optional[PositionRepository] = None
        
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connections and repositories."""
        try:
            logger.info("Initializing DatabaseManager...")
            
            # Initialize connection pool
            self.pool = await AsyncPGPool.get_pool()
            logger.info("✅ Database connection pool initialized")
            
            # Initialize transaction manager
            self.transaction_manager = await AsyncPGPool.get_transaction_manager()
            logger.info("✅ TransactionManager initialized")
            
            # Initialize repositories with TransactionManager
            self.order_repository = OrderRepository(self.pool, self.transaction_manager)
            self.trade_repository = TradeRepository(self.pool, self.transaction_manager)
            self.signal_repository = SignalRepository(self.pool, self.transaction_manager)
            self.ml_prediction_repository = MLPredictionRepository(self.pool, self.transaction_manager)
            self.position_repository = PositionRepository(self.pool, self.transaction_manager)
            
            logger.info("✅ All repositories initialized with TransactionManager")
            
            self._is_initialized = True
            logger.info("✅ DatabaseManager initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize DatabaseManager: {e}")
            raise
    
    async def close(self) -> None:
        """Close all database connections."""
        try:
            logger.info("Closing DatabaseManager connections...")
            
            # Close connection pool
            await AsyncPGPool.close_pool()
            
            # Reset repositories
            self.order_repository = None
            self.trade_repository = None
            self.signal_repository = None
            self.ml_prediction_repository = None
            self.position_repository = None
            
            # Reset managers
            self.transaction_manager = None
            self.pool = None
            
            self._is_initialized = False
            logger.info("✅ DatabaseManager closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing DatabaseManager: {e}")
            raise
    
    async def get_active_connections_count(self) -> int:
        """Get number of active database connections."""
        if self.pool:
            return len(self.pool._holders) - len(self.pool._queue._queue)
        return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        try:
            if not self._is_initialized:
                return {
                    "status": "not_initialized",
                    "healthy": False,
                    "error": "DatabaseManager not initialized"
                }
            
            # Test connection with simple query
            result = await AsyncPGPool.fetchrow("SELECT 1 as test")
            
            # Get connection statistics
            active_connections = await self.get_active_connections_count()
            
            # Get transaction statistics if available
            tx_stats = {}
            if self.transaction_manager:
                tx_stats = await self.transaction_manager.get_transaction_stats()
            
            return {
                "status": "healthy",
                "healthy": True,
                "connection_test": result is not None and result['test'] == 1,
                "active_connections": active_connections,
                "transaction_stats": tx_stats,
                "repositories_initialized": all([
                    self.order_repository is not None,
                    self.trade_repository is not None,
                    self.signal_repository is not None,
                    self.ml_prediction_repository is not None,
                    self.position_repository is not None
                ])
            }
            
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    async def execute_in_transaction(self, operations) -> Any:
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of async functions or single async function
        
        Returns:
            Result of operations
        """
        if not self.transaction_manager:
            raise RuntimeError("TransactionManager not initialized")
        
        if not isinstance(operations, list):
            operations = [operations]
        
        return await self.transaction_manager.execute_in_transaction(operations)
    
    async def create_order_with_trade_atomic(
        self,
        order_data: Dict[str, Any],
        trade_data: Dict[str, Any]
    ) -> tuple[int, int]:
        """
        Create order and trade atomically using TransactionManager.
        
        Example of using repositories within transactions.
        """
        async def create_order_operation(conn):
            # Here we would use repository methods within transaction
            return await self.order_repository.create_order_atomic(conn, order_data)
        
        async def create_trade_operation(conn):
            return await self.trade_repository.create_trade_atomic(conn, trade_data)
        
        results = await self.transaction_manager.execute_in_transaction([
            create_order_operation,
            create_trade_operation
        ])
        
        return results[0], results[1]
    
    @property
    def is_initialized(self) -> bool:
        """Check if DatabaseManager is initialized."""
        return self._is_initialized


# Global DatabaseManager instance
_global_database_manager: Optional[DatabaseManager] = None


async def get_database_manager(config: Optional[Dict[str, Any]] = None) -> DatabaseManager:
    """
    Get or create global DatabaseManager instance.
    
    Args:
        config: Database configuration
    
    Returns:
        DatabaseManager instance
    """
    global _global_database_manager
    
    if _global_database_manager is None:
        _global_database_manager = DatabaseManager(config)
        await _global_database_manager.initialize()
    
    return _global_database_manager


async def close_global_database_manager():
    """Close global DatabaseManager instance."""
    global _global_database_manager
    
    if _global_database_manager:
        await _global_database_manager.close()
        _global_database_manager = None


# Context manager for DatabaseManager
class DatabaseContext:
    """Context manager for DatabaseManager lifecycle."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config
        self.manager = None
    
    async def __aenter__(self) -> DatabaseManager:
        """Enter async context."""
        self.manager = DatabaseManager(self.config)
        await self.manager.initialize()
        return self.manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.manager:
            await self.manager.close()


# Example usage functions
async def example_atomic_operations():
    """Example of using atomic operations with DatabaseManager."""
    async with DatabaseContext() as db_manager:
        
        # Example 1: Simple transaction
        async def update_order_status(conn):
            return await conn.execute(
                "UPDATE orders SET status = $1 WHERE id = $2",
                "filled", 123
            )
        
        result = await db_manager.execute_in_transaction(update_order_status)
        logger.info(f"Order status updated: {result}")
        
        # Example 2: Complex multi-operation transaction
        order_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 1.0,
            "price": 50000.0
        }
        
        trade_data = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 1.0,
            "price": 50000.0
        }
        
        order_id, trade_id = await db_manager.create_order_with_trade_atomic(
            order_data, trade_data
        )
        logger.info(f"Created order {order_id} and trade {trade_id} atomically")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_atomic_operations())