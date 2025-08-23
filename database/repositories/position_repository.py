"""
Position Repository for centralized position management.

This repository handles all database operations for trading positions,
replacing direct SQL queries in trading/engine.py with transaction-safe operations.
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


class PositionStatus(Enum):
    """Position status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    PARTIALLY_CLOSED = "partially_closed"
    LIQUIDATED = "liquidated"


class PositionSide(Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"


class Position:
    """Position model class."""
    
    def __init__(
        self,
        id: Optional[int] = None,
        symbol: str = None,
        exchange: str = None,
        side: str = None,
        quantity: Decimal = None,
        entry_price: Decimal = None,
        current_price: Optional[Decimal] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        leverage: int = 5,
        status: str = PositionStatus.OPEN.value,
        pnl: Optional[Decimal] = None,
        pnl_percentage: Optional[Decimal] = None,
        opened_at: Optional[datetime] = None,
        closed_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ):
        self.id = id
        self.symbol = symbol
        self.exchange = exchange
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.leverage = leverage
        self.status = status
        self.pnl = pnl
        self.pnl_percentage = pnl_percentage
        self.opened_at = opened_at or datetime.now()
        self.closed_at = closed_at
        self.metadata = metadata or {}


class PositionRepository(BaseRepository[Position]):
    """
    Repository for position database operations.
    
    Features:
    - Atomic position updates with transactions
    - Bulk position management
    - PnL calculation and tracking
    - Position history and analytics
    """
    
    def __init__(self, pool: asyncpg.Pool, transaction_manager: TransactionManager):
        """
        Initialize Position Repository.
        
        Args:
            pool: AsyncPG connection pool
            transaction_manager: Transaction manager for atomic operations
        """
        super().__init__(pool, "positions", Position, transaction_manager)
        
    def _to_dict(self, model: Position) -> Dict[str, Any]:
        """Convert Position to dictionary for database."""
        return {
            "symbol": model.symbol,
            "exchange": model.exchange,
            "side": model.side,
            "quantity": float(model.quantity),
            "entry_price": float(model.entry_price),
            "current_price": float(model.current_price) if model.current_price else None,
            "stop_loss": float(model.stop_loss) if model.stop_loss else None,
            "take_profit": float(model.take_profit) if model.take_profit else None,
            "leverage": model.leverage,
            "status": model.status,
            "pnl": float(model.pnl) if model.pnl else None,
            "pnl_percentage": float(model.pnl_percentage) if model.pnl_percentage else None,
            "opened_at": model.opened_at,
            "closed_at": model.closed_at,
            "metadata": json.dumps(model.metadata) if model.metadata else None
        }
    
    def _from_record(self, record: asyncpg.Record) -> Position:
        """Convert database record to Position."""
        return Position(
            id=record["id"],
            symbol=record["symbol"],
            exchange=record["exchange"],
            side=record["side"],
            quantity=Decimal(str(record["quantity"])),
            entry_price=Decimal(str(record["entry_price"])),
            current_price=Decimal(str(record["current_price"])) if record["current_price"] else None,
            stop_loss=Decimal(str(record["stop_loss"])) if record["stop_loss"] else None,
            take_profit=Decimal(str(record["take_profit"])) if record["take_profit"] else None,
            leverage=record["leverage"],
            status=record["status"],
            pnl=Decimal(str(record["pnl"])) if record["pnl"] else None,
            pnl_percentage=Decimal(str(record["pnl_percentage"])) if record["pnl_percentage"] else None,
            opened_at=record["opened_at"],
            closed_at=record["closed_at"],
            metadata=json.loads(record["metadata"]) if record["metadata"] else {}
        )
    
    async def open_position(
        self,
        position: Position,
        order_id: Optional[int] = None
    ) -> int:
        """
        Open a new position with atomic order linkage.
        
        Args:
            position: Position to open
            order_id: Related order ID
        
        Returns:
            Position ID
        """
        async def create_position(conn):
            query = """
            INSERT INTO positions 
            (symbol, exchange, side, quantity, entry_price, stop_loss, take_profit,
             leverage, status, opened_at, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
            """
            
            data = self._to_dict(position)
            return await conn.fetchval(
                query,
                data["symbol"],
                data["exchange"],
                data["side"],
                data["quantity"],
                data["entry_price"],
                data["stop_loss"],
                data["take_profit"],
                data["leverage"],
                PositionStatus.OPEN.value,
                data["opened_at"],
                data["metadata"]
            )
        
        async def link_order(conn):
            if order_id:
                query = """
                UPDATE orders 
                SET position_id = $1, status = 'filled'
                WHERE id = $2
                """
                await conn.execute(query, position_id, order_id)
        
        # Execute atomically
        async with self.transaction_manager.transaction() as conn:
            position_id = await create_position(conn)
            position.id = position_id
            
            if order_id:
                await conn.execute(
                    "UPDATE orders SET position_id = $1, status = 'filled' WHERE id = $2",
                    position_id, order_id
                )
            
            logger.info(f"Opened position {position_id} for {position.symbol} on {position.exchange}")
            return position_id
    
    async def update_position_price(
        self,
        position_id: int,
        current_price: Decimal,
        calculate_pnl: bool = True
    ) -> Dict[str, Any]:
        """
        Update position's current price and calculate PnL.
        
        Args:
            position_id: Position ID
            current_price: Current market price
            calculate_pnl: Whether to calculate PnL
        
        Returns:
            Updated position data with PnL
        """
        async with self.transaction_manager.transaction() as conn:
            # Get current position
            position_query = """
            SELECT * FROM positions WHERE id = $1 AND status = 'open'
            """
            record = await conn.fetchrow(position_query, position_id)
            
            if not record:
                raise ValueError(f"Position {position_id} not found or not open")
            
            position = self._from_record(record)
            
            # Calculate PnL if requested
            pnl = None
            pnl_percentage = None
            
            if calculate_pnl:
                if position.side == PositionSide.LONG.value:
                    pnl = (current_price - position.entry_price) * position.quantity
                else:  # SHORT
                    pnl = (position.entry_price - current_price) * position.quantity
                
                pnl_percentage = (pnl / (position.entry_price * position.quantity)) * 100
            
            # Update position
            update_query = """
            UPDATE positions 
            SET current_price = $1, pnl = $2, pnl_percentage = $3, updated_at = $4
            WHERE id = $5
            RETURNING *
            """
            
            updated_record = await conn.fetchrow(
                update_query,
                float(current_price),
                float(pnl) if pnl else None,
                float(pnl_percentage) if pnl_percentage else None,
                datetime.now(),
                position_id
            )
            
            return {
                "position_id": position_id,
                "current_price": float(current_price),
                "pnl": float(pnl) if pnl else 0,
                "pnl_percentage": float(pnl_percentage) if pnl_percentage else 0
            }
    
    async def close_position(
        self,
        position_id: int,
        exit_price: Decimal,
        reason: str = "manual"
    ) -> Dict[str, Any]:
        """
        Close a position with final PnL calculation.
        
        Args:
            position_id: Position ID to close
            exit_price: Exit price
            reason: Reason for closing (manual, stop_loss, take_profit, liquidation)
        
        Returns:
            Closing details including final PnL
        """
        async with self.transaction_manager.transaction() as conn:
            # Get position
            position_query = "SELECT * FROM positions WHERE id = $1"
            record = await conn.fetchrow(position_query, position_id)
            
            if not record:
                raise ValueError(f"Position {position_id} not found")
            
            position = self._from_record(record)
            
            # Calculate final PnL
            if position.side == PositionSide.LONG.value:
                final_pnl = (exit_price - position.entry_price) * position.quantity
            else:
                final_pnl = (position.entry_price - exit_price) * position.quantity
            
            final_pnl_percentage = (final_pnl / (position.entry_price * position.quantity)) * 100
            
            # Update position
            update_query = """
            UPDATE positions 
            SET status = $1, current_price = $2, pnl = $3, pnl_percentage = $4,
                closed_at = $5, metadata = metadata || $6
            WHERE id = $7
            RETURNING *
            """
            
            metadata_update = json.dumps({"close_reason": reason})
            
            await conn.execute(
                update_query,
                PositionStatus.CLOSED.value,
                float(exit_price),
                float(final_pnl),
                float(final_pnl_percentage),
                datetime.now(),
                metadata_update,
                position_id
            )
            
            # Update related orders
            await conn.execute(
                "UPDATE orders SET status = 'closed' WHERE position_id = $1",
                position_id
            )
            
            logger.info(
                f"Closed position {position_id}: PnL={final_pnl:.2f} "
                f"({final_pnl_percentage:.2f}%), reason={reason}"
            )
            
            return {
                "position_id": position_id,
                "exit_price": float(exit_price),
                "final_pnl": float(final_pnl),
                "final_pnl_percentage": float(final_pnl_percentage),
                "close_reason": reason
            }
    
    async def get_open_positions(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Position]:
        """
        Get all open positions with optional filters.
        
        Args:
            exchange: Filter by exchange
            symbol: Filter by symbol
        
        Returns:
            List of open positions
        """
        query_parts = ["SELECT * FROM positions WHERE status = 'open'"]
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
        
        query_parts.append("ORDER BY opened_at DESC")
        query = " ".join(query_parts)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query, *args)
            return [self._from_record(record) for record in records]
    
    async def update_positions_batch(
        self,
        updates: List[Tuple[int, Dict[str, Any]]]
    ) -> int:
        """
        Batch update multiple positions efficiently.
        
        Args:
            updates: List of (position_id, update_data) tuples
        
        Returns:
            Number of updated positions
        """
        # Convert to format expected by base repository
        formatted_updates = [
            ({"id": position_id}, update_data)
            for position_id, update_data in updates
        ]
        
        return await self.bulk_update(formatted_updates)
    
    async def check_stop_loss_take_profit(
        self,
        current_prices: Dict[str, Decimal]
    ) -> List[Dict[str, Any]]:
        """
        Check all open positions for SL/TP triggers.
        
        Args:
            current_prices: Dictionary of symbol -> current price
        
        Returns:
            List of triggered positions with action details
        """
        triggered = []
        
        open_positions = await self.get_open_positions()
        
        for position in open_positions:
            if position.symbol not in current_prices:
                continue
            
            current_price = current_prices[position.symbol]
            
            # Check stop loss
            if position.stop_loss:
                if (position.side == PositionSide.LONG.value and 
                    current_price <= position.stop_loss):
                    triggered.append({
                        "position_id": position.id,
                        "action": "stop_loss",
                        "trigger_price": float(position.stop_loss),
                        "current_price": float(current_price)
                    })
                elif (position.side == PositionSide.SHORT.value and 
                      current_price >= position.stop_loss):
                    triggered.append({
                        "position_id": position.id,
                        "action": "stop_loss",
                        "trigger_price": float(position.stop_loss),
                        "current_price": float(current_price)
                    })
            
            # Check take profit
            if position.take_profit:
                if (position.side == PositionSide.LONG.value and 
                    current_price >= position.take_profit):
                    triggered.append({
                        "position_id": position.id,
                        "action": "take_profit",
                        "trigger_price": float(position.take_profit),
                        "current_price": float(current_price)
                    })
                elif (position.side == PositionSide.SHORT.value and 
                      current_price <= position.take_profit):
                    triggered.append({
                        "position_id": position.id,
                        "action": "take_profit",
                        "trigger_price": float(position.take_profit),
                        "current_price": float(current_price)
                    })
        
        return triggered
    
    async def get_position_stats(
        self,
        exchange: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get aggregated position statistics.
        
        Args:
            exchange: Optional exchange filter
            days: Days to analyze
        
        Returns:
            Statistics dictionary
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
        SELECT 
            COUNT(*) as total_positions,
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_positions,
            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_positions,
            AVG(CASE WHEN status = 'closed' THEN pnl END) as avg_pnl,
            SUM(CASE WHEN status = 'closed' THEN pnl END) as total_pnl,
            AVG(CASE WHEN status = 'closed' THEN pnl_percentage END) as avg_pnl_percentage,
            SUM(CASE WHEN status = 'closed' AND pnl > 0 THEN 1 ELSE 0 END) as profitable_positions,
            SUM(CASE WHEN status = 'closed' AND pnl <= 0 THEN 1 ELSE 0 END) as losing_positions,
            AVG(leverage) as avg_leverage
        FROM positions
        WHERE opened_at > $1
        """
        
        args = [cutoff_date]
        
        if exchange:
            query += " AND exchange = $2"
            args.append(exchange)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            record = await conn.fetchrow(query, *args)
            
            total_closed = (record["profitable_positions"] or 0) + (record["losing_positions"] or 0)
            win_rate = 0
            if total_closed > 0:
                win_rate = (record["profitable_positions"] / total_closed) * 100
            
            return {
                "total_positions": record["total_positions"] or 0,
                "open_positions": record["open_positions"] or 0,
                "closed_positions": record["closed_positions"] or 0,
                "avg_pnl": float(record["avg_pnl"]) if record["avg_pnl"] else 0,
                "total_pnl": float(record["total_pnl"]) if record["total_pnl"] else 0,
                "avg_pnl_percentage": float(record["avg_pnl_percentage"]) if record["avg_pnl_percentage"] else 0,
                "profitable_positions": record["profitable_positions"] or 0,
                "losing_positions": record["losing_positions"] or 0,
                "win_rate": win_rate,
                "avg_leverage": float(record["avg_leverage"]) if record["avg_leverage"] else 5,
                "period_days": days
            }
    
    async def fix_all_leverage(self, target_leverage: int = 5) -> int:
        """
        Fix leverage for all open positions.
        
        Args:
            target_leverage: Target leverage value
        
        Returns:
            Number of updated positions
        """
        query = """
        UPDATE positions 
        SET leverage = $1 
        WHERE status = 'open' AND leverage != $1
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            result = await conn.execute(query, target_leverage)
            updated = int(result.split()[-1])
            
        if updated > 0:
            logger.info(f"Fixed leverage to {target_leverage}x for {updated} positions")
        
        return updated