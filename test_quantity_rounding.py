#!/usr/bin/env python3
"""
Тест округления количеств для Bybit
Проверяет исправление ошибки "Qty invalid"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bybit.client import format_quantity
from exchanges.bybit.instrument_settings import get_instrument_settings


def test_xrp_rounding():
    """Тест округления для XRPUSDT"""
    print("Testing XRPUSDT quantity rounding...")
    
    # Получаем настройки для XRPUSDT
    settings = get_instrument_settings("XRPUSDT")
    print(f"XRPUSDT settings: qtyStep={settings['qtyStep']}, minOrderQty={settings['minOrderQty']}")
    
    # Тестовые случаи
    test_cases = [
        3.449,   # Из ошибки в логах
        3.4,     # Should round to 3.4
        3.45,    # Should round to 3.4
        3.55,    # Should round to 3.5
        10.123,  # Should round to 10.1
        0.05,    # Below minimum, should use minimum 0.1
        100.99,  # Should round to 100.9
    ]
    
    print("\nTest results:")
    print("-" * 50)
    
    for qty in test_cases:
        try:
            formatted = format_quantity(
                quantity=qty,
                qty_step=settings['qtyStep'],
                min_qty=settings['minOrderQty'],
                max_qty=settings.get('maxOrderQty', float('inf'))
            )
            print(f"Input: {qty:8.3f} -> Output: {formatted:>10s} ✅")
        except ValueError as e:
            print(f"Input: {qty:8.3f} -> Error: {e} ❌")
    
    print("-" * 50)


def test_btc_rounding():
    """Тест округления для BTCUSDT"""
    print("\nTesting BTCUSDT quantity rounding...")
    
    settings = get_instrument_settings("BTCUSDT")
    print(f"BTCUSDT settings: qtyStep={settings['qtyStep']}, minOrderQty={settings['minOrderQty']}")
    
    test_cases = [
        0.001234,  # Should round to 0.001
        0.00156,   # Should round to 0.001
        0.0025,    # Should round to 0.002
        0.1234,    # Should round to 0.123
        1.23456,   # Should round to 1.234
    ]
    
    print("\nTest results:")
    print("-" * 50)
    
    for qty in test_cases:
        try:
            formatted = format_quantity(
                quantity=qty,
                qty_step=settings['qtyStep'],
                min_qty=settings['minOrderQty'],
                max_qty=settings.get('maxOrderQty', float('inf'))
            )
            print(f"Input: {qty:8.6f} -> Output: {formatted:>10s} ✅")
        except ValueError as e:
            print(f"Input: {qty:8.6f} -> Error: {e} ❌")
    
    print("-" * 50)


def test_edge_cases():
    """Тест граничных случаев"""
    print("\nTesting edge cases...")
    
    # Тест с неизвестным символом (использует _DEFAULT)
    settings = get_instrument_settings("UNKNOWN_SYMBOL")
    print(f"Unknown symbol uses default: qtyStep={settings['qtyStep']}")
    
    # Тест с целыми числами (например, ADAUSDT)
    settings = get_instrument_settings("ADAUSDT")
    print(f"\nADAUSDT settings: qtyStep={settings['qtyStep']} (whole numbers)")
    
    test_cases = [1.5, 10.7, 100.1, 100.9]
    
    for qty in test_cases:
        formatted = format_quantity(
            quantity=qty,
            qty_step=settings['qtyStep'],
            min_qty=settings['minOrderQty'],
            max_qty=settings.get('maxOrderQty', float('inf'))
        )
        print(f"Input: {qty:6.1f} -> Output: {formatted:>10s}")


if __name__ == "__main__":
    print("=" * 60)
    print("Bybit Quantity Rounding Test")
    print("=" * 60)
    
    test_xrp_rounding()
    test_btc_rounding()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)