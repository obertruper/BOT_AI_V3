#!/usr/bin/env python3
"""
Комплексный тест всех исправлений Bybit API
Проверяет:
1. Форматирование количества (quantity formatting)
2. Hedge mode configuration
3. Enum REJECTED статус
4. Интеграцию всех исправлений
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models.base_models import OrderStatus
from exchanges.base.order_types import OrderRequest, OrderSide, OrderType, TimeInForce
from exchanges.bybit.client import BybitClient, format_quantity
from exchanges.bybit.instrument_settings import INSTRUMENT_SETTINGS, get_instrument_settings


async def test_quantity_formatting():
    """Тест форматирования количества"""
    print("🧪 1. ТЕСТИРОВАНИЕ ФОРМАТИРОВАНИЯ КОЛИЧЕСТВА")
    print("-" * 60)

    test_cases = [
        ("XRPUSDT", 1.759, "1.7"),  # XRP с шагом 0.1
        ("DOGEUSDT", 24.0, "24"),  # DOGE с шагом 1.0
        ("ADAUSDT", 5.99, "5"),  # ADA с шагом 1.0
        ("SOLUSDT", 0.234, "0.2"),  # SOL с шагом 0.1
        ("BTCUSDT", 0.00123, "0.001"),  # BTC с шагом 0.001
        ("ETHUSDT", 0.0156, "0.01"),  # ETH с шагом 0.01
    ]

    all_passed = True

    for symbol, original_qty, expected in test_cases:
        settings = INSTRUMENT_SETTINGS.get(symbol, {})
        qty_step = settings.get("qtyStep", 0.1)
        min_qty = settings.get("minOrderQty", 0.1)
        max_qty = settings.get("maxOrderQty", float("inf"))

        try:
            result = format_quantity(
                quantity=original_qty,
                qty_step=qty_step,
                min_qty=min_qty,
                max_qty=max_qty,
                symbol=symbol,
            )

            passed = result == expected
            status = "✅" if passed else "❌"

            if not passed:
                all_passed = False

            print(
                f"{status} {symbol:10} | {original_qty:8.6f} -> {result:8s} | Expected: {expected:8s}"
            )

        except Exception as e:
            print(f"❌ {symbol:10} | {original_qty:8.6f} | Error: {e}")
            all_passed = False

    return all_passed


async def test_hedge_mode():
    """Тест hedge mode"""
    print("\n🧪 2. ТЕСТИРОВАНИЕ HEDGE MODE")
    print("-" * 60)

    # Тест с hedge mode включён
    os.environ["BYBIT_HEDGE_MODE"] = "true"
    client = BybitClient("public_access", "public_access")

    print(f"✅ Hedge mode enabled: {client.hedge_mode}")

    test_cases = [("BUY", 1), ("SELL", 2), ("LONG", 1), ("SHORT", 2)]

    all_passed = True

    for side, expected_idx in test_cases:
        actual_idx = client._get_position_idx(side)
        passed = actual_idx == expected_idx
        status = "✅" if passed else "❌"

        if not passed:
            all_passed = False

        print(f"{status} {side:5} -> positionIdx={actual_idx} (expected {expected_idx})")

    return all_passed


async def test_order_status_enum():
    """Тест enum OrderStatus"""
    print("\n🧪 3. ТЕСТИРОВАНИЕ ENUM ORDER STATUS")
    print("-" * 60)

    try:
        # Проверяем все статусы
        statuses = [
            OrderStatus.PENDING,
            OrderStatus.OPEN,
            OrderStatus.FILLED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        ]

        for status in statuses:
            print(f"✅ {status.name:18} -> '{status.value}'")

        # Особая проверка REJECTED
        rejected_status = OrderStatus.REJECTED
        if rejected_status.value == "rejected":
            print(f"✅ REJECTED статус корректный: '{rejected_status.value}'")
            return True
        else:
            print(f"❌ REJECTED статус неверный: '{rejected_status.value}'")
            return False

    except Exception as e:
        print(f"❌ Ошибка проверки enum: {e}")
        return False


async def test_integration():
    """Интеграционный тест всех исправлений"""
    print("\n🧪 4. ИНТЕГРАЦИОННЫЙ ТЕСТ")
    print("-" * 60)

    try:
        # Создаём клиент
        client = BybitClient("public_access", "public_access")

        # Создаём тестовый запрос
        order_request = OrderRequest(
            symbol="XRPUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.759,  # Тестируем форматирование
            time_in_force=TimeInForce.GTC,
        )

        # Получаем информацию для форматирования
        settings = get_instrument_settings("XRPUSDT")

        # Форматируем количество
        formatted_qty = format_quantity(
            quantity=order_request.quantity,
            qty_step=settings.get("qtyStep", 0.1),
            min_qty=settings.get("minOrderQty", 0.1),
            max_qty=settings.get("maxOrderQty", float("inf")),
            symbol="XRPUSDT",
        )

        # Получаем position index
        position_idx = client._get_position_idx(order_request.side.value, symbol="XRPUSDT")

        print(f"✅ Symbol: {order_request.symbol}")
        print(f"✅ Original quantity: {order_request.quantity}")
        print(f"✅ Formatted quantity: {formatted_qty}")
        print(f"✅ Side: {order_request.side.value}")
        print(f"✅ Position index: {position_idx}")
        print(f"✅ Hedge mode: {client.hedge_mode}")

        # Проверяем корректность
        qty_correct = formatted_qty == "1.7"
        idx_correct = position_idx == 1  # BUY должно быть 1
        hedge_correct = client.hedge_mode == True

        if qty_correct and idx_correct and hedge_correct:
            print("✅ Интеграционный тест ПРОЙДЕН!")
            return True
        else:
            print("❌ Интеграционный тест ПРОВАЛЕН!")
            return False

    except Exception as e:
        print(f"❌ Ошибка интеграционного теста: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("🚀 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ BYBIT API")
    print("=" * 80)

    results = []

    # Запускаем все тесты
    results.append(await test_quantity_formatting())
    results.append(await test_hedge_mode())
    results.append(await test_order_status_enum())
    results.append(await test_integration())

    # Итоговый результат
    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 80)

    test_names = [
        "Форматирование количества",
        "Hedge mode",
        "Order Status Enum",
        "Интеграционный тест",
    ]

    for i, (name, passed) in enumerate(zip(test_names, results, strict=False), 1):
        status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
        print(f"{i}. {name:25} | {status}")

    all_passed = all(results)

    print("-" * 80)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Исправления работают корректно.")
        print("✅ Система готова к продуктиву!")
    else:
        failed_count = sum(1 for x in results if not x)
        print(f"⚠️  {failed_count} тестов провалено. Требуются дополнительные исправления.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
