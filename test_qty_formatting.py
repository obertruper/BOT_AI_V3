#!/usr/bin/env python3
"""
Тестирование форматирования количества для разных символов
"""
import sys
sys.path.append('.')

from exchanges.bybit.instrument_settings import get_instrument_settings
from exchanges.bybit.client import format_quantity

def test_quantity_formatting():
    """Тест форматирования количества"""
    
    # Тестовые случаи: (символ, количество в USDT, цена)
    test_cases = [
        ("BTCUSDT", 100, 109860.70),  # BTC
        ("ETHUSDT", 50, 4406.01),      # ETH
        ("SOLUSDT", 20, 187.80),       # SOL
        ("DOGEUSDT", 10, 0.21),        # DOGE
        ("XRPUSDT", 10, 2.91),         # XRP
        ("ADAUSDT", 10, 0.84),         # ADA
    ]
    
    print("🔍 Тестирование форматирования количества:\n")
    print("-" * 80)
    print(f"{'Символ':<10} {'Сумма USDT':<12} {'Цена':<12} {'Кол-во':<15} {'Форматированное':<15}")
    print("-" * 80)
    
    for symbol, usdt_value, price in test_cases:
        # Рассчитываем количество
        quantity = usdt_value / price
        
        # Получаем настройки инструмента
        settings = get_instrument_settings(symbol)
        
        # Форматируем количество
        try:
            formatted = format_quantity(
                quantity=quantity,
                qty_step=settings.get("qtyStep", 0.1),
                min_qty=settings.get("minOrderQty", 0.1),
                max_qty=settings.get("maxOrderQty", float("inf")),
                symbol=symbol
            )
            
            # Проверяем минимальную стоимость
            min_value = float(formatted) * price
            status = "✅" if min_value >= 5 else "⚠️"
            
            print(f"{symbol:<10} ${usdt_value:<11.2f} ${price:<11.2f} {quantity:<15.8f} {formatted:<15} {status} (${min_value:.2f})")
            
        except Exception as e:
            print(f"{symbol:<10} ОШИБКА: {e}")
    
    print("-" * 80)
    
    print("\n📊 Рекомендации:")
    print("   • Минимальный размер ордера на Bybit: 5 USDT")
    print("   • Всегда проверяйте минимальное количество для каждого символа")
    print("   • Используйте правильный шаг количества (qtyStep)")
    print("   • Для безопасности добавляйте 10-20% к минимальному размеру")

if __name__ == "__main__":
    test_quantity_formatting()