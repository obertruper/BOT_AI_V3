#!/usr/bin/env python3
"""
Диагностика проблемы с SL/TP для SHORT позиций
Проверяет всю цепочку передачи значений
"""

import asyncio

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

logger = setup_logger("diagnose_sl_tp")


async def check_recent_signals():
    """Проверяет последние сигналы в БД"""

    print("\n" + "=" * 80)
    print(" ПРОВЕРКА ПОСЛЕДНИХ СИГНАЛОВ В БД ".center(80, "="))
    print("=" * 80 + "\n")

    query = """
        SELECT
            symbol,
            signal_type,
            suggested_price,
            suggested_stop_loss,
            suggested_take_profit,
            created_at
        FROM signals
        WHERE signal_type = 'SHORT'
        ORDER BY created_at DESC
        LIMIT 5
    """

    try:
        rows = await AsyncPGPool.fetch(query)

        if rows:
            print("📊 Последние SHORT сигналы:")
            print("-" * 80)

            for row in rows:
                symbol = row["symbol"]
                price = row["suggested_price"]
                sl = row["suggested_stop_loss"]
                tp = row["suggested_take_profit"]

                print(f"\n{symbol}:")
                print(f"  Цена: {price:.6f}")
                print(f"  SL: {sl:.6f} ({'✅ ВЫШЕ' if sl > price else '❌ НИЖЕ'} цены)")
                print(f"  TP: {tp:.6f} ({'✅ НИЖЕ' if tp < price else '❌ ВЫШЕ'} цены)")

                # Проверка правильности
                if sl <= price:
                    print("  ⚠️ ОШИБКА: SL должен быть ВЫШЕ цены для SHORT!")
                if tp >= price:
                    print("  ⚠️ ОШИБКА: TP должен быть НИЖЕ цены для SHORT!")

        else:
            print("Нет SHORT сигналов в БД")

    except Exception as e:
        logger.error(f"Ошибка при проверке сигналов: {e}")


async def check_recent_orders():
    """Проверяет последние ордера в БД"""

    print("\n" + "=" * 80)
    print(" ПРОВЕРКА ПОСЛЕДНИХ ОРДЕРОВ В БД ".center(80, "="))
    print("=" * 80 + "\n")

    query = """
        SELECT
            symbol,
            side,
            price,
            stop_loss,
            take_profit,
            status,
            created_at
        FROM orders
        WHERE side = 'SELL'
        ORDER BY created_at DESC
        LIMIT 5
    """

    try:
        rows = await AsyncPGPool.fetch(query)

        if rows:
            print("📊 Последние SELL ордера:")
            print("-" * 80)

            for row in rows:
                symbol = row["symbol"]
                price = row["price"] or 0
                sl = row["stop_loss"]
                tp = row["take_profit"]
                status = row["status"]

                if sl and tp and price > 0:
                    print(f"\n{symbol} [{status}]:")
                    print(f"  Цена: {price:.6f}")
                    print(f"  SL: {sl:.6f} ({'✅ ВЫШЕ' if sl > price else '❌ НИЖЕ'} цены)")
                    print(f"  TP: {tp:.6f} ({'✅ НИЖЕ' if tp < price else '❌ ВЫШЕ'} цены)")

                    # Проверка правильности
                    if sl <= price:
                        print("  ⚠️ ОШИБКА: SL должен быть ВЫШЕ цены для SELL!")
                    if tp >= price:
                        print("  ⚠️ ОШИБКА: TP должен быть НИЖЕ цены для SELL!")

        else:
            print("Нет SELL ордеров в БД")

    except Exception as e:
        logger.error(f"Ошибка при проверке ордеров: {e}")


async def analyze_error_pattern():
    """Анализирует паттерн ошибок"""

    print("\n" + "=" * 80)
    print(" АНАЛИЗ ПАТТЕРНА ОШИБОК ".center(80, "="))
    print("=" * 80 + "\n")

    print("📋 Из логов видно:")
    print("-" * 40)
    print("1. API Bybit отклоняет ордера с ошибкой:")
    print("   'StopLoss should greater base_price'")
    print("")
    print("2. В параметрах ордера передается:")
    print("   - stopLoss: 0.9918612")
    print("   - takeProfit: 0.9565776")
    print("   - base_price: ~1.0062")
    print("")
    print("3. Для SHORT позиции (Sell):")
    print("   ❌ stopLoss (0.9918) < base_price (1.0062) - НЕПРАВИЛЬНО!")
    print("   ✅ Должно быть: stopLoss > base_price")
    print("")

    print("💡 ВЫВОД:")
    print("-" * 40)
    print("Значения SL и TP рассчитываются ПРАВИЛЬНО в ml_signal_processor,")
    print("но где-то в цепочке передачи они МЕНЯЮТСЯ МЕСТАМИ или")
    print("используется неправильная формула для SHORT позиций.")
    print("")

    print("🔍 ПРОВЕРИТЬ:")
    print("-" * 40)
    print("1. trading/orders/order_manager.py - создание ордера")
    print("2. exchanges/bybit/client.py - передача в API")
    print("3. trading/execution/executor.py - исполнение ордера")
    print("4. Возможно есть промежуточная обработка SL/TP")


async def suggest_fix():
    """Предлагает исправление"""

    print("\n" + "=" * 80)
    print(" ПРЕДЛАГАЕМОЕ ИСПРАВЛЕНИЕ ".center(80, "="))
    print("=" * 80 + "\n")

    print("🔧 ВАРИАНТ 1: Проверить формулы в ml_signal_processor.py")
    print("-" * 40)
    print(
        """
# Текущий код (ПРАВИЛЬНЫЙ):
if signal_type == SignalType.SHORT:
    stop_loss = current_price * (1 + stop_loss_pct)  # SL выше
    take_profit = current_price * (1 - take_profit_pct)  # TP ниже
"""
    )

    print("\n🔧 ВАРИАНТ 2: Добавить валидацию перед отправкой")
    print("-" * 40)
    print(
        """
# В exchanges/bybit/client.py перед отправкой:
if order_request.side == OrderSide.SELL:
    # Для SHORT позиций проверяем корректность
    if stop_loss and stop_loss < current_price:
        logger.error(f"SHORT: SL {stop_loss} < price {current_price}")
        # Возможно поменять местами
        stop_loss, take_profit = take_profit, stop_loss
"""
    )

    print("\n🔧 ВАРИАНТ 3: Проверить передачу в order_manager.py")
    print("-" * 40)
    print(
        """
# Убедиться что значения не меняются местами:
stop_loss = signal.suggested_stop_loss  # Не перепутано с TP?
take_profit = signal.suggested_take_profit
"""
    )


async def main():
    """Главная функция диагностики"""

    print("\n" + "=" * 80)
    print(" ДИАГНОСТИКА ПРОБЛЕМЫ SL/TP ДЛЯ SHORT ПОЗИЦИЙ ".center(80, "="))
    print("=" * 80)

    # Проверяем сигналы
    await check_recent_signals()

    # Проверяем ордера
    await check_recent_orders()

    # Анализируем паттерн
    await analyze_error_pattern()

    # Предлагаем исправление
    await suggest_fix()

    print("\n" + "=" * 80)
    print(" ДИАГНОСТИКА ЗАВЕРШЕНА ".center(80, "✅"))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
