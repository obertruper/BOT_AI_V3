#!/usr/bin/env python3
"""
Простой мониторинг торговли
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


async def simple_monitor():
    """Простой мониторинг"""
    from database.connections.postgres import AsyncPGPool

    print("\n🔍 МОНИТОРИНГ ТОРГОВЛИ")
    print("=" * 60)

    try:
        pool = await AsyncPGPool.get_pool()

        # 1. Проверяем баланс через Bybit API
        print("\n💰 ПРОВЕРКА БАЛАНСА:")
        from exchanges.bybit.bybit_exchange import BybitExchange

        exchange = BybitExchange(
            api_key=os.getenv("BYBIT_API_KEY"),
            api_secret=os.getenv("BYBIT_API_SECRET"),
            sandbox=False,
        )

        try:
            await exchange.connect()
            balances = await exchange.get_balances()

            for balance in balances:
                if balance.total > 0:
                    print(
                        f"   {balance.currency}: ${balance.total:.2f} (доступно: ${balance.available:.2f})"
                    )
        except Exception as e:
            print(f"   ❌ Ошибка получения баланса: {e}")
        finally:
            await exchange.disconnect()

        # 2. ML сигналы за последние 10 минут
        print("\n🤖 ML СИГНАЛЫ (последние 10 минут):")

        signals = await pool.fetch(
            """
            SELECT
                symbol,
                signal_type,
                strength,
                confidence,
                created_at
            FROM signals
            WHERE created_at > NOW() - INTERVAL '10 minutes'
                AND strategy_name LIKE '%ML%'
            ORDER BY created_at DESC
        """
        )

        if signals:
            long_count = sum(1 for s in signals if s["signal_type"] == "LONG")
            short_count = sum(1 for s in signals if s["signal_type"] == "SHORT")
            neutral_count = len(signals) - long_count - short_count

            print(
                f"   Всего: {len(signals)} (LONG: {long_count} 🟢, SHORT: {short_count} 🔴, NEUTRAL: {neutral_count} ⚪)"
            )

            print("\n   Последние 5 сигналов:")
            for signal in signals[:5]:
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
            print("   ❌ Нет ML сигналов")

        # 3. Последние ордера
        print("\n💱 ПОСЛЕДНИЕ ОРДЕРА (2 часа):")

        orders = await pool.fetch(
            """
            SELECT
                id,
                symbol,
                side,
                order_type,
                price,
                quantity,
                status,
                created_at
            FROM orders
            WHERE created_at > NOW() - INTERVAL '2 hours'
            ORDER BY created_at DESC
            LIMIT 10
        """
        )

        if orders:
            market_count = sum(1 for o in orders if o["order_type"] == "MARKET")
            limit_count = sum(1 for o in orders if o["order_type"] == "LIMIT")

            print(
                f"   Всего: {len(orders)} (MARKET: {market_count} 💲, LIMIT: {limit_count} 📊)"
            )

            print("\n   Последние ордера:")
            for order in orders[:5]:
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
                    if order["order_type"] == "LIMIT" and order["price"]
                    else ""
                )
                print(
                    f"   {status_emoji} {order_type} #{order['id']} {order['symbol']} {order['side']} "
                    f"{order['quantity']}{price_info} - {order['status']} "
                    f"в {order['created_at'].strftime('%H:%M:%S')}"
                )
        else:
            print("   ❌ Нет ордеров")

        # 4. Проверка данных
        print("\n📊 АКТУАЛЬНОСТЬ ДАННЫХ:")

        data_stats = await pool.fetch(
            """
            SELECT
                symbol,
                MAX(datetime) as latest,
                COUNT(*) as count
            FROM raw_market_data
            WHERE interval_minutes = 15
                AND symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
            GROUP BY symbol
            ORDER BY symbol
        """
        )

        for stat in data_stats:
            lag = datetime.now() - stat["latest"].replace(tzinfo=None)
            lag_minutes = int(lag.total_seconds() / 60)
            status = "✅" if lag_minutes < 30 else "⚠️" if lag_minutes < 60 else "❌"
            print(
                f"   {status} {stat['symbol']}: последние данные {lag_minutes} мин назад ({stat['count']} свечей)"
            )

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    asyncio.run(simple_monitor())
