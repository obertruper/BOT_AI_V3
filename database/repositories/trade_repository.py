"""
Enhanced Trade Repository with bulk operations and performance optimizations.

This repository handles all database operations for completed trades,
with optimized analytics and bulk processing capabilities.
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


class TradeStatus(Enum):
    """Trade status enumeration."""
    PENDING = "pending"
    EXECUTED = "executed"
    PARTIALLY_EXECUTED = "partially_executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TradeSide(Enum):
    """Trade side enumeration."""
    BUY = "buy"
    SELL = "sell"


class Trade:
    """Trade model class."""
    
    def __init__(
        self,
        id: Optional[int] = None,
        order_id: Optional[int] = None,
        symbol: str = None,
        exchange: str = None,
        side: str = None,
        quantity: Decimal = None,
        price: Decimal = None,
        fee: Decimal = Decimal('0'),
        fee_currency: str = "USDT",
        realized_pnl: Optional[Decimal] = None,
        commission: Decimal = Decimal('0'),
        exchange_trade_id: Optional[str] = None,
        status: str = TradeStatus.EXECUTED.value,
        executed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ):
        self.id = id
        self.order_id = order_id
        self.symbol = symbol
        self.exchange = exchange
        self.side = side
        self.quantity = quantity
        self.price = price
        self.fee = fee
        self.fee_currency = fee_currency
        self.realized_pnl = realized_pnl
        self.commission = commission
        self.exchange_trade_id = exchange_trade_id
        self.status = status
        self.executed_at = executed_at or datetime.now()
        self.created_at = created_at or datetime.now()
        self.metadata = metadata or {}

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost including fees."""
        return (self.quantity * self.price) + self.fee + self.commission

    @property
    def net_pnl(self) -> Decimal:
        """Calculate net PnL after fees."""
        if self.realized_pnl:
            return self.realized_pnl - self.fee - self.commission
        return Decimal('0')


