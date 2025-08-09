#!/usr/bin/env python3
"""Мониторинг ML сигналов и торговли"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta

from dotenv import load_dotenv
from sqlalchemy import desc, select

from core.logger import setup_logger
from database.connections import get_async_db
from database.models.base_models import Order, Trade
from database.models.signal import Signal

logger = setup_logger("monitor")


async def monitor_signals():
    """Мониторинг сигналов и ордеров"""
    load_dotenv()

    logger.info("🔍 Мониторинг ML торговли запущен...")

    while True:
        try:
            async with get_async_db() as db:
                # Последние сигналы
                result = await db.execute(
                    select(Signal)
                    .where(Signal.created_at > datetime.utcnow() - timedelta(minutes=5))
                    .order_by(desc(Signal.created_at))
                    .limit(10)
                )
                signals = result.scalars().all()

                if signals:
                    logger.info(f"\n📡 Последние {len(signals)} сигналов:")
                    for sig in signals:
                        logger.info(
                            f"  {sig.symbol}: {sig.signal_type} "
                            f"(сила: {sig.strength:.2f}, уверенность: {sig.confidence:.2f}) "
                            f"- {sig.created_at.strftime('%H:%M:%S')}"
                        )

                # Последние ордера
                result = await db.execute(
                    select(Order)
                    .where(Order.created_at > datetime.utcnow() - timedelta(minutes=5))
                    .order_by(desc(Order.created_at))
                    .limit(10)
                )
                orders = result.scalars().all()

                if orders:
                    logger.info(f"\n📦 Последние {len(orders)} ордеров:")
                    for order in orders:
                        logger.info(
                            f"  {order.symbol}: {order.side} {order.quantity} "
                            f"@ {order.price or 'MARKET'} - {order.status} "
                            f"- {order.created_at.strftime('%H:%M:%S')}"
                        )

                # Последние сделки
                result = await db.execute(
                    select(Trade)
                    .where(Trade.executed_at > datetime.utcnow() - timedelta(minutes=5))
                    .order_by(desc(Trade.executed_at))
                    .limit(10)
                )
                trades = result.scalars().all()

                if trades:
                    logger.info(f"\n💰 Последние {len(trades)} сделок:")
                    for trade in trades:
                        pnl_str = (
                            f"+${trade.realized_pnl:.2f}"
                            if trade.realized_pnl > 0
                            else f"-${abs(trade.realized_pnl):.2f}"
                        )
                        logger.info(
                            f"  {trade.symbol}: {trade.side} {trade.quantity} "
                            f"@ {trade.price} - PnL: {pnl_str} "
                            f"- {trade.executed_at.strftime('%H:%M:%S')}"
                        )

                if not signals and not orders and not trades:
                    logger.info("⏳ Ожидание активности...")

        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга: {e}")

        await asyncio.sleep(30)  # Проверка каждые 30 секунд


if __name__ == "__main__":
    asyncio.run(monitor_signals())
