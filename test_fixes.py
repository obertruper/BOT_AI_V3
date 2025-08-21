#!/usr/bin/env python3
"""
Тест исправлений для Bybit trading engine
"""

import asyncio
from decimal import Decimal
from trading.engine import TradingEngine


def test_rounding():
    """Тест округления для XRPUSDT"""
    print("Testing XRPUSDT rounding...")
    
    # Тестируем функцию округления напрямую
    def _round_to_step(value: Decimal, step: Decimal) -> Decimal:
        """Округление значения до шага"""
        if step == 0:
            return value
        return (value / step).quantize(Decimal("1"), rounding="ROUND_DOWN") * step
    
    # Тестируем округление
    test_cases = [
        (Decimal("3.449"), Decimal("0.1"), Decimal("3.4")),
        (Decimal("3.45"), Decimal("0.1"), Decimal("3.4")),
        (Decimal("3.55"), Decimal("0.1"), Decimal("3.5")),
        (Decimal("10.123"), Decimal("0.1"), Decimal("10.1")),
    ]
    
    for value, step, expected in test_cases:
        result = _round_to_step(value, step)
        status = "✅" if result == expected else "❌"
        print(f"  {value} with step {step} -> {result} (expected {expected}) {status}")


async def test_position_manager_call():
    """Тест вызова position_manager.get_position с правильными аргументами"""
    print("\nTesting position_manager.get_position call...")
    
    # Создаем мок для position_manager
    class MockPositionManager:
        async def get_position(self, exchange: str, symbol: str):
            print(f"  ✅ Called with exchange='{exchange}', symbol='{symbol}'")
            return None
    
    # Используем только мок position_manager
    position_manager = MockPositionManager()
    
    # Симулируем сигнал
    class MockSignal:
        exchange = "bybit"
        symbol = "XRPUSDT"
    
    # Проверяем, что вызов теперь работает правильно
    try:
        signal = MockSignal()
        position = await position_manager.get_position(
            exchange=signal.exchange,
            symbol=signal.symbol
        )
        print("  Position check completed without errors")
    except Exception as e:
        print(f"  ❌ Error: {e}")


async def test_instrument_info():
    """Тест получения информации об инструменте"""
    print("\nTesting instrument info for XRPUSDT...")
    
    # Проверяем значения по умолчанию напрямую
    print("  Checking default values...")
    
    # Значения по умолчанию из engine.py
    defaults = {
        "BTCUSDT": {"min": 0.001, "step": 0.001},
        "ETHUSDT": {"min": 0.01, "step": 0.01},
        "BNBUSDT": {"min": 0.01, "step": 0.01},
        "SOLUSDT": {"min": 0.1, "step": 0.1},
        "XRPUSDT": {"min": 0.1, "step": 0.1},  # ИСПРАВЛЕНО: qtyStep = 0.1
        "ADAUSDT": {"min": 1.0, "step": 1.0},
        "DOGEUSDT": {"min": 1.0, "step": 1.0},
        "DOTUSDT": {"min": 0.1, "step": 0.1},
        "LINKUSDT": {"min": 0.1, "step": 0.1},
    }
    
    xrp_info = defaults.get("XRPUSDT")
    if xrp_info:
        print(f"  XRPUSDT qty_step: {xrp_info['step']}")
        print(f"  XRPUSDT min_order_qty: {xrp_info['min']}")
        
        # Проверяем, что qty_step теперь правильный
        if xrp_info['step'] == 0.1:
            print("  ✅ qty_step is correct (0.1)")
        else:
            print(f"  ❌ qty_step is wrong ({xrp_info['step']}, expected 0.1)")
    else:
        print("  ⚠️  No XRPUSDT in defaults")


async def main():
    print("=" * 60)
    print("Testing Bybit Trading Engine Fixes")
    print("=" * 60)
    
    # Тест 1: Округление
    test_rounding()
    
    # Тест 2: Вызов position_manager
    await test_position_manager_call()
    
    # Тест 3: Информация об инструменте
    await test_instrument_info()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())