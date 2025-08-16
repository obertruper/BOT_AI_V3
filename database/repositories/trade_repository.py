"""
Репозиторий для работы с торговыми операциями
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError
from database.models.base_models import Trade


class TradeRepository:
    """Репозиторий для работы с торговыми операциями"""

    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def create_trade(self, trade_data: dict[str, Any]) -> Trade:
        """Создает новую торговую операцию"""
        try:
            trade = Trade(**trade_data)
            self.session.add(trade)
            await self.session.commit()
            await self.session.refresh(trade)
            return trade
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create trade: {e}")

    async def get_trading_stats(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """Получает статистику торговли"""
        try:
            query = select(
                func.count(Trade.id).label("total_trades"),
                func.sum(Trade.realized_pnl).label("total_profit"),
                func.sum(Trade.quantity * Trade.price).label("total_volume"),
                func.avg(Trade.realized_pnl).label("avg_profit"),
            )

            if start_date:
                query = query.where(Trade.created_at >= start_date)
            if end_date:
                query = query.where(Trade.created_at <= end_date)

            result = await self.session.execute(query)
            row = result.first()

            if not row:
                return {
                    "total_trades": 0,
                    "total_profit": Decimal("0"),
                    "total_volume": Decimal("0"),
                    "avg_profit": Decimal("0"),
                    "win_rate": 0.0,
                }

            # Подсчитываем win rate
            win_query = select(func.count(Trade.id)).where(Trade.realized_pnl > 0)
            if start_date:
                win_query = win_query.where(Trade.created_at >= start_date)
            if end_date:
                win_query = win_query.where(Trade.created_at <= end_date)

            win_result = await self.session.execute(win_query)
            win_count = win_result.scalar() or 0

            total_trades = row.total_trades or 0
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

            return {
                "total_trades": total_trades,
                "total_profit": row.total_profit or Decimal("0"),
                "total_volume": row.total_volume or Decimal("0"),
                "avg_profit": row.avg_profit or Decimal("0"),
                "win_rate": win_rate,
            }

        except Exception as e:
            raise DatabaseError(f"Failed to get trading stats: {e}")
