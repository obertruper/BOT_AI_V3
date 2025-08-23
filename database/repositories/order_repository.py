"""
Order Repository for comprehensive order management.

This repository handles all database operations for trading orders,
with optimized bulk operations and atomic state transitions.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncpg
import json
from loguru import logger
from enum import Enum

from database.repositories.base_repository import BaseRepository
from database.connections.transaction_manager import TransactionManager


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class Order:
    """Order model class."""
    
    def __init__(
        self,
        id: Optional[int] = None,
        symbol: str = None,
        exchange: str = None,
        side: str = None,
        order_type: str = OrderType.LIMIT.value,
        quantity: Decimal = None,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        filled_quantity: Decimal = Decimal('0'),
        average_price: Optional[Decimal] = None,
        status: str = OrderStatus.PENDING.value,
        exchange_order_id: Optional[str] = None,
        position_id: Optional[int] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        leverage: int = 5,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        executed_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ):
        self.id = id
        self.symbol = symbol
        self.exchange = exchange
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.filled_quantity = filled_quantity
        self.average_price = average_price
        self.status = status
        self.exchange_order_id = exchange_order_id
        self.position_id = position_id
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.leverage = leverage
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.executed_at = executed_at
        self.cancelled_at = cancelled_at
        self.metadata = metadata or {}

    @property
    def is_active(self) -> bool:
        """Check if order is in active state."""
        return self.status in [OrderStatus.PENDING.value, OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]

    @property
    def is_completed(self) -> bool:
        """Check if order is completed."""
        return self.status in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value, OrderStatus.REJECTED.value, OrderStatus.EXPIRED.value]

    @property
    def remaining_quantity(self) -> Decimal:
        """Get remaining quantity to fill."""
        return self.quantity - self.filled_quantity


class OrderRepository(BaseRepository[Order]):
    """
    Repository for order database operations.
    
    Features:
    - Atomic order state transitions
    - Bulk order management for high-frequency trading
    - Order lifecycle tracking
    - Exchange synchronization
    """
    
    def __init__(self, pool: asyncpg.Pool, transaction_manager: TransactionManager = None):
        """
        Initialize Order Repository.
        
        Args:
            pool: AsyncPG connection pool
            transaction_manager: Transaction manager for atomic operations
        """
        super().__init__(pool, "orders", Order, transaction_manager)
        
    def _to_dict(self, model: Order) -> Dict[str, Any]:
        """Convert Order to dictionary for database."""
        return {
            "symbol": model.symbol,
            "exchange": model.exchange,
            "side": model.side,
            "order_type": model.order_type,
            "quantity": float(model.quantity),
            "price": float(model.price) if model.price else None,
            "stop_price": float(model.stop_price) if model.stop_price else None,
            "filled_quantity": float(model.filled_quantity),
            "average_price": float(model.average_price) if model.average_price else None,
            "status": model.status,
            "exchange_order_id": model.exchange_order_id,
            "position_id": model.position_id,
            "stop_loss": float(model.stop_loss) if model.stop_loss else None,
            "take_profit": float(model.take_profit) if model.take_profit else None,
            "leverage": model.leverage,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
            "executed_at": model.executed_at,
            "cancelled_at": model.cancelled_at,
            "metadata": json.dumps(model.metadata) if model.metadata else None
        }
    
    def _from_record(self, record: asyncpg.Record) -> Order:
        """Convert database record to Order."""
        return Order(
            id=record["id"],
            symbol=record["symbol"],
            exchange=record["exchange"],
            side=record["side"],
            order_type=record["order_type"],
            quantity=Decimal(str(record["quantity"])),
            price=Decimal(str(record["price"])) if record["price"] else None,
            stop_price=Decimal(str(record["stop_price"])) if record["stop_price"] else None,
            filled_quantity=Decimal(str(record["filled_quantity"])),
            average_price=Decimal(str(record["average_price"])) if record["average_price"] else None,
            status=record["status"],
            exchange_order_id=record["exchange_order_id"],
            position_id=record["position_id"],
            stop_loss=Decimal(str(record["stop_loss"])) if record["stop_loss"] else None,
            take_profit=Decimal(str(record["take_profit"])) if record["take_profit"] else None,
            leverage=record["leverage"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            executed_at=record["executed_at"],
            cancelled_at=record["cancelled_at"],
            metadata=json.loads(record["metadata"]) if record["metadata"] else {}
        )
    
    async def create_order(
        self,
        order: Order,
        signal_id: Optional[int] = None
    ) -> int:
        """
        Create a new order with optional signal linkage.
        
        Args:
            order: Order to create
            signal_id: Related signal ID
        
        Returns:
            Order ID
        """
        query = """
        INSERT INTO orders 
        (symbol, exchange, side, order_type, quantity, price, stop_price, 
         status, stop_loss, take_profit, leverage, created_at, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING id
        """
        
        data = self._to_dict(order)
        
        if self.transaction_manager:
            async with self.transaction_manager.transaction() as conn:
                order_id = await conn.fetchval(
                    query,
                    data["symbol"],
                    data["exchange"],
                    data["side"],
                    data["order_type"],
                    data["quantity"],
                    data["price"],
                    data["stop_price"],
                    data["status"],
                    data["stop_loss"],
                    data["take_profit"],
                    data["leverage"],
                    data["created_at"],
                    data["metadata"]
                )
                
                # Link to signal if provided
                if signal_id:
                    await conn.execute(
                        "UPDATE signals SET order_id = $1 WHERE id = $2",
                        order_id, signal_id
                    )
        else:
            async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
                order_id = await conn.fetchval(
                    query,
                    data["symbol"],
                    data["exchange"],
                    data["side"],
                    data["order_type"],
                    data["quantity"],
                    data["price"],
                    data["stop_price"],
                    data["status"],
                    data["stop_loss"],
                    data["take_profit"],
                    data["leverage"],
                    data["created_at"],
                    data["metadata"]
                )
        
        order.id = order_id
        logger.info(f"Created order {order_id} for {order.symbol} {order.side} {order.quantity}")
        return order_id
    
    async def update_order_status(
        self,
        order_id: int,
        new_status: str,
        filled_quantity: Optional[Decimal] = None,
        average_price: Optional[Decimal] = None,
        exchange_order_id: Optional[str] = None
    ) -> bool:
        """
        Update order status with atomic transition.
        
        Args:
            order_id: Order ID
            new_status: New status
            filled_quantity: Filled quantity
            average_price: Average execution price
            exchange_order_id: Exchange order identifier
        
        Returns:
            True if updated successfully
        """
        # Build update fields
        update_fields = ["status = $2", "updated_at = $3"]
        args = [order_id, new_status, datetime.now()]
        param_counter = 4
        
        if filled_quantity is not None:
            update_fields.append(f"filled_quantity = ${param_counter}")
            args.append(float(filled_quantity))
            param_counter += 1
        
        if average_price is not None:
            update_fields.append(f"average_price = ${param_counter}")
            args.append(float(average_price))
            param_counter += 1
        
        if exchange_order_id is not None:
            update_fields.append(f"exchange_order_id = ${param_counter}")
            args.append(exchange_order_id)
            param_counter += 1
        
        # Add status-specific timestamps
        if new_status == OrderStatus.FILLED.value:
            update_fields.append(f"executed_at = ${param_counter}")
            args.append(datetime.now())
            param_counter += 1
        elif new_status == OrderStatus.CANCELLED.value:
            update_fields.append(f"cancelled_at = ${param_counter}")
            args.append(datetime.now())
            param_counter += 1
        
        query = f"""
        UPDATE orders 
        SET {', '.join(update_fields)}
        WHERE id = $1
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            result = await conn.execute(query, *args)
            updated = int(result.split()[-1]) > 0
        
        if updated:
            logger.info(f"Updated order {order_id} status to {new_status}")
        
        return updated
    
    async def get_active_orders(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Order]:
        """
        Get all active orders with optional filters.
        
        Args:
            exchange: Filter by exchange
            symbol: Filter by symbol
        
        Returns:
            List of active orders
        """
        query_parts = [
            "SELECT * FROM orders",
            "WHERE status IN ('pending', 'open', 'partially_filled')"
        ]
        args = []
        param_counter = 1
        
        if exchange:
            query_parts.append(f"AND exchange = ${param_counter}")
            args.append(exchange)
            param_counter += 1
        
        if symbol:
            query_parts.append(f"AND symbol = ${param_counter}")
            args.append(symbol)
            param_counter += 1
        
        query_parts.append("ORDER BY created_at DESC")
        query = " ".join(query_parts)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query, *args)
            return [self._from_record(record) for record in records]
    
    async def cancel_orders(
        self,
        order_ids: List[int],
        reason: str = "manual_cancel"
    ) -> int:
        """
        Cancel multiple orders atomically.
        
        Args:
            order_ids: List of order IDs to cancel
            reason: Cancellation reason
        
        Returns:
            Number of cancelled orders
        """
        if not order_ids:
            return 0
        
        query = """
        UPDATE orders 
        SET status = 'cancelled', 
            cancelled_at = $1, 
            updated_at = $1,
            metadata = COALESCE(metadata::jsonb, '{}'::jsonb) || $2::jsonb
        WHERE id = ANY($3) 
        AND status IN ('pending', 'open', 'partially_filled')
        """
        
        metadata_update = json.dumps({"cancel_reason": reason})
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            result = await conn.execute(
                query,
                datetime.now(),
                metadata_update,
                order_ids
            )
            cancelled_count = int(result.split()[-1])
        
        logger.info(f"Cancelled {cancelled_count} orders: {order_ids}")
        return cancelled_count
    
    async def get_order_by_exchange_id(
        self,
        exchange_order_id: str,
        exchange: str
    ) -> Optional[Order]:
        """
        Get order by exchange order ID.
        
        Args:
            exchange_order_id: Exchange order identifier
            exchange: Exchange name
        
        Returns:
            Order if found
        """
        query = """
        SELECT * FROM orders 
        WHERE exchange_order_id = $1 AND exchange = $2
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            record = await conn.fetchrow(query, exchange_order_id, exchange)
            if record:
                return self._from_record(record)
        
        return None
    
    async def get_orders_by_position(
        self,
        position_id: int
    ) -> List[Order]:
        """
        Get all orders related to a position.
        
        Args:
            position_id: Position ID
        
        Returns:
            List of related orders
        """
        query = """
        SELECT * FROM orders 
        WHERE position_id = $1 
        ORDER BY created_at ASC
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query, position_id)
            return [self._from_record(record) for record in records]
    
    async def bulk_update_orders(
        self,
        updates: List[Tuple[int, Dict[str, Any]]]
    ) -> int:
        """
        Bulk update multiple orders efficiently.
        
        Args:
            updates: List of (order_id, update_data) tuples
        
        Returns:
            Number of updated orders
        """
        # Use base repository bulk update
        formatted_updates = [
            ({"id": order_id}, update_data)
            for order_id, update_data in updates
        ]
        
        return await self.bulk_update(formatted_updates)
    
    async def get_order_stats(
        self,
        exchange: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get aggregated order statistics.
        
        Args:
            exchange: Optional exchange filter
            days: Days to analyze
        
        Returns:
            Statistics dictionary
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'filled' THEN 1 ELSE 0 END) as filled_orders,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_orders,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_orders,
            SUM(CASE WHEN side = 'buy' THEN 1 ELSE 0 END) as buy_orders,
            SUM(CASE WHEN side = 'sell' THEN 1 ELSE 0 END) as sell_orders,
            AVG(CASE WHEN executed_at IS NOT NULL AND created_at IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (executed_at - created_at)) END) as avg_execution_time_seconds,
            COUNT(DISTINCT symbol) as unique_symbols
        FROM orders
        WHERE created_at > $1
        """
        
        args = [cutoff_date]
        
        if exchange:
            query += " AND exchange = $2"
            args.append(exchange)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            record = await conn.fetchrow(query, *args)
            
            total_orders = record["total_orders"] or 0
            filled_orders = record["filled_orders"] or 0
            
            return {
                "total_orders": total_orders,
                "filled_orders": filled_orders,
                "cancelled_orders": record["cancelled_orders"] or 0,
                "rejected_orders": record["rejected_orders"] or 0,
                "buy_orders": record["buy_orders"] or 0,
                "sell_orders": record["sell_orders"] or 0,
                "fill_rate": (filled_orders / total_orders * 100) if total_orders > 0 else 0,
                "avg_execution_time_seconds": float(record["avg_execution_time_seconds"]) if record["avg_execution_time_seconds"] else 0,
                "unique_symbols": record["unique_symbols"] or 0,
                "period_days": days
            }
    
    async def cleanup_old_orders(
        self,
        days_to_keep: int = 30,
        keep_filled: bool = True
    ) -> int:
        """
        Clean up old orders to manage database size.
        
        Args:
            days_to_keep: Days of data to retain
            keep_filled: Whether to keep filled orders longer
        
        Returns:
            Number of deleted orders
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        if keep_filled:
            # Only delete cancelled/rejected orders
            query = """
            DELETE FROM orders
            WHERE created_at < $1 
            AND status IN ('cancelled', 'rejected', 'expired')
            """
        else:
            # Delete all old orders except active ones
            query = """
            DELETE FROM orders
            WHERE created_at < $1 
            AND status NOT IN ('pending', 'open', 'partially_filled')
            """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            result = await conn.execute(query, cutoff_date)
            deleted_count = int(result.split()[-1])
        
        logger.info(f"Cleaned up {deleted_count} old orders older than {days_to_keep} days")
        return deleted_count