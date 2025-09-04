#!/usr/bin/env python3
"""
Test script to verify Bybit quantity formatting fixes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exchanges.bybit.client import format_quantity
from exchanges.bybit.instrument_settings import INSTRUMENT_SETTINGS


def test_quantity_formatting():
    """Test quantity formatting for different instruments"""

    test_cases = [
        # Symbol, Original Qty, Expected Result
        ("XRPUSDT", 1.759, "1.7"),  # XRP with 0.1 step
        ("DOGEUSDT", 24.0, "24"),  # DOGE with 1.0 step (whole number)
        ("ADAUSDT", 5.99, "5"),  # ADA with 1.0 step (rounds down)
        ("SOLUSDT", 0.234, "0.2"),  # SOL with 0.1 step
        ("BTCUSDT", 0.00123, "0.001"),  # BTC with 0.001 step
        ("ETHUSDT", 0.0156, "0.01"),  # ETH with 0.01 step
    ]

    print("Testing quantity formatting...")
    print("-" * 60)

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
            status = "✅ PASS" if passed else "❌ FAIL"

            if not passed:
                all_passed = False

            print(
                f"{status} | {symbol:10} | {original_qty:10.6f} -> {result:10s} | Expected: {expected:10s} | Step: {qty_step}"
            )

        except Exception as e:
            print(f"❌ ERROR | {symbol:10} | {original_qty:10.6f} | Error: {e}")
            all_passed = False

    print("-" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Please review the formatting logic.")

    return all_passed


def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\nTesting edge cases...")
    print("-" * 60)

    # Test minimum quantities
    print("\nMinimum quantity tests:")
    for symbol in ["XRPUSDT", "DOGEUSDT", "ADAUSDT", "BTCUSDT"]:
        settings = INSTRUMENT_SETTINGS.get(symbol, {})
        min_qty = settings.get("minOrderQty", 0.1)
        qty_step = settings.get("qtyStep", 0.1)

        # Try quantity below minimum
        test_qty = min_qty / 2

        try:
            result = format_quantity(
                quantity=test_qty,
                qty_step=qty_step,
                min_qty=min_qty,
                max_qty=float("inf"),
                symbol=symbol,
            )
            print(f"✅ {symbol}: {test_qty:.6f} -> {result} (min enforced)")
        except Exception as e:
            print(f"❌ {symbol}: {test_qty:.6f} -> Error: {e}")

    print("-" * 60)


if __name__ == "__main__":
    success = test_quantity_formatting()
    test_edge_cases()

    if success:
        print("\n🎉 All quantity formatting tests passed! The fix should work.")
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        sys.exit(1)