class TradeRepository(BaseRepository[Trade]):
    """
    Repository for trade database operations.
    
    Features:
    - High-performance trade recording
    - Bulk trade processing
    - Advanced analytics and reporting
    - PnL calculation and tracking
    """
    
    def __init__(self, pool: asyncpg.Pool, transaction_manager: TransactionManager = None):
        """
        Initialize Trade Repository.
        
        Args:
            pool: AsyncPG connection pool  
            transaction_manager: Transaction manager for atomic operations
        """
        super().__init__(pool, "trades", Trade, transaction_manager)
        
    def _to_dict(self, model: Trade) -> Dict[str, Any]:
        """Convert Trade to dictionary for database."""
        return {
            "order_id": model.order_id,
            "symbol": model.symbol,
            "exchange": model.exchange,
            "side": model.side,
            "quantity": float(model.quantity),
            "price": float(model.price),
            "fee": float(model.fee),
            "fee_currency": model.fee_currency,
            "realized_pnl": float(model.realized_pnl) if model.realized_pnl else None,
            "commission": float(model.commission),
            "exchange_trade_id": model.exchange_trade_id,
            "status": model.status,
            "executed_at": model.executed_at,
            "created_at": model.created_at,
            "metadata": json.dumps(model.metadata) if model.metadata else None
        }
    
    def _from_record(self, record: asyncpg.Record) -> Trade:
        """Convert database record to Trade."""
        return Trade(
            id=record["id"],
            order_id=record["order_id"],
            symbol=record["symbol"],
            exchange=record["exchange"],
            side=record["side"],
            quantity=Decimal(str(record["quantity"])),
            price=Decimal(str(record["price"])),
            fee=Decimal(str(record["fee"])),
            fee_currency=record["fee_currency"],
            realized_pnl=Decimal(str(record["realized_pnl"])) if record["realized_pnl"] else None,
            commission=Decimal(str(record["commission"])),
            exchange_trade_id=record["exchange_trade_id"],
            status=record["status"],
            executed_at=record["executed_at"],
            created_at=record["created_at"],
            metadata=json.loads(record["metadata"]) if record["metadata"] else {}
        )
    
    async def create_trade(self, trade: Trade) -> int:
        """
        Create a new trade record.
        
        Args:
            trade: Trade to create
        
        Returns:
            Trade ID
        """
        query = """
        INSERT INTO trades 
        (order_id, symbol, exchange, side, quantity, price, fee, fee_currency,
         realized_pnl, commission, exchange_trade_id, status, executed_at, created_at, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING id
        """
        
        data = self._to_dict(trade)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            trade_id = await conn.fetchval(
                query,
                data["order_id"],
                data["symbol"],
                data["exchange"],
                data["side"],
                data["quantity"],
                data["price"],
                data["fee"],
                data["fee_currency"],
                data["realized_pnl"],
                data["commission"],
                data["exchange_trade_id"],
                data["status"],
                data["executed_at"],
                data["created_at"],
                data["metadata"]
            )
        
        trade.id = trade_id
        logger.info(f"Created trade {trade_id} for {trade.symbol} {trade.side} {trade.quantity}")
        return trade_id
    
    async def get_trading_stats(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive trading statistics.
        
        Args:
            exchange: Filter by exchange
            symbol: Filter by symbol
            start_date: Start date filter
            end_date: End date filter
        
        Returns:
            Trading statistics dictionary
        """
        # Build WHERE clause
        where_conditions = ["status = 'executed'"]
        args = []
        param_counter = 1
        
        if exchange:
            where_conditions.append(f"exchange = ${param_counter}")
            args.append(exchange)
            param_counter += 1
        
        if symbol:
            where_conditions.append(f"symbol = ${param_counter}")
            args.append(symbol)
            param_counter += 1
        
        if start_date:
            where_conditions.append(f"executed_at >= ${param_counter}")
            args.append(start_date)
            param_counter += 1
        
        if end_date:
            where_conditions.append(f"executed_at <= ${param_counter}")
            args.append(end_date)
            param_counter += 1
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            COUNT(*) as total_trades,
            SUM(quantity * price) as total_volume,
            SUM(realized_pnl) as total_pnl,
            AVG(realized_pnl) as avg_pnl,
            SUM(fee + commission) as total_fees,
            SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
            MAX(realized_pnl) as best_trade,
            MIN(realized_pnl) as worst_trade,
            COUNT(DISTINCT symbol) as unique_symbols,
            SUM(CASE WHEN side = 'buy' THEN 1 ELSE 0 END) as buy_trades,
            SUM(CASE WHEN side = 'sell' THEN 1 ELSE 0 END) as sell_trades
        FROM trades
        WHERE {where_clause}
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            record = await conn.fetchrow(query, *args)
            
            total_trades = record["total_trades"] or 0
            winning_trades = record["winning_trades"] or 0
            losing_trades = record["losing_trades"] or 0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "total_volume": float(record["total_volume"]) if record["total_volume"] else 0,
                "total_pnl": float(record["total_pnl"]) if record["total_pnl"] else 0,
                "avg_pnl": float(record["avg_pnl"]) if record["avg_pnl"] else 0,
                "total_fees": float(record["total_fees"]) if record["total_fees"] else 0,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "best_trade": float(record["best_trade"]) if record["best_trade"] else 0,
                "worst_trade": float(record["worst_trade"]) if record["worst_trade"] else 0,
                "unique_symbols": record["unique_symbols"] or 0,
                "buy_trades": record["buy_trades"] or 0,
                "sell_trades": record["sell_trades"] or 0
            }
    
    async def get_recent_trades(
        self,
        limit: int = 50,
        exchange: Optional[str] = None
    ) -> List[Trade]:
        """
        Get recent trades.
        
        Args:
            limit: Maximum number of trades
            exchange: Filter by exchange
        
        Returns:
            List of recent trades
        """
        query_parts = ["SELECT * FROM trades WHERE status = 'executed'"]
        args = []
        param_counter = 1
        
        if exchange:
            query_parts.append(f"AND exchange = ${param_counter}")
            args.append(exchange)
            param_counter += 1
        
        query_parts.extend([
            "ORDER BY executed_at DESC",
            f"LIMIT {limit}"
        ])
        
        query = " ".join(query_parts)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query, *args)
            return [self._from_record(record) for record in records]
    
    async def get_daily_pnl(
        self,
        days: int = 30,
        exchange: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily PnL breakdown.
        
        Args:
            days: Number of days to analyze
            exchange: Filter by exchange
        
        Returns:
            List of daily PnL data
        """
        where_conditions = ["status = 'executed'", f"executed_at >= NOW() - INTERVAL '{days} days'"]
        args = []
        param_counter = 1
        
        if exchange:
            where_conditions.append(f"exchange = ${param_counter}")
            args.append(exchange)
            param_counter += 1
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            DATE(executed_at) as trade_date,
            COUNT(*) as trades_count,
            SUM(realized_pnl) as daily_pnl,
            SUM(quantity * price) as daily_volume,
            SUM(fee + commission) as daily_fees
        FROM trades
        WHERE {where_clause}
        GROUP BY DATE(executed_at)
        ORDER BY trade_date DESC
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query, *args)
            
            return [
                {
                    "date": record["trade_date"].isoformat(),
                    "trades_count": record["trades_count"],
                    "daily_pnl": float(record["daily_pnl"]) if record["daily_pnl"] else 0,
                    "daily_volume": float(record["daily_volume"]) if record["daily_volume"] else 0,
                    "daily_fees": float(record["daily_fees"]) if record["daily_fees"] else 0
                }
                for record in records
            ]
    
    async def get_symbol_performance(
        self,
        limit: int = 20,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get performance by symbol.
        
        Args:
            limit: Maximum symbols to return
            days: Days to analyze
        
        Returns:
            List of symbol performance data
        """
        query = """
        SELECT 
            symbol,
            COUNT(*) as trades_count,
            SUM(realized_pnl) as total_pnl,
            AVG(realized_pnl) as avg_pnl,
            SUM(quantity * price) as total_volume,
            SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades
        FROM trades
        WHERE status = 'executed' 
        AND executed_at >= NOW() - INTERVAL '%s days'
        GROUP BY symbol
        HAVING COUNT(*) > 0
        ORDER BY total_pnl DESC
        LIMIT %s
        """ % (days, limit)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query)
            
            return [
                {
                    "symbol": record["symbol"],
                    "trades_count": record["trades_count"],
                    "total_pnl": float(record["total_pnl"]) if record["total_pnl"] else 0,
                    "avg_pnl": float(record["avg_pnl"]) if record["avg_pnl"] else 0,
                    "total_volume": float(record["total_volume"]) if record["total_volume"] else 0,
                    "winning_trades": record["winning_trades"],
                    "win_rate": (record["winning_trades"] / record["trades_count"] * 100) if record["trades_count"] > 0 else 0
                }
                for record in records
            ]
    
    async def cleanup_old_trades(self, days_to_keep: int = 90) -> int:
        """
        Clean up old trade records.
        
        Args:
            days_to_keep: Days of data to retain
        
        Returns:
            Number of deleted trades
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        query = """
        DELETE FROM trades
        WHERE executed_at < $1 
        AND status IN ('cancelled', 'failed')
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            result = await conn.execute(query, cutoff_date)
            deleted_count = int(result.split()[-1])
        
        logger.info(f"Cleaned up {deleted_count} old trades older than {days_to_keep} days")
        return deleted_count
