#!/usr/bin/env python3
"""
Мониторинг торговли в реальном времени
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def monitor_trading():
    """Мониторинг торговли"""
    from database.connections.postgres import AsyncPGPool

    print("\n🔍 МОНИТОРИНГ ТОРГОВЛИ - REAL TIME")
    print("=" * 60)
    print("Нажмите Ctrl+C для остановки\n")

    try:
        pool = await AsyncPGPool.get_pool()

        while True:
            # Очищаем экран
            print("\033[2J\033[H")  # Clear screen and move cursor to top

            print(
                f"🔍 МОНИТОРИНГ ТОРГОВЛИ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print("=" * 60)

            # 1. Баланс
            balance = await pool.fetchrow(
                """
                SELECT balance, reserved, updated_at
                FROM account_balances
                WHERE currency = 'USDT'
                ORDER BY updated_at DESC
                LIMIT 1
            """
            )

            if balance:
                print("\n💰 БАЛАНС:")
                print(
                    f"   USDT: ${balance['balance']:.2f} (зарезервировано: ${balance['reserved']:.2f})"
                )
                print(f"   Обновлено: {balance['updated_at'].strftime('%H:%M:%S')}")

            # 2. Последние ML сигналы
            print("\n🤖 ML СИГНАЛЫ (последние 5 минут):")

            signals = await pool.fetch(
                """
                SELECT
                    symbol,
                    signal_type,
                    strength,
                    confidence,
                    created_at
                FROM signals
                WHERE created_at > NOW() - INTERVAL '5 minutes'
                    AND strategy_name LIKE '%ML%'
                ORDER BY created_at DESC
                LIMIT 5
            """
            )

            if signals:
                for signal in signals:
                    emoji = (
                        "🟢"
                        if signal["signal_type"] == "LONG"
                        else "🔴"
                        if signal["signal_type"] == "SHORT"
                        else "⚪"
                    )
                    print(
                        f"   {emoji} {signal['symbol']} - {signal['signal_type']} "
                        f"(уверенность: {signal['confidence']:.0%}, сила: {signal['strength']:.4f}) "
                        f"в {signal['created_at'].strftime('%H:%M:%S')}"
                    )
            else:
                print("   ❌ Нет сигналов")

            # 3. Последние ордера
            print("\n💱 ПОСЛЕДНИЕ ОРДЕРА:")

            orders = await pool.fetch(
                """
                SELECT
                    symbol,
                    side,
                    order_type,
                    price,
                    quantity,
                    status,
                    created_at
                FROM orders
                WHERE created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                LIMIT 5
            """
            )

            if orders:
                for order in orders:
                    status_emoji = (
                        "✅"
                        if order["status"] == "FILLED"
                        else "⏳"
                        if order["status"] in ["NEW", "OPEN"]
                        else "❌"
                    )
                    order_type = "💲" if order["order_type"] == "MARKET" else "📊"
                    price_info = (
                        f" @ ${order['price']}"
                        if order["order_type"] == "LIMIT"
                        else ""
                    )
                    print(
                        f"   {status_emoji} {order_type} {order['symbol']} {order['side']} "
                        f"{order['quantity']}{price_info} - {order['status']} "
                        f"в {order['created_at'].strftime('%H:%M:%S')}"
                    )
            else:
                print("   ❌ Нет ордеров за последний час")

            # 4. Открытые позиции
            print("\n📈 ОТКРЫТЫЕ ПОЗИЦИИ:")

            positions = await pool.fetch(
                """
                SELECT
                    symbol,
                    side,
                    quantity,
                    entry_price,
                    current_price,
                    unrealized_pnl
                FROM positions
                WHERE status = 'open'
            """
            )

            if positions:
                total_pnl = 0
                for pos in positions:
                    pnl_emoji = "🟢" if pos["unrealized_pnl"] > 0 else "🔴"
                    total_pnl += pos["unrealized_pnl"]
                    print(
                        f"   {pos['symbol']} {pos['side']}: {pos['quantity']} @ ${pos['entry_price']} "
                        f"→ ${pos['current_price']} {pnl_emoji} PnL: ${pos['unrealized_pnl']:.2f}"
                    )
                print(f"   📊 Общий PnL: ${total_pnl:.2f}")
            else:
                print("   ❌ Нет открытых позиций")

            # 5. Статистика
            stats = await pool.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as orders_hour,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as orders_day,
                    COUNT(*) FILTER (WHERE status = 'FILLED' AND created_at > NOW() - INTERVAL '24 hours') as filled_day
                FROM orders
            """
            )

            ml_stats = await pool.fetchrow(
                """
                SELECT
                    COUNT(*) as signals_hour,
                    COUNT(*) FILTER (WHERE signal_type = 'LONG') as long_signals,
                    COUNT(*) FILTER (WHERE signal_type = 'SHORT') as short_signals
                FROM signals
                WHERE created_at > NOW() - INTERVAL '1 hour'
                    AND strategy_name LIKE '%ML%'
            """
            )

            print("\n📊 СТАТИСТИКА:")
            print(f"   Ордеров за час: {stats['orders_hour']}")
            print(
                f"   Ордеров за 24ч: {stats['orders_day']} (исполнено: {stats['filled_day']})"
            )
            print(
                f"   ML сигналов за час: {ml_stats['signals_hour']} "
                f"(LONG: {ml_stats['long_signals']}, SHORT: {ml_stats['short_signals']})"
            )

            print("\n" + "=" * 60)
            print("Обновление каждые 5 секунд...")

            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\n\n⏹️ Мониторинг остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(monitor_trading())
