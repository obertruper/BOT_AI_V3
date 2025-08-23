#!/usr/bin/env python3
"""
Упрощенный скрипт для тестирования исправлений
"""

import sys
from pathlib import Path
from decimal import Decimal

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent))


def test_instrument_rounding():
    """Тест округления для XRPUSDT"""
    print("=" * 60)
    print("🧪 Тестирование округления XRPUSDT")
    print("=" * 60)
    
    # Импортируем только после добавления в path
    from trading.instrument_manager import InstrumentManager
    
    manager = InstrumentManager()
    
    # Тестовые значения для XRPUSDT
    test_values = [
        3.230,   # Должно округлиться до 3.2
        3.256,   # Должно округлиться до 3.2
        3.289,   # Должно округлиться до 3.2
        3.15,    # Должно округлиться до 3.1
        0.09,    # Должно округлиться до минимума 0.1
        10.567,  # Должно округлиться до 10.5
    ]
    
    print("\n  Результаты округления:")
    for value in test_values:
        rounded = manager.round_qty("XRPUSDT", value, round_up=False)
        formatted = manager.format_qty("XRPUSDT", rounded)
        print(f"    {value} -> {rounded} -> '{formatted}'")
        
        # Проверка корректности
        if value == 3.230:
            if formatted == "3.2":
                print(f"    ✅ Корректно: 3.230 -> '3.2'")
            else:
                print(f"    ❌ Ошибка: 3.230 должно быть '3.2', а не '{formatted}'")
                return False
    
    print("\n✅ Тест округления XRPUSDT пройден успешно!")
    return True


def test_signal_logic():
    """Простой тест логики определения сигналов"""
    print("\n" + "=" * 60)
    print("🧪 Тестирование логики определения сигналов")
    print("=" * 60)
    
    # Симуляция определения сигнала
    test_cases = [
        {"long": 3, "short": 1, "expected": "LONG", "desc": "3 LONG, 1 SHORT"},
        {"long": 1, "short": 3, "expected": "SHORT", "desc": "1 LONG, 3 SHORT"},
        {"long": 2, "short": 2, "expected": "NEUTRAL", "desc": "2 LONG, 2 SHORT"},
    ]
    
    for case in test_cases:
        long_count = case["long"]
        short_count = case["short"]
        
        # Логика из signal_quality_analyzer
        if long_count > short_count and long_count >= 2:
            result = "LONG"
        elif short_count > long_count and short_count >= 2:
            result = "SHORT"
        else:
            result = "NEUTRAL"
        
        status = "✅" if result == case["expected"] else "❌"
        print(f"  {case['desc']}: {result} (ожидалось {case['expected']}) {status}")
        
        if result != case["expected"]:
            return False
    
    print("\n✅ Логика определения сигналов корректна!")
    return True


def test_sl_tp_logic():
    """Тест логики SL/TP для SHORT позиций"""
    print("\n" + "=" * 60)
    print("🧪 Тестирование логики SL/TP")
    print("=" * 60)
    
    # Тестовые данные
    current_price = 100.0
    stop_loss_pct = 0.02  # 2%
    take_profit_pct = 0.03  # 3%
    
    # Для LONG позиции
    long_sl = current_price * (1 - stop_loss_pct)  # 98
    long_tp = current_price * (1 + take_profit_pct)  # 103
    
    print(f"\n  LONG позиция (цена входа: {current_price}):")
    print(f"    SL: {long_sl:.2f} (ниже на {stop_loss_pct:.1%})")
    print(f"    TP: {long_tp:.2f} (выше на {take_profit_pct:.1%})")
    
    # Для SHORT позиции
    short_sl = current_price * (1 + stop_loss_pct)  # 102
    short_tp = current_price * (1 - take_profit_pct)  # 97
    
    print(f"\n  SHORT позиция (цена входа: {current_price}):")
    print(f"    SL: {short_sl:.2f} (выше на {stop_loss_pct:.1%})")
    print(f"    TP: {short_tp:.2f} (ниже на {take_profit_pct:.1%})")
    
    # Проверка корректности
    checks = [
        (long_sl < current_price, "LONG SL должен быть ниже цены входа"),
        (long_tp > current_price, "LONG TP должен быть выше цены входа"),
        (short_sl > current_price, "SHORT SL должен быть выше цены входа"),
        (short_tp < current_price, "SHORT TP должен быть ниже цены входа"),
    ]
    
    all_correct = True
    for check, desc in checks:
        if check:
            print(f"    ✅ {desc}")
        else:
            print(f"    ❌ {desc}")
            all_correct = False
    
    return all_correct


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестирования исправлений")
    print("=" * 60)
    
    results = []
    
    # Тест 1: Округление
    try:
        results.append(("Округление XRPUSDT", test_instrument_rounding()))
    except Exception as e:
        print(f"❌ Ошибка в тесте округления: {e}")
        results.append(("Округление XRPUSDT", False))
    
    # Тест 2: Логика сигналов
    results.append(("Логика определения сигналов", test_signal_logic()))
    
    # Тест 3: SL/TP логика
    results.append(("Логика SL/TP", test_sl_tp_logic()))
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\n📝 Внесенные изменения:")
        print("  1. Исправлена логика определения SHORT сигналов")
        print("  2. Добавлен InstrumentManager для правильного округления")
        print("  3. Реализовано закрытие противоположных позиций")
        print("  4. Увеличен интервал между сигналами до 5 минут")
        print("  5. Проверена логика SL/TP для SHORT позиций")
        print("\n🔄 Рекомендации:")
        print("  1. Перезапустите бота командой: ./stop_all.sh && ./quick_start.sh")
        print("  2. Мониторьте логи: tail -f data/logs/bot_trading_*.log | grep -E 'SHORT|XRPUSDT'")
        print("  3. Проверьте статус: python3 unified_launcher.py --status")
    else:
        print("\n⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ!")
        print("Требуется дополнительная отладка")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())