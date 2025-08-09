#!/usr/bin/env python3
"""
Проверка сигналов и ордеров
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


async def check_signals_and_orders():
    """Проверка сигналов и ордеров"""
    print(f"\n🔍 ПРОВЕРКА СИГНАЛОВ И ОРДЕРОВ - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    from database.connections.postgres import AsyncPGPool

    try:
        pool = await AsyncPGPool.get_pool()

        # 1. Проверка ML сигналов за последний час
        print("\n📊 ML СИГНАЛЫ (последний час):")

        signals = await pool.fetch(
            """
            SELECT
                symbol,
                direction,
                confidence,
                strength,
                created_at,
                metadata
            FROM signals
            WHERE created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 20
        """
        )

        if signals:
            positive_count = 0
            negative_count = 0
            neutral_count = 0

            for signal in signals:
                direction = signal["direction"]
                if direction == "LONG":
                    positive_count += 1
                    emoji = "🟢"
                elif direction == "SHORT":
                    negative_count += 1
                    emoji = "🔴"
                else:
                    neutral_count += 1
                    emoji = "⚪"

                print(f"\n   {emoji} {signal['symbol']} - {direction}")
                print(f"      Уверенность: {signal['confidence']:.2%}")
                print(f"      Сила: {signal['strength']:.4f}")
                print(f"      Время: {signal['created_at'].strftime('%H:%M:%S')}")

                # Показываем metadata если есть
                if signal["metadata"]:
                    import json

                    meta = (
                        json.loads(signal["metadata"])
                        if isinstance(signal["metadata"], str)
                        else signal["metadata"]
                    )
                    if "predicted_return" in meta:
                        print(f"      Ожидаемый доход: {meta['predicted_return']:.4f}")

            print("\n   📈 СТАТИСТИКА:")
            print(f"      - Всего сигналов: {len(signals)}")
            print(f"      - LONG (покупка): {positive_count} 🟢")
            print(f"      - SHORT (продажа): {negative_count} 🔴")
            print(f"      - NEUTRAL: {neutral_count} ⚪")
        else:
            print("   ❌ Нет сигналов за последний час")

        # 2. Проверка ордеров
        print("\n\n💱 ОРДЕРА (последние 24 часа):")

        orders = await pool.fetch(
            """
            SELECT
                symbol,
                side,
                order_type,
                price,
                quantity,
                status,
                created_at,
                filled_at,
                exchange_order_id
            FROM orders
            WHERE created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 10
        """
        )

        if orders:
            for order in orders:
                status_emoji = {
                    "new": "⏳",
                    "open": "⏳",
                    "filled": "✅",
                    "cancelled": "❌",
                    "rejected": "❌",
                }.get(order["status"].lower(), "❓")

                print(
                    f"\n   {status_emoji} {order['symbol']} - {order['side']} {order['order_type']}"
                )
                print(f"      Количество: {order['quantity']}")
                if order["order_type"] == "LIMIT":
                    print(f"      Цена: ${order['price']}")
                print(f"      Статус: {order['status']}")
                print(
                    f"      Время создания: {order['created_at'].strftime('%H:%M:%S')}"
                )
                if order["filled_at"]:
                    print(
                        f"      Время исполнения: {order['filled_at'].strftime('%H:%M:%S')}"
                    )
        else:
            print("   ❌ Нет ордеров за последние 24 часа")

        # 3. Проверка текущих цен
        print("\n\n💲 ТЕКУЩИЕ ЦЕНЫ (последние данные):")

        prices = await pool.fetch(
            """
            SELECT DISTINCT ON (symbol)
                symbol,
                close as price,
                datetime,
                volume
            FROM raw_market_data
            WHERE interval_minutes = 15
            AND symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT')
            ORDER BY symbol, datetime DESC
        """
        )

        for price_data in prices:
            print(
                f"   {price_data['symbol']}: ${price_data['price']:.2f} (обновлено: {price_data['datetime'].strftime('%H:%M')})"
            )

        # 4. Проверка позиций
        print("\n\n📈 ПОЗИЦИИ:")

        positions = await pool.fetch(
            """
            SELECT
                symbol,
                side,
                quantity,
                entry_price,
                current_price,
                unrealized_pnl,
                created_at
            FROM positions
            WHERE status = 'open'
            ORDER BY created_at DESC
        """
        )

        if positions:
            for pos in positions:
                pnl_emoji = "🟢" if pos["unrealized_pnl"] > 0 else "🔴"
                print(f"\n   {pos['symbol']} - {pos['side']}")
                print(f"      Количество: {pos['quantity']}")
                print(f"      Цена входа: ${pos['entry_price']}")
                print(f"      Текущая цена: ${pos['current_price']}")
                print(f"      PnL: {pnl_emoji} ${pos['unrealized_pnl']:.2f}")
        else:
            print("   ❌ Нет открытых позиций")

        # 5. Проверка конфигурации ордеров
        print("\n\n⚙️ КОНФИГУРАЦИЯ ТОРГОВЛИ:")

        from core.config.config_manager import get_global_config_manager

        config = get_global_config_manager().get_config()

        # Проверяем настройки ордеров
        trading_config = config.get("trading", {})
        order_config = trading_config.get("order_execution", {})

        print(
            f"   Тип ордеров по умолчанию: {order_config.get('default_order_type', 'MARKET')}"
        )
        print(
            f"   Использовать лимитные ордера: {order_config.get('use_limit_orders', False)}"
        )
        print(
            f"   Отступ для лимитных ордеров: {order_config.get('limit_order_offset', 0.0001):.4f}"
        )

        # Проверяем стратегию
        ml_strategy_config = None
        for trader in config.get("traders", []):
            if trader.get("strategy") == "ml_signal":
                ml_strategy_config = trader.get("strategy_config", {})
                break

        if ml_strategy_config:
            print("\n   📊 Настройки ML стратегии:")
            print(
                f"      Интервал сигналов: {ml_strategy_config.get('signal_interval', 60)} сек"
            )
            print(
                f"      Минимальная уверенность: {ml_strategy_config.get('min_confidence', 0.6):.0%}"
            )

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(check_signals_and_orders())
