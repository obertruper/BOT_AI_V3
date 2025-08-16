#!/usr/bin/env python3
"""
Упрощенный анализ работы бота
"""

import asyncio
from datetime import datetime

from sqlalchemy import text

from database.connections import get_async_db


async def analyze():
    print("=" * 80)
    print("📊 АНАЛИЗ РАБОТЫ БОТА BOT_AI_V3")
    print("=" * 80)

    async with get_async_db() as db:
        # 1. ГЛАВНАЯ ПРОБЛЕМА - НЕТ SHORT СИГНАЛОВ!
        print("\n🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА:")
        result = await db.execute(
            text(
                """
            SELECT signal_type, COUNT(*) as count
            FROM signals
            WHERE created_at >= NOW() - INTERVAL '18 hours'
            GROUP BY signal_type
        """
            )
        )
        signals = result.fetchall()

        has_short = False
        for s in signals:
            print(f"  {s.signal_type.upper()}: {s.count} сигналов")
            if s.signal_type.lower() == "short":
                has_short = True

        if not has_short:
            print("  ⚠️ НЕТ SHORT СИГНАЛОВ! БОТ ТОРГУЕТ ТОЛЬКО В LONG!")
            print("  📌 Это критично на падающем рынке!")

        # 2. Текущие позиции на Bybit (реальные)
        print("\n📊 ТЕКУЩИЕ ПОЗИЦИИ НА BYBIT:")
        result = await db.execute(
            text(
                """
            SELECT
                symbol,
                side,
                size,
                entry_price,
                unrealized_pnl,
                created_at
            FROM positions
            WHERE status = 'open'
            ORDER BY created_at DESC
        """
            )
        )
        positions = result.fetchall()

        if positions:
            total_pnl = 0
            long_count = 0
            short_count = 0

            for p in positions:
                pnl = p.unrealized_pnl or 0
                total_pnl += pnl
                age_hours = (datetime.utcnow() - p.created_at).total_seconds() / 3600

                if p.side.upper() == "LONG":
                    long_count += 1
                else:
                    short_count += 1

                pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"${pnl:.2f}"
                print(
                    f"  {p.symbol} {p.side}: size={p.size}, PnL={pnl_str}, возраст={age_hours:.1f}ч"
                )

            print("\n  📈 ИТОГО:")
            print(f"     LONG позиций: {long_count}")
            print(f"     SHORT позиций: {short_count}")
            print(f"     Нереализованный PnL: ${total_pnl:.2f}")
        else:
            print("  Нет открытых позиций")

        # 3. Проверка реальных ордеров
        print("\n📝 ОРДЕРА ЗА 18 ЧАСОВ:")
        result = await db.execute(
            text(
                """
            SELECT
                status,
                COUNT(*) as count,
                MIN(created_at) as first_order,
                MAX(created_at) as last_order
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '18 hours'
            GROUP BY status
        """
            )
        )
        orders = result.fetchall()

        for o in orders:
            print(f"  {o.status}: {o.count} ордеров")
            if o.last_order:
                minutes_ago = (datetime.utcnow() - o.last_order).total_seconds() / 60
                print(f"     Последний: {minutes_ago:.0f} мин назад")

        # 4. Проверка типов ордеров (тестовые vs реальные)
        result = await db.execute(
            text(
                """
            SELECT
                CASE
                    WHEN order_id LIKE 'test_%' THEN 'TEST'
                    WHEN order_id LIKE 'demo_%' THEN 'DEMO'
                    WHEN order_id LIKE 'paper_%' THEN 'PAPER'
                    ELSE 'REAL'
                END as type,
                COUNT(*) as cnt
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '18 hours'
            GROUP BY
                CASE
                    WHEN order_id LIKE 'test_%' THEN 'TEST'
                    WHEN order_id LIKE 'demo_%' THEN 'DEMO'
                    WHEN order_id LIKE 'paper_%' THEN 'PAPER'
                    ELSE 'REAL'
                END
        """
            )
        )
        order_types = result.fetchall()

        print("\n  Типы ордеров:")
        for ot in order_types:
            print(f"     {ot.type}: {ot.cnt}")

        # 5. Анализ закрытых сделок
        print("\n💰 ЗАКРЫТЫЕ СДЕЛКИ:")
        result = await db.execute(
            text(
                """
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as profitable,
                SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing,
                ROUND(SUM(profit)::numeric, 2) as total_profit
            FROM trades
            WHERE created_at >= NOW() - INTERVAL '18 hours'
        """
            )
        )
        trades = result.fetchone()

        if trades and trades.total_trades > 0:
            win_rate = (
                (trades.profitable / trades.total_trades * 100) if trades.total_trades > 0 else 0
            )
            print(f"  Всего сделок: {trades.total_trades}")
            print(f"  Прибыльных: {trades.profitable or 0}")
            print(f"  Убыточных: {trades.losing or 0}")
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Общая прибыль: ${trades.total_profit or 0:.2f}")
        else:
            print("  Нет закрытых сделок за период")

        # 6. Последняя активность
        print("\n⏰ ПОСЛЕДНЯЯ АКТИВНОСТЬ:")

        # Последний сигнал
        result = await db.execute(
            text(
                """
            SELECT MAX(created_at) as last_time
            FROM signals
        """
            )
        )
        last_signal = result.fetchone()
        if last_signal and last_signal.last_time:
            minutes_ago = (datetime.utcnow() - last_signal.last_time).total_seconds() / 60
            print(f"  Последний сигнал: {minutes_ago:.1f} мин назад")

        # Последний ордер
        result = await db.execute(
            text(
                """
            SELECT MAX(created_at) as last_time
            FROM orders
        """
            )
        )
        last_order = result.fetchone()
        if last_order and last_order.last_time:
            minutes_ago = (datetime.utcnow() - last_order.last_time).total_seconds() / 60
            print(f"  Последний ордер: {minutes_ago:.1f} мин назад")

        print("\n" + "=" * 80)
        print("ВЫВОДЫ:")
        print("=" * 80)

        if not has_short:
            print("❌ ML модель генерирует ТОЛЬКО LONG сигналы!")
            print("   Это критично при падающем рынке!")
            print("   Нужно проверить ML логику предсказаний")

        if long_count > 0 and short_count == 0:
            print("❌ Все позиции только LONG - нет хеджирования")

        if total_pnl < 0:
            print(f"⚠️ Отрицательный нереализованный PnL: ${total_pnl:.2f}")

        print("\n📌 РЕКОМЕНДАЦИИ:")
        print("1. Исправить ML модель для генерации SHORT сигналов")
        print("2. Проверить логику фильтрации сигналов")
        print("3. Добавить стратегию хеджирования")
        print("4. Проверить TP/SL настройки")


if __name__ == "__main__":
    asyncio.run(analyze())
