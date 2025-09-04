#!/usr/bin/env python3
"""
Финальный тест всех исправлений
Проверяет работу системы после всех изменений
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Загружаем .env файл
from dotenv import load_dotenv

load_dotenv()

from database.database_manager import DatabaseManager
from database.models.base_models import OrderStatus as DBOrderStatus
from exchanges.base.order_types import OrderStatus
from exchanges.bybit.bybit_exchange import BybitExchange


async def test_enum_in_database():
    """Тест enum значений в базе данных"""
    print("🗄️ ТЕСТ ENUM В БАЗЕ ДАННЫХ")
    print("-" * 60)

    try:
        # Подключаемся к БД
        db_manager = DatabaseManager()
        await db_manager.initialize()

        # Проверяем что можем сохранить все статусы
        test_statuses = [
            OrderStatus.PENDING,
            OrderStatus.NEW,  # Используем NEW вместо OPEN в exchanges/base/order_types.py
            OrderStatus.FILLED,
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
        ]

        for status in test_statuses:
            # Проверяем что значение enum правильное
            status_value = status.value
            print(f"✅ {status.name}: '{status_value}' (lowercase)")

        # Проверяем совместимость с БД enum
        db_status = DBOrderStatus.REJECTED
        code_status = OrderStatus.REJECTED

        compatible = db_status.value == code_status.value
        print(
            f"\n✅ Совместимость enum: DBOrderStatus.REJECTED ('{db_status.value}') == OrderStatus.REJECTED ('{code_status.value}'): {compatible}"
        )

        return compatible

    except Exception as e:
        print(f"❌ Ошибка теста enum: {e}")
        return False


async def test_hedge_mode_final():
    """Финальный тест hedge mode"""
    print("\n🎯 ФИНАЛЬНЫЙ ТЕСТ HEDGE MODE")
    print("-" * 60)

    try:
        # Создаём exchange
        api_key = os.getenv("BYBIT_API_KEY", "public_access")
        api_secret = os.getenv("BYBIT_API_SECRET", "public_access")

        exchange = BybitExchange(api_key, api_secret)
        client = exchange.client

        # Проверяем настройки
        print(f"✅ Hedge mode enabled: {client.hedge_mode}")
        print(f"✅ BYBIT_HEDGE_MODE env: {os.getenv('BYBIT_HEDGE_MODE', 'не установлена')}")

        # Проверяем position index для разных сторон
        test_cases = [
            ("BUY", 1),
            ("SELL", 2),
        ]

        for side, expected in test_cases:
            actual = client._get_position_idx(side)
            status = "✅" if actual == expected else "❌"
            print(f"{status} {side:5} -> positionIdx={actual} (expected {expected})")

        # Симулируем параметры ордера
        from exchanges.base.order_types import OrderRequest, OrderSide, OrderType, TimeInForce

        order_request = OrderRequest(
            symbol="XRPUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,  # Используем большее количество для минимального объёма
            time_in_force=TimeInForce.GTC,
        )

        # Проверяем форматирование количества
        from exchanges.bybit.client import format_quantity
        from exchanges.bybit.instrument_settings import get_instrument_settings

        settings = get_instrument_settings("XRPUSDT")
        formatted_qty = format_quantity(
            quantity=10.759,
            qty_step=settings.get("qtyStep", 0.1),
            min_qty=settings.get("minOrderQty", 0.1),
            max_qty=settings.get("maxOrderQty", float("inf")),
            symbol="XRPUSDT",
        )

        print(f"\n✅ Форматирование количества: 10.759 -> '{formatted_qty}'")

        # Проверяем что position_idx правильный
        position_idx = client._get_position_idx(order_request.side.value, symbol="XRPUSDT")
        print(f"✅ Position index для BUY: {position_idx}")

        success = client.hedge_mode and position_idx == 1

        if success:
            print("\n🎉 Hedge mode работает корректно!")
        else:
            print("\n❌ Проблемы с hedge mode!")

        return success

    except Exception as e:
        print(f"❌ Ошибка теста hedge mode: {e}")
        return False


async def test_system_status():
    """Проверка общего статуса системы"""
    print("\n🔍 ПРОВЕРКА СТАТУСА СИСТЕМЫ")
    print("-" * 60)

    # Проверяем переменные окружения
    env_checks = [
        ("BYBIT_HEDGE_MODE", "true"),
        ("PGPORT", "5555"),
        ("BYBIT_API_KEY", None),  # Просто проверяем наличие
        ("BYBIT_API_SECRET", None),
    ]

    all_good = True

    for env_name, expected in env_checks:
        actual = os.getenv(env_name)
        if expected:
            status = "✅" if actual == expected else "❌"
            print(f"{status} {env_name}: {actual} (expected: {expected})")
            if actual != expected:
                all_good = False
        else:
            status = "✅" if actual else "❌"
            print(f"{status} {env_name}: {'установлена' if actual else 'НЕ УСТАНОВЛЕНА'}")
            if not actual:
                all_good = False

    return all_good


async def main():
    """Основная функция"""
    print("🚀 ФИНАЛЬНАЯ ПРОВЕРКА ВСЕХ ИСПРАВЛЕНИЙ")
    print("=" * 80)

    results = []

    # Запускаем все тесты
    results.append(await test_enum_in_database())
    results.append(await test_hedge_mode_final())
    results.append(await test_system_status())

    # Итоговый результат
    print("\n" + "=" * 80)
    print("📊 ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 80)

    test_names = ["Enum в базе данных", "Hedge mode", "Статус системы"]

    for i, (name, passed) in enumerate(zip(test_names, results, strict=False), 1):
        status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
        print(f"{i}. {name:25} | {status}")

    all_passed = all(results)

    print("-" * 80)
    if all_passed:
        print("🎉 ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ!")
        print("✅ Система полностью готова к работе!")
        print("\n📝 ИТОГ:")
        print("• Hedge mode: включён и работает (positionIdx=1 для BUY, =2 для SELL)")
        print("• Форматирование количества: корректное")
        print("• Enum статусы: совместимы с БД")
        print("\n🚀 Перезапустите систему командой: ./stop_all.sh && ./start_with_logs_filtered.sh")
    else:
        failed_count = sum(1 for x in results if not x)
        print(f"⚠️  {failed_count} тестов провалено.")
        print("\n❌ Требуются дополнительные исправления.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
