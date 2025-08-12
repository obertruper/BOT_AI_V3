#!/usr/bin/env python3
"""
Анализ торговой активности бота за последние 18 часов
"""

import asyncio
from datetime import datetime

from sqlalchemy import text

from database.connections import get_async_db


async def analyze_bot_activity():
    print("=" * 80)
    print("📊 АНАЛИЗ РАБОТЫ БОТА ЗА ПОСЛЕДНИЕ 18 ЧАСОВ")
    print("=" * 80)

    async with get_async_db() as db:
        # 1. Анализ сигналов LONG vs SHORT
        print("\n1️⃣ СИГНАЛЫ (LONG vs SHORT):")
        result = await db.execute(
            text(
                """
            SELECT
                signal_type,
                COUNT(*) as count,
                ROUND(AVG(confidence)::numeric, 3) as avg_conf,
                ROUND(AVG(strength)::numeric, 3) as avg_str
            FROM signals
            WHERE created_at >= NOW() - INTERVAL '18 hours'
            GROUP BY signal_type
            ORDER BY count DESC
        """
            )
        )
        signals = result.fetchall()

        total_signals = sum(s.count for s in signals)
        print(f"  Всего сигналов: {total_signals}")

        for s in signals:
            percent = (s.count / total_signals * 100) if total_signals > 0 else 0
            print(
                f"  {s.signal_type.upper()}: {s.count} ({percent:.1f}%) | confidence={s.avg_conf:.3f}, strength={s.avg_str:.3f}"
            )

        if not any(s.signal_type.lower() == "short" for s in signals):
            print("  ⚠️ SHORT СИГНАЛОВ НЕТ! Модель работает только в LONG!")

        # 2. Детализация по символам
        print("\n  Распределение по символам:")
        result = await db.execute(
            text(
                """
            SELECT
                symbol,
                signal_type,
                COUNT(*) as count
            FROM signals
            WHERE created_at >= NOW() - INTERVAL '18 hours'
            GROUP BY symbol, signal_type
            ORDER BY symbol, signal_type
        """
            )
        )
        symbol_signals = result.fetchall()

        current_symbol = None
        for ss in symbol_signals:
            if current_symbol != ss.symbol:
                if current_symbol:
                    print()
                print(f"  {ss.symbol}:", end=" ")
                current_symbol = ss.symbol
            print(f"{ss.signal_type}={ss.count}", end=" ")
        print()

        # 3. Статусы ордеров
        print("\n2️⃣ ОРДЕРА:")
        result = await db.execute(
            text(
                """
            SELECT
                status,
                COUNT(*) as count
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '18 hours'
            GROUP BY status
            ORDER BY count DESC
        """
            )
        )
        orders = result.fetchall()

        for o in orders:
            print(f"  {o.status}: {o.count}")

        # 4. Проверка реальных vs тестовых ордеров
        print("\n3️⃣ ТИП ОРДЕРОВ:")
        result = await db.execute(
            text(
                """
            WITH order_types AS (
                SELECT
                    CASE
                        WHEN order_id LIKE 'test_%' THEN 'ТЕСТОВЫЕ'
                        WHEN order_id LIKE 'demo_%' THEN 'ДЕМО'
                        WHEN order_id LIKE 'paper_%' THEN 'PAPER'
                        WHEN order_id LIKE 'BOT_%' THEN 'BOT_GENERATED'
                        ELSE 'РЕАЛЬНЫЕ_BYBIT'
                    END as order_type
                FROM orders
                WHERE created_at >= NOW() - INTERVAL '18 hours'
            )
            SELECT order_type, COUNT(*) as count
            FROM order_types
            GROUP BY order_type
            ORDER BY count DESC
        """
            )
        )
        order_types = result.fetchall()

        for ot in order_types:
            print(f"  {ot.order_type}: {ot.count}")

        # 5. PnL анализ
        print("\n4️⃣ ПРИБЫЛЬ/УБЫТОК (PnL):")
        result = await db.execute(
            text(
                """
            SELECT
                symbol,
                COUNT(*) as trades,
                ROUND(SUM(pnl)::numeric, 2) as total_pnl,
                ROUND(AVG(pnl)::numeric, 2) as avg_pnl,
                ROUND(MAX(pnl)::numeric, 2) as best,
                ROUND(MIN(pnl)::numeric, 2) as worst
            FROM trades
            WHERE created_at >= NOW() - INTERVAL '18 hours'
            GROUP BY symbol
            ORDER BY total_pnl DESC
            LIMIT 10
        """
            )
        )
        trades = result.fetchall()

        if trades:
            total_pnl_all = 0
            for t in trades:
                status = "✅" if t.total_pnl and t.total_pnl > 0 else "❌"
                pnl = t.total_pnl if t.total_pnl else 0
                total_pnl_all += pnl
                print(
                    f"  {status} {t.symbol}: {t.trades} сделок, PnL=${pnl:.2f} (avg=${t.avg_pnl or 0:.2f}, best=${t.best or 0:.2f}, worst=${t.worst or 0:.2f})"
                )
            print(f"\n  📈 ИТОГО PnL за 18 часов: ${total_pnl_all:.2f}")
        else:
            print("  Нет закрытых сделок за период")

        # 6. Текущие открытые позиции
        print("\n5️⃣ ОТКРЫТЫЕ ПОЗИЦИИ:")
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
            ORDER BY unrealized_pnl DESC
        """
            )
        )
        positions = result.fetchall()

        if positions:
            total_unrealized = 0
            for p in positions:
                pnl = p.unrealized_pnl if p.unrealized_pnl else 0
                age_hours = (datetime.utcnow() - p.created_at).total_seconds() / 3600
                pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"${pnl:.2f}"
                print(
                    f"  {p.symbol} {p.side}: size={p.size}, entry={p.entry_price}, PnL={pnl_str}, возраст={age_hours:.1f}ч"
                )
                total_unrealized += pnl

            print(f"\n  💰 Общий нереализованный PnL: ${total_unrealized:.2f}")
            print(f"  📊 Всего открытых позиций: {len(positions)}")
        else:
            print("  Нет открытых позиций")

        # 7. Последняя активность
        print("\n6️⃣ ПОСЛЕДНЯЯ АКТИВНОСТЬ:")
        result = await db.execute(
            text(
                """
            SELECT
                'Signals' as component,
                COUNT(*) as count_last_hour,
                MAX(created_at) as last_activity
            FROM signals
            WHERE created_at >= NOW() - INTERVAL '1 hour'
            UNION ALL
            SELECT
                'Orders' as component,
                COUNT(*) as count_last_hour,
                MAX(created_at) as last_activity
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '1 hour'
            UNION ALL
            SELECT
                'Trades' as component,
                COUNT(*) as count_last_hour,
                MAX(created_at) as last_activity
            FROM trades
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """
            )
        )
        activity = result.fetchall()

        for a in activity:
            if a.last_activity:
                minutes_ago = (datetime.utcnow() - a.last_activity).total_seconds() / 60
                print(
                    f"  {a.component}: {a.count_last_hour} за час, последняя {minutes_ago:.1f} мин назад"
                )
            else:
                print(f"  {a.component}: НЕТ активности за последний час ⚠️")

        # 8. Проверка частичных закрытий и TP/SL
        print("\n7️⃣ ЧАСТИЧНЫЕ ЗАКРЫТИЯ И TP/SL:")
        result = await db.execute(
            text(
                """
            SELECT
                COUNT(*) FILTER (WHERE notes LIKE '%partial%') as partial_closes,
                COUNT(*) FILTER (WHERE notes LIKE '%take_profit%' OR notes LIKE '%TP%') as tp_hits,
                COUNT(*) FILTER (WHERE notes LIKE '%stop_loss%' OR notes LIKE '%SL%') as sl_hits,
                COUNT(*) as total_trades
            FROM trades
            WHERE created_at >= NOW() - INTERVAL '18 hours'
        """
            )
        )
        tp_sl = result.fetchone()

        if tp_sl and tp_sl.total_trades > 0:
            print(f"  Частичных закрытий: {tp_sl.partial_closes or 0}")
            print(f"  Take Profit срабатываний: {tp_sl.tp_hits or 0}")
            print(f"  Stop Loss срабатываний: {tp_sl.sl_hits or 0}")
            print(f"  Всего сделок: {tp_sl.total_trades}")
        else:
            print("  Нет данных о TP/SL")


if __name__ == "__main__":
    asyncio.run(analyze_bot_activity())
