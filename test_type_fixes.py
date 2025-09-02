#!/usr/bin/env python3
"""Тест исправлений проблем с типами в InstrumentManager"""

from decimal import Decimal
from trading.instrument_manager import InstrumentManager

def test_type_conversions():
    """Тестируем преобразования типов"""
    
    manager = InstrumentManager()
    
    test_cases = [
        # (symbol, test_value, description)
        ("XRPUSDT", "1.5", "String quantity"),
        ("XRPUSDT", Decimal("2.3"), "Decimal quantity"),  
        ("XRPUSDT", 3.7, "Float quantity"),
        ("XRPUSDT", None, "None quantity"),
        ("DOGEUSDT", "0.5", "String small quantity"),
        ("DOGEUSDT", "None", "String 'None'"),
    ]
    
    print("Testing InstrumentManager type conversions...")
    print("-" * 50)
    
    for symbol, test_value, description in test_cases:
        print(f"\nTest: {description}")
        print(f"Symbol: {symbol}")
        print(f"Input: {test_value} (type: {type(test_value).__name__})")
        
        try:
            # Test round_qty
            result = manager.round_qty(symbol, test_value, enforce_min=True)
            print(f"✓ round_qty result: {result} (type: {type(result).__name__})")
            
            # Test format_qty
            if test_value is not None and test_value != "None":
                formatted = manager.format_qty(symbol, result)
                print(f"✓ format_qty result: {formatted} (type: {type(formatted).__name__})")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Test get methods return proper floats
    print("\n" + "=" * 50)
    print("Testing getter methods return floats...")
    print("-" * 50)
    
    getter_methods = [
        ("get_tick_size", "BTCUSDT"),
        ("get_qty_step", "ETHUSDT"),
        ("get_min_qty", "XRPUSDT"),
        ("get_min_notional", "DOGEUSDT"),
    ]
    
    for method_name, symbol in getter_methods:
        method = getattr(manager, method_name)
        result = method(symbol)
        print(f"{method_name}('{symbol}'): {result} (type: {type(result).__name__})")
        assert isinstance(result, float), f"{method_name} should return float, got {type(result)}"
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_type_conversions()