#!/usr/bin/env python3
"""
Мониторинг баланса LONG/SHORT сигналов в реальном времени
"""

import asyncio
import sys
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select

from core.logger import setup_logger
from database.connections import get_async_db
from database.models.base_models import SignalType
from database.models.signal import Signal

logger = setup_logger("signal_balance_monitor")


async def monitor_signal_balance():
    """
    Мониторит баланс сигналов и выводит статистику
    """
    logger.info("=" * 60)
    logger.info("📊 МОНИТОРИНГ БАЛАНСА СИГНАЛОВ")
    logger.info("=" * 60)

    # Анализируем сигналы за последний час
    time_window = datetime.utcnow() - timedelta(hours=1)

    async with get_async_db() as db:
        # Общее количество сигналов
        total_query = select(func.count(Signal.id)).where(
            Signal.created_at >= time_window
        )
        total_result = await db.execute(total_query)
        total_signals = total_result.scalar()

        if total_signals == 0:
            logger.warning("⚠️ Нет сигналов за последний час")
            return

        # Количество LONG сигналов
        long_query = select(func.count(Signal.id)).where(
            and_(
                Signal.created_at >= time_window, Signal.signal_type == SignalType.LONG
            )
        )
        long_result = await db.execute(long_query)
        long_signals = long_result.scalar()

        # Количество SHORT сигналов
        short_query = select(func.count(Signal.id)).where(
            and_(
                Signal.created_at >= time_window, Signal.signal_type == SignalType.SHORT
            )
        )
        short_result = await db.execute(short_query)
        short_signals = short_result.scalar()

        # Расчет процентов
        long_pct = (long_signals / total_signals) * 100
        short_pct = (short_signals / total_signals) * 100

        # Вывод статистики
        logger.info("📈 Сигналы за последний час:")
        logger.info(f"   Всего:  {total_signals}")
        logger.info(f"   LONG:   {long_signals} ({long_pct:.1f}%)")
        logger.info(f"   SHORT:  {short_signals} ({short_pct:.1f}%)")

        # Анализ баланса
        logger.info("")
        if long_pct == 100:
            logger.critical("🚨 КРИТИЧЕСКИЙ ДИСБАЛАНС: 100% LONG сигналов!")
            logger.critical("   Рекомендуется НЕМЕДЛЕННО остановить торговлю!")
        elif short_pct == 100:
            logger.critical("🚨 КРИТИЧЕСКИЙ ДИСБАЛАНС: 100% SHORT сигналов!")
            logger.critical("   Рекомендуется НЕМЕДЛЕННО остановить торговлю!")
        elif long_pct > 80:
            logger.warning("⚠️ ПРЕДУПРЕЖДЕНИЕ: Дисбаланс в сторону LONG")
            logger.warning(f"   {long_pct:.1f}% LONG vs {short_pct:.1f}% SHORT")
        elif short_pct > 80:
            logger.warning("⚠️ ПРЕДУПРЕЖДЕНИЕ: Дисбаланс в сторону SHORT")
            logger.warning(f"   {short_pct:.1f}% SHORT vs {long_pct:.1f}% LONG")
        elif 30 <= long_pct <= 70 and 30 <= short_pct <= 70:
            logger.info("✅ ОТЛИЧНО: Сигналы хорошо сбалансированы")
            logger.info("   Идеальный баланс для торговли в обе стороны")
        else:
            logger.info("✅ НОРМАЛЬНО: Баланс сигналов в пределах нормы")

        # Детальная статистика по символам
        logger.info("")
        logger.info("📊 Статистика по символам:")

        symbols_query = (
            select(
                Signal.symbol, Signal.signal_type, func.count(Signal.id).label("count")
            )
            .where(Signal.created_at >= time_window)
            .group_by(Signal.symbol, Signal.signal_type)
        )

        symbols_result = await db.execute(symbols_query)
        symbols_data = symbols_result.all()

        # Группируем по символам
        symbol_stats = {}
        for row in symbols_data:
            symbol = row.symbol
            signal_type = row.signal_type
            count = row.count

            if symbol not in symbol_stats:
                symbol_stats[symbol] = {"LONG": 0, "SHORT": 0}

            if signal_type == SignalType.LONG:
                symbol_stats[symbol]["LONG"] = count
            elif signal_type == SignalType.SHORT:
                symbol_stats[symbol]["SHORT"] = count

        # Выводим статистику по символам
        for symbol, stats in sorted(symbol_stats.items()):
            total = stats["LONG"] + stats["SHORT"]
            if total > 0:
                long_pct = (stats["LONG"] / total) * 100
                short_pct = (stats["SHORT"] / total) * 100

                # Эмодзи для визуализации баланса
                if long_pct > 70:
                    emoji = "📈"  # Сильный LONG bias
                elif short_pct > 70:
                    emoji = "📉"  # Сильный SHORT bias
                else:
                    emoji = "⚖️"  # Сбалансировано

                logger.info(
                    f"   {emoji} {symbol:10s}: "
                    f"L:{stats['LONG']:3d} ({long_pct:5.1f}%) / "
                    f"S:{stats['SHORT']:3d} ({short_pct:5.1f}%)"
                )

        # Средние показатели confidence и strength
        avg_query = (
            select(
                Signal.signal_type,
                func.avg(Signal.confidence).label("avg_confidence"),
                func.avg(Signal.strength).label("avg_strength"),
            )
            .where(Signal.created_at >= time_window)
            .group_by(Signal.signal_type)
        )

        avg_result = await db.execute(avg_query)
        avg_data = avg_result.all()

        logger.info("")
        logger.info("📊 Средние показатели:")
        for row in avg_data:
            signal_type = "LONG" if row.signal_type == SignalType.LONG else "SHORT"
            logger.info(
                f"   {signal_type}: "
                f"Confidence: {row.avg_confidence:.3f}, "
                f"Strength: {row.avg_strength:.3f}"
            )


async def continuous_monitoring(interval_seconds=60):
    """
    Непрерывный мониторинг с заданным интервалом

    Args:
        interval_seconds: Интервал между проверками в секундах
    """
    logger.info(f"🚀 Запуск непрерывного мониторинга (интервал: {interval_seconds}с)")
    logger.info("Нажмите Ctrl+C для остановки")

    try:
        while True:
            await monitor_signal_balance()
            logger.info(f"\n⏰ Следующая проверка через {interval_seconds} секунд...\n")
            await asyncio.sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info("\n✋ Мониторинг остановлен пользователем")


if __name__ == "__main__":
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        # Непрерывный мониторинг
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        asyncio.run(continuous_monitoring(interval))
    else:
        # Однократная проверка
        asyncio.run(monitor_signal_balance())
