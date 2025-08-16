#!/usr/bin/env python3
"""
Проверка конфигурации торговли и типов ордеров
"""

import asyncio
import os
from datetime import datetime

import yaml
from dotenv import load_dotenv

load_dotenv()

# Устанавливаем переменные окружения
os.environ["PGPORT"] = "5555"
os.environ["PGUSER"] = "obertruper"
os.environ["PGDATABASE"] = "bot_trading_v3"


async def check_trading_config():
    """Проверка конфигурации торговли"""
    print(f"\n🔍 ПРОВЕРКА КОНФИГУРАЦИИ ТОРГОВЛИ - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    # 1. Проверка system.yaml
    print("\n⚙️ КОНФИГУРАЦИЯ SYSTEM.YAML:")

    try:
        with open("config/system.yaml") as f:
            system_config = yaml.safe_load(f)

        trading_config = system_config.get("trading", {})

        print("\n   📊 Основные настройки торговли:")
        print(f"      - Hedge mode: {trading_config.get('hedge_mode', False)}")
        print(f"      - Категория: {trading_config.get('category', 'spot')}")
        print(f"      - Плечо: {trading_config.get('leverage', 1)}")

        order_config = trading_config.get("order_execution", {})
        print("\n   💱 Настройки исполнения ордеров:")
        print(
            f"      - Тип ордеров по умолчанию: {order_config.get('default_order_type', 'MARKET')}"
        )
        print(
            f"      - Использовать лимитные ордера: {order_config.get('use_limit_orders', False)}"
        )
        print(f"      - Таймаут ордера: {order_config.get('order_timeout', 300)} сек")

        if order_config.get("use_limit_orders"):
            print(
                f"      - Отступ для BUY: {order_config.get('limit_order_offset_buy', 0.0001):.4f}"
            )
            print(
                f"      - Отступ для SELL: {order_config.get('limit_order_offset_sell', 0.0001):.4f}"
            )

    except Exception as e:
        print(f"   ❌ Ошибка чтения system.yaml: {e}")

    # 2. Проверка traders.yaml
    print("\n\n⚙️ КОНФИГУРАЦИЯ TRADERS.YAML:")

    try:
        with open("config/traders.yaml") as f:
            traders_config = yaml.safe_load(f)

        for trader in traders_config.get("traders", []):
            if trader.get("enabled"):
                print(f"\n   🤖 Трейдер: {trader['id']}")
                print(f"      - Тип: {trader['type']}")
                print(f"      - Стратегия: {trader['strategy']}")
                print(f"      - Биржа: {trader['exchange']}")

                strategy_config = trader.get("strategy_config", {})
                if "order_type" in strategy_config:
                    print(f"      - Тип ордеров стратегии: {strategy_config['order_type']}")

    except Exception as e:
        print(f"   ❌ Ошибка чтения traders.yaml: {e}")

    # 3. Проверка последних ордеров в БД
    print("\n\n📊 ПОСЛЕДНИЕ ОРДЕРА ИЗ БД:")

    from database.connections.postgres import AsyncPGPool

    try:
        pool = await AsyncPGPool.get_pool()

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
            WHERE created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 10
        """
        )

        if orders:
            for order in orders:
                order_type_emoji = "💲" if order["order_type"] == "MARKET" else "📊"
                print(
                    f"\n   {order_type_emoji} {order['symbol']} - {order['side']} {order['order_type']}"
                )
                print(f"      ID: {order['id']}")
                print(f"      Количество: {order['quantity']}")
                if order["order_type"] == "LIMIT":
                    print(f"      Цена лимитного ордера: ${order['price']}")
                print(f"      Статус: {order['status']}")
                print(f"      Время: {order['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("   ❌ Нет ордеров за последние 24 часа")

        # 4. Проверка сигналов ML
        print("\n\n🤖 ML СИГНАЛЫ (последний час):")

        signals = await pool.fetch(
            """
            SELECT
                symbol,
                signal_type,
                strength,
                confidence,
                suggested_price,
                created_at,
                extra_data
            FROM signals
            WHERE created_at > NOW() - INTERVAL '1 hour'
                AND strategy_name LIKE '%ML%'
            ORDER BY created_at DESC
            LIMIT 10
        """
        )

        if signals:
            long_count = sum(1 for s in signals if s["signal_type"] == "LONG")
            short_count = sum(1 for s in signals if s["signal_type"] == "SHORT")

            print("\n   📈 Статистика:")
            print(f"      - Всего ML сигналов: {len(signals)}")
            print(f"      - LONG (покупка): {long_count} 🟢")
            print(f"      - SHORT (продажа): {short_count} 🔴")

            print("\n   Последние сигналы:")
            for signal in signals[:5]:
                emoji = "🟢" if signal["signal_type"] == "LONG" else "🔴"
                print(f"\n   {emoji} {signal['symbol']} - {signal['signal_type']}")
                print(f"      Уверенность: {signal['confidence']:.2%}")
                print(f"      Сила: {signal['strength']:.4f}")
                if signal["suggested_price"]:
                    print(f"      Рекомендуемая цена: ${signal['suggested_price']}")
                print(f"      Время: {signal['created_at'].strftime('%H:%M:%S')}")
        else:
            print("   ❌ Нет ML сигналов за последний час")

    except Exception as e:
        print(f"\n❌ Ошибка работы с БД: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()

    # 5. Рекомендации
    print("\n\n💡 РЕКОМЕНДАЦИИ:")
    print("   1. Чтобы использовать РЫНОЧНЫЕ ордера вместо лимитных:")
    print("      - В config/system.yaml установите:")
    print("        trading.order_execution.use_limit_orders: false")
    print("        trading.order_execution.default_order_type: MARKET")
    print("\n   2. Для просмотра логов в реальном времени:")
    print("      - tail -f logs/core.log")
    print("      - или запустите: python unified_launcher.py --logs")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(check_trading_config())
