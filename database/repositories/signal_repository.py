"""
Signal Repository with asyncpg-based operations.

This repository handles all database operations for trading signals,
with optimized performance and bulk processing capabilities.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import asyncpg
import json
from loguru import logger
from enum import Enum

from database.repositories.base_repository import BaseRepository
from database.connections.transaction_manager import TransactionManager
from database.models.signal import Signal
from database.models.base_models import SignalType


class SignalRepository(BaseRepository[Signal]):
    """
    Repository for signal database operations.
    
    Features:
    - High-performance signal recording
    - Bulk signal processing
    - Signal status management
    - Historical signal analytics
    """
    
    def __init__(self, pool: asyncpg.Pool, transaction_manager: TransactionManager = None):
        """
        Initialize Signal Repository.
        
        Args:
            pool: AsyncPG connection pool  
            transaction_manager: Transaction manager for atomic operations
        """
        super().__init__(pool, "signals", Signal, transaction_manager)

    def _to_dict(self, model: Signal) -> Dict[str, Any]:
        """Convert Signal to dictionary for database."""
        return {
            "symbol": model.symbol,
            "exchange": model.exchange,
            "signal_type": model.signal_type.value if isinstance(model.signal_type, SignalType) else model.signal_type,
            "strength": float(model.strength) if model.strength else None,
            "confidence": float(model.confidence) if model.confidence else None,
            "suggested_price": float(model.suggested_price) if model.suggested_price else None,
            "suggested_stop_loss": float(model.suggested_stop_loss) if model.suggested_stop_loss else None,
            "suggested_take_profit": float(model.suggested_take_profit) if model.suggested_take_profit else None,
            "suggested_quantity": float(model.suggested_quantity) if model.suggested_quantity else None,
            "strategy_name": model.strategy_name,
            "timeframe": model.timeframe,
            "expires_at": model.expires_at,
            "indicators": json.dumps(model.indicators) if model.indicators else None,
            "extra_data": json.dumps(model.extra_data) if model.extra_data else None,
            "metadata": json.dumps(model.signal_metadata) if model.signal_metadata else None,
            "status": getattr(model, 'status', 'active'),
            "processed_at": getattr(model, 'processed_at', None),
            "created_at": model.created_at,
            "updated_at": model.updated_at
        }
    
    def _from_record(self, record: asyncpg.Record) -> Signal:
        """Convert database record to SQLAlchemy Signal model."""
        signal = Signal()
        signal.id = record["id"]
        signal.symbol = record["symbol"]
        signal.exchange = record["exchange"]
        signal.signal_type = record["signal_type"]
        signal.strength = float(record["strength"]) if record["strength"] else None
        signal.confidence = float(record["confidence"]) if record["confidence"] else None
        signal.suggested_price = Decimal(str(record["suggested_price"])) if record["suggested_price"] else None
        signal.suggested_stop_loss = Decimal(str(record["suggested_stop_loss"])) if record["suggested_stop_loss"] else None
        signal.suggested_take_profit = Decimal(str(record["suggested_take_profit"])) if record["suggested_take_profit"] else None
        signal.suggested_quantity = Decimal(str(record["suggested_quantity"])) if record["suggested_quantity"] else None
        signal.strategy_name = record["strategy_name"]
        signal.timeframe = record["timeframe"]
        signal.expires_at = record["expires_at"]
        signal.indicators = json.loads(record["indicators"]) if record["indicators"] else {}
        signal.extra_data = json.loads(record["extra_data"]) if record["extra_data"] else {}
        signal.signal_metadata = json.loads(record["metadata"]) if record["metadata"] else {}
        signal.status = record.get("status", "active")
        signal.processed_at = record.get("processed_at")
        signal.created_at = record["created_at"]
        signal.updated_at = record["updated_at"]
        return signal
    
    async def get_active_signals(self, exchange: Optional[str] = None) -> List[Signal]:
        """Get active signals with optional exchange filter."""
        where_conditions = ["status = 'active'"]
        args = []
        param_counter = 1
        
        if exchange:
            where_conditions.append(f"exchange = ${param_counter}")
            args.append(exchange)
            param_counter += 1
        
        # Also check expiration
        where_conditions.append("(expires_at IS NULL OR expires_at > NOW())")
        
        where_clause = " AND ".join(where_conditions)
        query = f"SELECT * FROM signals WHERE {where_clause} ORDER BY created_at DESC"
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query, *args)
            return [self._from_record(record) for record in records]

    async def create_signal(self, signal: Signal) -> int:
        """
        Create a new signal record.
        
        Args:
            signal: Signal to create
        
        Returns:
            Signal ID
        """
        query = """
        INSERT INTO signals 
        (symbol, exchange, signal_type, strength, confidence, suggested_price,
         suggested_stop_loss, suggested_take_profit, suggested_quantity,
         strategy_name, timeframe, expires_at, indicators, extra_data,
         metadata, status, processed_at, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
        RETURNING id
        """
        
        data = self._to_dict(signal)
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            signal_id = await conn.fetchval(
                query,
                data["symbol"],
                data["exchange"],
                data["signal_type"],
                data["strength"],
                data["confidence"],
                data["suggested_price"],
                data["suggested_stop_loss"],
                data["suggested_take_profit"],
                data["suggested_quantity"],
                data["strategy_name"],
                data["timeframe"],
                data["expires_at"],
                data["indicators"],
                data["extra_data"],
                data["metadata"],
                data["status"],
                data["processed_at"],
                data["created_at"],
                data["updated_at"]
            )
        
        signal.id = signal_id
        logger.info(f"Created signal {signal_id} for {signal.symbol} {signal.signal_type} strength={signal.strength}")
        return signal_id

    async def mark_signal_processed(self, signal_id: int, processed_at: Optional[datetime] = None) -> bool:
        """
        Mark signal as processed.
        
        Args:
            signal_id: Signal ID to mark as processed
            processed_at: Processing timestamp (defaults to now)
        
        Returns:
            True if signal was updated, False if not found
        """
        if processed_at is None:
            processed_at = datetime.now()
        
        query = """
        UPDATE signals 
        SET status = 'processed', processed_at = $2, updated_at = $3
        WHERE id = $1 AND status != 'processed'
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            result = await conn.execute(query, signal_id, processed_at, datetime.now())
            updated_count = int(result.split()[-1])
        
        if updated_count > 0:
            logger.info(f"Marked signal {signal_id} as processed")
            return True
        else:
            logger.warning(f"Signal {signal_id} not found or already processed")
            return False

    async def save_signal(self, signal) -> None:
        """Save signal to database (V2 compatibility)."""
        if isinstance(signal, Signal):
            await self.create_signal(signal)
        elif isinstance(signal, dict):
            # Convert dict to Signal object
            signal_obj = Signal(**signal)
            await self.create_signal(signal_obj)
        elif hasattr(signal, "__dict__"):
            # Convert object with attributes to Signal
            signal_dict = {}
            for key, value in signal.__dict__.items():
                if not key.startswith("_"):
                    # Special handling for enum signal_type
                    if key == "signal_type" and hasattr(value, "value"):
                        signal_dict[key] = value.value.upper()
                    else:
                        signal_dict[key] = value
            signal_obj = Signal(**signal_dict)
            await self.create_signal(signal_obj)
        else:
            raise ValueError(f"Unsupported signal type: {type(signal)}")
    
    async def get_recent_signals(
        self,
        limit: int = 50,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Signal]:
        """
        Get recent signals with filtering.
        
        Args:
            limit: Maximum number of signals
            exchange: Filter by exchange
            symbol: Filter by symbol
            status: Filter by status
        
        Returns:
            List of recent signals
        """
        where_conditions = []
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
        
        if status:
            where_conditions.append(f"status = ${param_counter}")
            args.append(status)
            param_counter += 1
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        query = f"SELECT * FROM signals WHERE {where_clause} ORDER BY created_at DESC LIMIT {limit}"
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            records = await conn.fetch(query, *args)
            return [self._from_record(record) for record in records]
    
    async def get_signal_stats(
        self,
        exchange: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get signal statistics.
        
        Args:
            exchange: Filter by exchange
            days: Days to analyze
        
        Returns:
            Signal statistics dictionary
        """
        where_conditions = [f"created_at >= NOW() - INTERVAL '{days} days'"]
        args = []
        param_counter = 1
        
        if exchange:
            where_conditions.append(f"exchange = ${param_counter}")
            args.append(exchange)
            param_counter += 1
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            COUNT(*) as total_signals,
            SUM(CASE WHEN status = 'processed' THEN 1 ELSE 0 END) as processed_signals,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_signals,
            SUM(CASE WHEN signal_type = 'long' THEN 1 ELSE 0 END) as long_signals,
            SUM(CASE WHEN signal_type = 'short' THEN 1 ELSE 0 END) as short_signals,
            AVG(strength) as avg_strength,
            AVG(confidence) as avg_confidence,
            COUNT(DISTINCT symbol) as unique_symbols
        FROM signals
        WHERE {where_clause}
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            record = await conn.fetchrow(query, *args)
            
            total_signals = record["total_signals"] or 0
            processed_signals = record["processed_signals"] or 0
            
            processing_rate = (processed_signals / total_signals * 100) if total_signals > 0 else 0
            
            return {
                "total_signals": total_signals,
                "processed_signals": processed_signals,
                "active_signals": record["active_signals"] or 0,
                "processing_rate": processing_rate,
                "long_signals": record["long_signals"] or 0,
                "short_signals": record["short_signals"] or 0,
                "avg_strength": float(record["avg_strength"]) if record["avg_strength"] else 0,
                "avg_confidence": float(record["avg_confidence"]) if record["avg_confidence"] else 0,
                "unique_symbols": record["unique_symbols"] or 0
            }
    
    async def cleanup_expired_signals(self) -> int:
        """
        Clean up expired signals.
        
        Returns:
            Number of cleaned up signals
        """
        query = """
        UPDATE signals
        SET status = 'expired', updated_at = NOW()
        WHERE expires_at < NOW() AND status = 'active'
        """
        
        async with (self.transaction_manager.transaction() if self.transaction_manager else self.pool.acquire()) as conn:
            result = await conn.execute(query)
            expired_count = int(result.split()[-1])
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired signals")
        
        return expired_count
