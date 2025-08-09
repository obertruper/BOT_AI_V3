#!/usr/bin/env python3
"""
Проверка результатов тестирования
"""

import asyncio

from database.connections.postgres import AsyncPGPool


async def check_results():
    """Проверяет результаты тестирования."""

    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ BOT_AI_V3")
    print("=" * 80)

    # 1. Сигналы
    signals = await AsyncPGPool.fetch(
        """
        SELECT id, symbol, signal_type, strength, confidence, strategy_name, created_at
        FROM signals
        ORDER BY created_at DESC
        LIMIT 10
    """
    )

    print("\n🔍 ПОСЛЕДНИЕ СИГНАЛЫ:")
    print("-" * 80)
    print(
        f"{'ID':>5} | {'Тип':^5} | {'Символ':^8} | {'Стратегия':^25} | {'Сила':>6} | {'Конф':>5}"
    )
    print("-" * 80)

    for sig in signals:
        print(
            f"{sig['id']:>5} | {sig['signal_type']:^5} | {sig['symbol']:^8} | {sig['strategy_name']:^25} | {sig['strength']:>6.2f} | {sig['confidence']:>5.0%}"
        )

    # 2. Ордера
    orders = await AsyncPGPool.fetch(
        """
        SELECT id, order_id, symbol, side, order_type, status, quantity, price, created_at
        FROM orders
        ORDER BY created_at DESC
        LIMIT 10
    """
    )

    print(f"\n📈 ПОСЛЕДНИЕ ОРДЕРА ({len(orders)}):")
    print("-" * 80)
    print(
        f"{'Order ID':^30} | {'Side':^4} | {'Символ':^8} | {'Тип':^6} | {'Кол-во':>10} | {'Цена':>10} | {'Статус':^10}"
    )
    print("-" * 80)

    for order in orders:
        price_str = f"${order['price']:,.2f}" if order["price"] else "Market"
        print(
            f"{order['order_id'][:30]:^30} | {order['side']:^4} | {order['symbol']:^8} | {order['order_type']:^6} | {order['quantity']:>10.4f} | {price_str:>10} | {order['status']:^10}"
        )

    # 3. Сделки
    trades = await AsyncPGPool.fetch(
        """
        SELECT id, order_id, symbol, side, quantity, price, executed_at
        FROM trades
        ORDER BY executed_at DESC
        LIMIT 10
    """
    )

    print(f"\n💰 ПОСЛЕДНИЕ СДЕЛКИ ({len(trades)}):")
    if trades:
        print("-" * 80)
        print(
            f"{'Trade ID':>8} | {'Символ':^8} | {'Side':^4} | {'Кол-во':>10} | {'Цена':>10} | {'Время':^20}"
        )
        print("-" * 80)

        for trade in trades:
            exec_time = trade["executed_at"].strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"{trade['id']:>8} | {trade['symbol']:^8} | {trade['side']:^4} | {trade['quantity']:>10.4f} | ${trade['price']:>9,.2f} | {exec_time:^20}"
            )
    else:
        print("   Нет сделок")

    # 4. Статистика
    stats = await AsyncPGPool.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM signals WHERE created_at > NOW() - INTERVAL '1 hour') as signals_hour,
            (SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 hour') as orders_hour,
            (SELECT COUNT(*) FROM trades WHERE executed_at > NOW() - INTERVAL '1 hour') as trades_hour,
            (SELECT COUNT(*) FROM signals WHERE signal_type = 'LONG' AND created_at > NOW() - INTERVAL '1 hour') as long_signals,
            (SELECT COUNT(*) FROM signals WHERE signal_type = 'SHORT' AND created_at > NOW() - INTERVAL '1 hour') as short_signals,
            (SELECT COUNT(*) FROM orders WHERE status = 'filled' AND created_at > NOW() - INTERVAL '1 hour') as filled_orders
    """
    )

    print("\n📊 СТАТИСТИКА ЗА ПОСЛЕДНИЙ ЧАС:")
    print("-" * 80)
    print(
        f"Сигналов создано: {stats['signals_hour']} (LONG: {stats['long_signals']}, SHORT: {stats['short_signals']})"
    )
    print(
        f"Ордеров создано: {stats['orders_hour']} (Исполнено: {stats['filled_orders']})"
    )
    print(f"Сделок совершено: {stats['trades_hour']}")

    # 5. Проверка конверсии
    conversion_rate = (
        (stats["orders_hour"] / stats["signals_hour"] * 100)
        if stats["signals_hour"] > 0
        else 0
    )
    print(f"\nКонверсия сигнал→ордер: {conversion_rate:.1f}%")

    # 6. Проверка уникальных стратегий
    strategies = await AsyncPGPool.fetch(
        """
        SELECT DISTINCT strategy_name, COUNT(*) as count
        FROM signals
        WHERE created_at > NOW() - INTERVAL '1 hour'
        GROUP BY strategy_name
        ORDER BY count DESC
    """
    )

    if strategies:
        print("\n🎯 АКТИВНЫЕ СТРАТЕГИИ:")
        for strat in strategies:
            print(f"   {strat['strategy_name']}: {strat['count']} сигналов")

    print("\n" + "=" * 80)
    print("✅ Проверка завершена")


if __name__ == "__main__":
    asyncio.run(check_results())
