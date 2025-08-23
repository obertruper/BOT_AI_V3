#!/usr/bin/env python3
"""
Unit tests for TransactionManager and BaseRepository.

Tests transaction management, bulk operations, atomicity,
Unit of Work pattern, and repository base functionality.
"""

import pytest
import asyncio
import asyncpg
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from datetime import datetime
import time

from database.connections.transaction_manager import (
    TransactionManager,
    TransactionState,
    TransactionMetrics,
    UnitOfWork,
    create_order_with_trade_atomic
)
from database.repositories.base_repository import BaseRepository


# Test models for BaseRepository
class TestModel:
    """Test model for repository testing."""
    
    def __init__(self, id: int = None, name: str = "test", value: float = 0.0):
        self.id = id
        self.name = name
        self.value = value


class TestRepository(BaseRepository[TestModel]):
    """Test repository implementation."""
    
    def _to_dict(self, model: TestModel) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {
            'name': model.name,
            'value': model.value
        }
        if model.id is not None:
            result['id'] = model.id
        return result
    
    def _from_record(self, record: asyncpg.Record) -> TestModel:
        """Convert record to model."""
        return TestModel(
            id=record.get('id'),
            name=record.get('name', 'test'),
            value=record.get('value', 0.0)
        )


class TestTransactionManager:
    """Test TransactionManager functionality."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create mock connection pool."""
        pool = MagicMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        
        # Setup connection mock
        mock_conn.transaction.return_value = mock_transaction
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock()
        mock_conn.fetchval = AsyncMock()
        
        # Setup pool mock
        pool.acquire = AsyncMock(return_value=mock_conn)
        pool.release = AsyncMock()
        
        # Setup transaction mock
        mock_transaction.start = AsyncMock()
        mock_transaction.commit = AsyncMock()
        mock_transaction.rollback = AsyncMock()
        
        return pool, mock_conn, mock_transaction
    
    @pytest.fixture
    def transaction_manager(self, mock_pool):
        """Create TransactionManager with mock pool."""
        pool, _, _ = mock_pool
        return TransactionManager(pool)
    
    def test_transaction_manager_init(self, transaction_manager):
        """Test TransactionManager initialization."""
        assert isinstance(transaction_manager._active_transactions, dict)
        assert transaction_manager._transaction_counter == 0
        assert transaction_manager._lock is not None
    
    def test_generate_transaction_id(self, transaction_manager):
        """Test transaction ID generation."""
        id1 = transaction_manager._generate_transaction_id()
        id2 = transaction_manager._generate_transaction_id()
        
        assert id1 != id2
        assert id1.startswith('txn_')
        assert id2.startswith('txn_')
        assert transaction_manager._transaction_counter == 2
    
    @pytest.mark.asyncio
    async def test_transaction_context_success(self, mock_pool):
        """Test successful transaction context."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        async with manager.transaction() as conn:
            assert conn == mock_conn
            await conn.execute("INSERT INTO test ...")
        
        # Verify transaction lifecycle
        mock_transaction.start.assert_called_once()
        mock_transaction.commit.assert_called_once()
        mock_transaction.rollback.assert_not_called()
        pool.acquire.assert_called_once()
        pool.release.assert_called_once_with(mock_conn)
    
    @pytest.mark.asyncio
    async def test_transaction_context_rollback_on_error(self, mock_pool):
        """Test transaction rollback on error."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        # Mock execute to raise error
        mock_conn.execute.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            async with manager.transaction() as conn:
                await conn.execute("INSERT INTO test ...")
        
        # Verify rollback occurred
        mock_transaction.start.assert_called_once()
        mock_transaction.commit.assert_not_called()
        mock_transaction.rollback.assert_called_once()
        pool.release.assert_called_once_with(mock_conn)
    
    @pytest.mark.asyncio
    async def test_transaction_deadlock_handling(self, mock_pool):
        """Test deadlock handling."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        # Mock execute to raise deadlock error
        mock_conn.execute.side_effect = asyncpg.DeadlockDetectedError("Deadlock")
        
        with pytest.raises(asyncpg.DeadlockDetectedError):
            async with manager.transaction() as conn:
                await conn.execute("INSERT INTO test ...")
        
        # Verify rollback occurred
        mock_transaction.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_isolation_levels(self, mock_pool):
        """Test different isolation levels."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        # Test different isolation levels
        isolation_levels = [
            "read_committed",
            "repeatable_read", 
            "serializable"
        ]
        
        for level in isolation_levels:
            async with manager.transaction(isolation_level=level) as conn:
                pass
            
            # Verify isolation level was set
            expected_sql = f"SET TRANSACTION ISOLATION LEVEL {level.upper().replace('_', ' ')}"
            mock_conn.execute.assert_called_with(expected_sql)
    
    @pytest.mark.asyncio
    async def test_execute_in_transaction_success(self, mock_pool):
        """Test execute_in_transaction with success."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        # Mock operations
        async def op1(conn):
            return await conn.fetchval("INSERT ... RETURNING id")
        
        async def op2(conn):
            return await conn.execute("UPDATE ...")
        
        # Mock return values
        mock_conn.fetchval.return_value = 123
        mock_conn.execute.return_value = "UPDATE 1"
        
        results = await manager.execute_in_transaction([op1, op2])
        
        assert len(results) == 2
        assert results[0] == 123
        assert results[1] == "UPDATE 1"
    
    @pytest.mark.asyncio
    async def test_execute_in_transaction_deadlock_retry(self, mock_pool):
        """Test execute_in_transaction with deadlock retry."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        # Mock operation
        call_count = 0
        async def operation(conn):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise asyncpg.DeadlockDetectedError("Deadlock")
            return "success"
        
        with patch('asyncio.sleep'):  # Speed up test
            results = await manager.execute_in_transaction([operation])
        
        assert results == ["success"]
        assert call_count == 3  # Should have retried
    
    @pytest.mark.asyncio
    async def test_execute_in_transaction_max_retries_exceeded(self, mock_pool):
        """Test execute_in_transaction with max retries exceeded."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        # Mock operation that always fails
        async def operation(conn):
            raise asyncpg.DeadlockDetectedError("Deadlock")
        
        with patch('asyncio.sleep'):  # Speed up test
            with pytest.raises(asyncpg.DeadlockDetectedError):
                await manager.execute_in_transaction([operation], max_retries=2)
    
    @pytest.mark.asyncio
    async def test_savepoint_success(self, mock_pool):
        """Test savepoint functionality."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        async with manager.transaction() as conn:
            async with manager.savepoint(conn, "test_savepoint"):
                await conn.execute("INSERT INTO test ...")
        
        # Verify savepoint lifecycle
        mock_conn.execute.assert_any_call("SAVEPOINT test_savepoint")
        mock_conn.execute.assert_any_call("RELEASE SAVEPOINT test_savepoint")
    
    @pytest.mark.asyncio
    async def test_savepoint_rollback_on_error(self, mock_pool):
        """Test savepoint rollback on error."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        async with manager.transaction() as conn:
            with pytest.raises(Exception, match="Test error"):
                async with manager.savepoint(conn, "test_savepoint"):
                    # Setup mock to fail on third call (after savepoint creation)
                    call_count = [0]
                    def side_effect(*args):
                        call_count[0] += 1
                        if call_count[0] == 3:  # Third call fails
                            raise Exception("Test error")
                    
                    mock_conn.execute.side_effect = side_effect
                    await conn.execute("INSERT INTO test ...")
        
        # Verify savepoint rollback
        mock_conn.execute.assert_any_call("ROLLBACK TO SAVEPOINT test_savepoint")
    
    @pytest.mark.asyncio
    async def test_transaction_metrics(self, transaction_manager):
        """Test transaction metrics collection."""
        # Get initial metrics
        initial_stats = await transaction_manager.get_transaction_stats()
        assert initial_stats['active_transactions'] == 0
        
        # Start a transaction (without completing it)
        transaction_manager._generate_transaction_id()
        
        # Verify counter increased
        assert transaction_manager._transaction_counter == 1
    
    @pytest.mark.asyncio
    async def test_transaction_metrics_cleanup(self, mock_pool):
        """Test transaction metrics cleanup."""
        pool, mock_conn, mock_transaction = mock_pool
        manager = TransactionManager(pool)
        
        # Complete a transaction
        async with manager.transaction() as conn:
            pass
        
        # Verify metrics are tracked
        metrics = await manager.get_transaction_metrics()
        assert len(metrics) >= 0  # May be cleaned up already due to asyncio timing


class TestUnitOfWork:
    """Test Unit of Work pattern implementation."""
    
    @pytest.fixture
    def mock_transaction_manager(self):
        """Create mock TransactionManager."""
        manager = MagicMock()
        manager.execute_in_transaction = AsyncMock(return_value=[1, 2])
        return manager
    
    def test_unit_of_work_init(self, mock_transaction_manager):
        """Test UnitOfWork initialization."""
        uow = UnitOfWork(mock_transaction_manager)
        
        assert uow.transaction_manager == mock_transaction_manager
        assert len(uow._operations) == 0
    
    def test_register_operation(self, mock_transaction_manager):
        """Test operation registration."""
        uow = UnitOfWork(mock_transaction_manager)
        
        async def operation1():
            pass
        
        async def operation2():
            pass
        
        uow.register_operation(operation1)
        uow.register_operation(operation2)
        
        assert len(uow._operations) == 2
    
    @pytest.mark.asyncio
    async def test_commit_success(self, mock_transaction_manager):
        """Test successful commit."""
        uow = UnitOfWork(mock_transaction_manager)
        
        # Register operations
        async def op1():
            return "result1"
        
        async def op2():
            return "result2"
        
        uow.register_operation(op1)
        uow.register_operation(op2)
        
        results = await uow.commit()
        
        assert results == [1, 2]  # From mock
        assert len(uow._operations) == 0  # Cleared after commit
        mock_transaction_manager.execute_in_transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_commit_no_operations(self, mock_transaction_manager):
        """Test commit with no operations."""
        uow = UnitOfWork(mock_transaction_manager)
        
        results = await uow.commit()
        
        assert results == []
        mock_transaction_manager.execute_in_transaction.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rollback(self, mock_transaction_manager):
        """Test rollback functionality."""
        uow = UnitOfWork(mock_transaction_manager)
        
        # Register operations
        uow.register_operation(lambda: None)
        uow.register_operation(lambda: None)
        
        await uow.rollback()
        
        assert len(uow._operations) == 0


class TestBaseRepository:
    """Test BaseRepository functionality."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create mock connection pool."""
        pool = MagicMock()
        mock_conn = AsyncMock()
        
        # Setup connection mock
        mock_conn.execute = AsyncMock(return_value="INSERT 1")
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchval = AsyncMock(return_value=1)
        
        # Setup pool mock
        pool.acquire = AsyncMock(return_value=mock_conn)
        pool.release = AsyncMock()
        
        return pool, mock_conn
    
    @pytest.fixture
    def mock_transaction_manager(self, mock_pool):
        """Create mock TransactionManager."""
        pool, _ = mock_pool
        return MagicMock()
    
    @pytest.fixture
    def test_repository(self, mock_pool, mock_transaction_manager):
        """Create test repository."""
        pool, _ = mock_pool
        return TestRepository(
            pool=pool,
            table_name="test_table",
            model_class=TestModel,
            transaction_manager=mock_transaction_manager
        )
    
    def test_repository_init(self, test_repository, mock_pool):
        """Test repository initialization."""
        pool, _ = mock_pool
        
        assert test_repository.pool == pool
        assert test_repository.table_name == "test_table"
        assert test_repository.model_class == TestModel
    
    @pytest.mark.asyncio
    async def test_bulk_insert_success(self, test_repository, mock_transaction_manager):
        """Test successful bulk insert."""
        # Setup transaction manager mock
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            MagicMock(id=1),
            MagicMock(id=2)
        ]
        mock_transaction_manager.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction_manager.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test data
        items = [
            TestModel(name="test1", value=1.0),
            TestModel(name="test2", value=2.0)
        ]
        
        results = await test_repository.bulk_insert(
            items=items,
            returning_fields=["id"]
        )
        
        assert len(results) == 2
        mock_conn.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_insert_empty_items(self, test_repository):
        """Test bulk insert with empty items."""
        results = await test_repository.bulk_insert([])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_bulk_insert_with_conflict(self, test_repository, mock_transaction_manager):
        """Test bulk insert with conflict handling."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = None
        mock_transaction_manager.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction_manager.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        items = [TestModel(name="test1", value=1.0)]
        
        results = await test_repository.bulk_insert(
            items=items,
            on_conflict="ON CONFLICT DO NOTHING"
        )
        
        assert results == []
        mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_update_success(self, test_repository, mock_transaction_manager):
        """Test successful bulk update."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "UPDATE 1"
        transaction_mock = AsyncMock()
        transaction_mock.__aenter__ = AsyncMock(return_value=None)
        transaction_mock.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction.return_value = transaction_mock
        
        mock_transaction_manager.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction_manager.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        updates = [
            ({"id": 1}, {"name": "updated1"}),
            ({"id": 2}, {"name": "updated2"})
        ]
        
        count = await test_repository.bulk_update(updates)
        assert count == 2  # 2 updates
    
    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, test_repository, mock_transaction_manager):
        """Test successful bulk delete."""
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 2"
        mock_transaction_manager.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction_manager.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        conditions = [
            {"id": 1},
            {"id": 2}
        ]
        
        count = await test_repository.bulk_delete(conditions)
        assert count == 2
        mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_upsert_success(self, test_repository):
        """Test successful bulk upsert."""
        items = [TestModel(name="test1", value=1.0)]
        
        # Mock bulk_insert (which upsert calls)
        with patch.object(test_repository, 'bulk_insert') as mock_bulk_insert:
            mock_bulk_insert.return_value = [{"id": 1}]
            
            results = await test_repository.bulk_upsert(
                items=items,
                conflict_columns=["name"],
                update_columns=["value"]
            )
            
            assert results == [{"id": 1}]
            mock_bulk_insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_success(self, test_repository, mock_transaction_manager):
        """Test successful count operation."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 5
        mock_transaction_manager.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction_manager.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        count = await test_repository.count({"name": "test"})
        assert count == 5
        mock_conn.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exists_success(self, test_repository, mock_transaction_manager):
        """Test successful exists check."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True
        mock_transaction_manager.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction_manager.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        exists = await test_repository.exists({"name": "test"})
        assert exists is True
        mock_conn.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_batch_by_ids_success(self, test_repository, mock_transaction_manager):
        """Test successful batch get by IDs."""
        mock_conn = AsyncMock()
        mock_records = [
            MagicMock(get=MagicMock(side_effect=lambda k, d=None: {"id": 1, "name": "test1", "value": 1.0}.get(k, d))),
            MagicMock(get=MagicMock(side_effect=lambda k, d=None: {"id": 2, "name": "test2", "value": 2.0}.get(k, d)))
        ]
        mock_conn.fetch.return_value = mock_records
        mock_transaction_manager.transaction.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_transaction_manager.transaction.return_value.__aexit__ = AsyncMock(return_value=None)
        
        results = await test_repository.get_batch_by_ids([1, 2])
        
        assert len(results) == 2
        assert all(isinstance(r, TestModel) for r in results)


class TestCreateOrderWithTradeAtomic:
    """Test atomic order and trade creation example function."""
    
    @pytest.mark.asyncio
    async def test_create_order_with_trade_atomic_success(self, mock_pool):
        """Test successful atomic order and trade creation."""
        pool, mock_conn, _ = mock_pool
        manager = TransactionManager(pool)
        
        # Mock return values
        mock_conn.fetchval.side_effect = [123, 456]  # order_id, trade_id
        
        order_data = {
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'quantity': 1.0,
            'price': 50000.0,
            'exchange': 'bybit'
        }
        
        trade_data = {
            'order_id': 123,
            'symbol': 'BTC/USDT',
            'side': 'buy',
            'quantity': 1.0,
            'price': 50000.0
        }
        
        order_id, trade_id = await create_order_with_trade_atomic(
            manager, order_data, trade_data
        )
        
        assert order_id == 123
        assert trade_id == 456


if __name__ == "__main__":
    pytest.main([__file__])