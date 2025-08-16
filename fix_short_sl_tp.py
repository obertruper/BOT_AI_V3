#!/usr/bin/env python3
"""
Скрипт для исправления проблемы с StopLoss и TakeProfit для SHORT позиций
Проблема: для SHORT позиций SL и TP передаются неправильно в Bybit API
"""

from core.logger import setup_logger

logger = setup_logger("fix_sl_tp")


def analyze_sl_tp_issue():
    """Анализ проблемы с SL/TP для SHORT позиций"""

    print("\n" + "=" * 80)
    print(" АНАЛИЗ ПРОБЛЕМЫ SL/TP ДЛЯ SHORT ПОЗИЦИЙ ".center(80, "="))
    print("=" * 80 + "\n")

    # Пример из логов
    print("📊 ДАННЫЕ ИЗ ЛОГОВ:")
    print("-" * 40)
    print("Symbol: ADAUSDT")
    print("Side: Sell (SHORT)")
    print("Base Price: ~1.0062")
    print("")

    print("❌ ТЕКУЩИЕ ЗНАЧЕНИЯ (НЕПРАВИЛЬНО):")
    print("  StopLoss: 0.9918612 (НИЖЕ цены входа)")
    print("  TakeProfit: 0.9565776 (НИЖЕ цены входа)")
    print("")

    print("✅ ПРАВИЛЬНЫЕ ЗНАЧЕНИЯ ДОЛЖНЫ БЫТЬ:")
    print("  StopLoss: 1.0263 (ВЫШЕ цены входа на 2%)")
    print("  TakeProfit: 0.9559 (НИЖЕ цены входа на 5%)")
    print("")

    print("🔍 ПРОБЛЕМА:")
    print("-" * 40)
    print("1. В ml_signal_processor.py расчет выглядит правильно:")
    print("   - SHORT: stop_loss = current_price * (1 + stop_loss_pct)")
    print("   - SHORT: take_profit = current_price * (1 - take_profit_pct)")
    print("")
    print("2. Но в логах видно что значения передаются наоборот!")
    print("   - stopLoss передается меньше цены входа")
    print("   - Bybit требует чтобы для Sell stopLoss был больше base_price")
    print("")

    print("💡 РЕШЕНИЕ:")
    print("-" * 40)
    print("Проверить всю цепочку передачи SL/TP от ml_signal_processor до bybit client:")
    print("1. ml_signal_processor.py - расчет SL/TP")
    print("2. Signal model - хранение SL/TP")
    print("3. order_manager.py - передача в OrderRequest")
    print("4. bybit/client.py - отправка в API")
    print("")

    print("🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
    print("-" * 40)
    print("1. Где-то в цепочке SL и TP меняются местами")
    print("2. Для SHORT позиций используется неправильная формула")
    print("3. Проблема с округлением или конвертацией типов")
    print("")


def calculate_correct_sl_tp(price: float, side: str, sl_pct: float = 0.02, tp_pct: float = 0.05):
    """
    Правильный расчет SL/TP для позиций

    Args:
        price: Текущая цена
        side: 'Buy' или 'Sell'
        sl_pct: Процент стоп-лосса
        tp_pct: Процент тейк-профита
    """
    print(f"\n📊 Расчет SL/TP для {side} позиции:")
    print(f"  Цена входа: {price}")
    print(f"  SL%: {sl_pct * 100}%, TP%: {tp_pct * 100}%")

    if side == "Buy":
        # LONG позиция
        stop_loss = price * (1 - sl_pct)
        take_profit = price * (1 + tp_pct)
        print(f"  LONG: SL={stop_loss:.6f} (ниже), TP={take_profit:.6f} (выше)")
    else:
        # SHORT позиция
        stop_loss = price * (1 + sl_pct)
        take_profit = price * (1 - tp_pct)
        print(f"  SHORT: SL={stop_loss:.6f} (выше), TP={take_profit:.6f} (ниже)")

    return stop_loss, take_profit


def main():
    """Главная функция"""

    # Анализ проблемы
    analyze_sl_tp_issue()

    # Примеры правильных расчетов
    print("\n" + "=" * 80)
    print(" ПРИМЕРЫ ПРАВИЛЬНЫХ РАСЧЕТОВ ".center(80, "="))
    print("=" * 80)

    # ADAUSDT
    calculate_correct_sl_tp(1.0062, "Sell", 0.02, 0.05)

    # BTCUSDT
    calculate_correct_sl_tp(50000, "Buy", 0.02, 0.03)
    calculate_correct_sl_tp(50000, "Sell", 0.02, 0.03)

    print("\n" + "=" * 80)
    print("\n✅ Анализ завершен. Необходимо проверить всю цепочку передачи SL/TP!")


if __name__ == "__main__":
    main()
