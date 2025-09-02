#!/usr/bin/env python3
"""Debug XRP quantity formatting issue"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal, ROUND_DOWN
from exchanges.bybit.instrument_settings import INSTRUMENT_SETTINGS

def debug_xrp_formatting():
    """Debug XRP quantity formatting"""
    
    symbol = "XRPUSDT"
    original_qty = 1.759
    settings = INSTRUMENT_SETTINGS[symbol]
    
    print(f"Testing {symbol} formatting:")
    print(f"Original quantity: {original_qty}")
    print(f"Settings: {settings}")
    print("-" * 50)
    
    qty_step = settings["qtyStep"]
    min_qty = settings["minOrderQty"]
    
    # Manual formatting logic
    qty_decimal = Decimal(str(original_qty))
    step_decimal = Decimal(str(qty_step))
    
    print(f"Decimal quantity: {qty_decimal}")
    print(f"Decimal step: {step_decimal}")
    
    # Round DOWN to nearest step
    rounded_qty = (qty_decimal / step_decimal).quantize(
        Decimal("1"), rounding=ROUND_DOWN
    ) * step_decimal
    
    print(f"Rounded quantity: {rounded_qty}")
    
    # Format with correct decimal places
    if qty_step >= 1:
        decimal_places = 0
        formatted_qty = str(int(rounded_qty))
    else:
        step_str = f"{qty_step:.10f}".rstrip("0")
        if "." in step_str:
            decimal_places = len(step_str.split(".")[1])
        else:
            decimal_places = 0
        
        formatted_qty = format(rounded_qty, f".{decimal_places}f")
    
    print(f"Decimal places: {decimal_places if qty_step < 1 else 0}")
    print(f"Formatted quantity: '{formatted_qty}'")
    
    # Check if the formatting removes trailing zeros incorrectly
    if "." in formatted_qty and all(c == "0" for c in formatted_qty.split(".")[1]):
        print("⚠️  Would remove decimal point (all zeros)")
        formatted_qty = formatted_qty.split(".")[0]
        print(f"After removing zeros: '{formatted_qty}'")
    
    print("-" * 50)
    print(f"Final result: '{formatted_qty}'")
    print(f"Expected: '1.759'")
    print(f"Match: {formatted_qty == '1.759'}")

if __name__ == "__main__":
    debug_xrp_formatting()