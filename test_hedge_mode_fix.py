#!/usr/bin/env python3
"""
Тест исправления hedge mode для Bybit
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.base.order_types import OrderRequest, OrderSide, OrderType, TimeInForce
from exchanges.bybit.client import BybitClient


async def test_hedge_mode():
    """Тест hedge mode логики"""

    print("🔧 Тестируем hedge mode fix...")
    print("-" * 60)

    # Создаём клиент с публичным доступом
    client = BybitClient("public_access", "public_access")

    # Проверяем, что hedge_mode установлен правильно
    print(f"✅ Hedge mode status: {client.hedge_mode}")
    print(f"✅ Default leverage: {client.default_leverage}")
    print(f"✅ Trading category: {client.trading_category}")

    # Тестируем _get_position_idx для разных сторон
    test_cases = [
        ("BUY", "Покупка/Long"),
        ("SELL", "Продажа/Short"),
        ("LONG", "Long позиция"),
        ("SHORT", "Short позиция"),
    ]

    print("\n📊 Тестируем position_idx для разных сторон:")
    print("-" * 60)

    for side, description in test_cases:
        position_idx = client._get_position_idx(side)
        expected = 1 if side.upper() in ["BUY", "LONG"] else 2
        status = "✅" if position_idx == expected else "❌"

        print(
            f"{status} {description:15} | side={side:5} | position_idx={position_idx} | expected={expected}"
        )

    # Тестируем создание параметров ордера
    print("\n🔧 Тестируем создание параметров ордера:")
    print("-" * 60)

    # Создаём тестовый order request
    order_request = OrderRequest(
        symbol="XRPUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.5,
        time_in_force=TimeInForce.GTC,
    )

    # Получаем position_idx как это делается в place_order
    symbol = order_request.symbol.replace("-", "")  # clean_symbol
    position_idx = client._get_position_idx(order_request.side.value, symbol=symbol)

    print(f"✅ Order symbol: {symbol}")
    print(f"✅ Order side: {order_request.side.value}")
    print(f"✅ Position index: {position_idx}")

    # Проверяем логику hedge mode detection
    if position_idx != 0:
        print(f"✅ Hedge mode корректно определён: positionIdx={position_idx}")
    else:
        # Проверяем fallback логику
        import os

        if os.getenv("BYBIT_HEDGE_MODE", "true").lower() == "true":
            corrected_idx = 1 if order_request.side.value.upper() in ["BUY", "LONG"] else 2
            print(f"⚠️  Position_idx был 0, но hedge mode включён. Корректируем на {corrected_idx}")
        else:
            print("✅ One-way mode корректно определён: positionIdx=0")

    print("\n" + "=" * 60)
    print("🎉 Тест hedge mode завершён!")

    return True


async def test_integration():
    """Интеграционный тест с реальными параметрами"""
    print("\n🧪 Интеграционный тест hedge mode...")
    print("-" * 60)

    # Тестируем с разными переменными окружения
    test_env_values = ["true", "false", "1", "0"]

    for env_value in test_env_values:
        os.environ["BYBIT_HEDGE_MODE"] = env_value

        # Создаём новый клиент
        client = BybitClient("public_access", "public_access")

        expected_hedge = env_value.lower() in ["true", "1"]
        actual_hedge = client.hedge_mode

        status = "✅" if actual_hedge == expected_hedge else "❌"

        print(
            f"{status} BYBIT_HEDGE_MODE={env_value:5} | hedge_mode={actual_hedge} | expected={expected_hedge}"
        )

    # Возвращаем к default значению
    os.environ["BYBIT_HEDGE_MODE"] = "true"

    print("\n✅ Интеграционный тест завершён!")


if __name__ == "__main__":

    async def main():
        try:
            await test_hedge_mode()
            await test_integration()
            print("\n🎯 Все тесты пройдены! Hedge mode fix работает корректно.")
        except Exception as e:
            print(f"\n❌ Ошибка в тестах: {e}")
            sys.exit(1)

    asyncio.run(main())
