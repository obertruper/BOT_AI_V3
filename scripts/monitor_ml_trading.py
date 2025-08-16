#!/usr/bin/env python3
"""Мониторинг ML торговой системы"""

import asyncio
import os
import sys
from datetime import datetime

from colorama import Fore, Style, init

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool

init(autoreset=True)
logger = setup_logger(__name__)


async def monitor_system():
    """Мониторинг всех компонентов системы"""
    print(f"{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}🤖 ML TRADING SYSTEM MONITOR")
    print(f"{Fore.CYAN}{'=' * 60}\n")

    while True:
        try:
            # Очистка экрана
            os.system("clear" if os.name == "posix" else "cls")

            print(f"{Fore.YELLOW}⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.CYAN}{'=' * 60}\n")

            # 1. Проверка БД подключения
            print(f"{Fore.GREEN}📊 DATABASE STATUS:")
            try:
                query = (
                    "SELECT COUNT(*) FROM ml_signals WHERE created_at > NOW() - INTERVAL '1 hour'"
                )
                result = await AsyncPGPool.fetchval(query)
                print("  ✅ База данных: ПОДКЛЮЧЕНА")
                print(f"  📈 ML сигналов за час: {result}")
            except Exception as e:
                print(f"  ❌ База данных: ОШИБКА - {e}")

            # 2. Проверка последних сигналов
            print(f"\n{Fore.GREEN}🔔 ПОСЛЕДНИЕ ML СИГНАЛЫ:")
            try:
                query = """
                SELECT symbol, signal_type, confidence, strength, created_at
                FROM ml_signals
                ORDER BY created_at DESC
                LIMIT 5
                """
                signals = await AsyncPGPool.fetch(query)

                if signals:
                    for signal in signals:
                        signal_type = signal["signal_type"]
                        confidence = signal["confidence"]
                        strength = signal["strength"]

                        # Цветовое кодирование
                        if signal_type == "LONG":
                            type_color = Fore.GREEN
                            emoji = "🟢"
                        elif signal_type == "SHORT":
                            type_color = Fore.RED
                            emoji = "🔴"
                        else:
                            type_color = Fore.YELLOW
                            emoji = "⚪"

                        print(
                            f"  {emoji} {signal['symbol']}: {type_color}{signal_type}{Style.RESET_ALL} "
                            f"| Conf: {confidence:.1%} | Str: {strength:.2f} "
                            f"| {signal['created_at'].strftime('%H:%M:%S')}"
                        )
                else:
                    print(f"  {Fore.YELLOW}⚠️  Нет недавних сигналов")

            except Exception as e:
                print(f"  ❌ Ошибка получения сигналов: {e}")

            # 3. Проверка торговых операций
            print(f"\n{Fore.GREEN}💼 ТОРГОВЫЕ ОПЕРАЦИИ:")
            try:
                # Последние ордера
                query = """
                SELECT symbol, side, order_type, status, price, quantity, created_at
                FROM orders
                WHERE created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                LIMIT 5
                """
                orders = await AsyncPGPool.fetch(query)

                if orders:
                    for order in orders:
                        status_emoji = {
                            "pending": "⏳",
                            "open": "📂",
                            "filled": "✅",
                            "cancelled": "❌",
                        }.get(order["status"], "❓")

                        side_color = Fore.GREEN if order["side"] == "BUY" else Fore.RED

                        print(
                            f"  {status_emoji} {order['symbol']}: {side_color}{order['side']}{Style.RESET_ALL} "
                            f"| {order['order_type']} | ${order['price']:.2f} x {order['quantity']:.4f} "
                            f"| {order['created_at'].strftime('%H:%M:%S')}"
                        )
                else:
                    print(f"  {Fore.YELLOW}⚠️  Нет недавних ордеров")

            except Exception as e:
                print(f"  ❌ Ошибка получения ордеров: {e}")

            # 4. Производительность системы
            print(f"\n{Fore.GREEN}📈 ПРОИЗВОДИТЕЛЬНОСТЬ:")
            try:
                # PnL за сегодня
                query = """
                SELECT
                    COUNT(*) as trades_count,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl
                FROM trades
                WHERE created_at > CURRENT_DATE
                """
                stats = await AsyncPGPool.fetchrow(query)

                if stats and stats["trades_count"] > 0:
                    win_rate = (stats["wins"] / stats["trades_count"]) * 100
                    total_pnl = stats["total_pnl"] or 0
                    avg_pnl = stats["avg_pnl"] or 0

                    pnl_color = Fore.GREEN if total_pnl >= 0 else Fore.RED

                    print(f"  📊 Сделок сегодня: {stats['trades_count']}")
                    print(f"  🎯 Win Rate: {win_rate:.1f}%")
                    print(f"  💰 Total PnL: {pnl_color}${total_pnl:.2f}{Style.RESET_ALL}")
                    print(f"  📈 Avg PnL: ${avg_pnl:.2f}")
                else:
                    print(f"  {Fore.YELLOW}⚠️  Нет сделок сегодня")

            except Exception as e:
                print(f"  ❌ Ошибка получения статистики: {e}")

            # 5. Состояние ML компонентов
            print(f"\n{Fore.GREEN}🧠 ML КОМПОНЕНТЫ:")
            try:
                # Проверка обработки данных
                query = """
                SELECT symbol, COUNT(*) as data_points
                FROM processed_market_data
                WHERE timestamp > NOW() - INTERVAL '1 hour'
                GROUP BY symbol
                ORDER BY symbol
                LIMIT 10
                """
                data_stats = await AsyncPGPool.fetch(query)

                if data_stats:
                    print("  📊 Обработано данных за час:")
                    for stat in data_stats:
                        print(f"     • {stat['symbol']}: {stat['data_points']} точек")
                else:
                    print(f"  {Fore.YELLOW}⚠️  Нет обработанных данных")

            except Exception as e:
                print(f"  ❌ Ошибка получения статистики ML: {e}")

            # 6. Баланс и позиции
            print(f"\n{Fore.GREEN}💵 БАЛАНСЫ И ПОЗИЦИИ:")
            try:
                # Текущий баланс
                query = """
                SELECT asset, exchange, free, used, total
                FROM balances
                WHERE asset = 'USDT'
                ORDER BY total DESC
                """
                balances = await AsyncPGPool.fetch(query)

                if balances:
                    for balance in balances:
                        print(
                            f"  💰 {balance['exchange']}: "
                            f"${balance['total']:.2f} USDT "
                            f"(Free: ${balance['free']:.2f}, Used: ${balance['used']:.2f})"
                        )
                else:
                    print(f"  {Fore.YELLOW}⚠️  Балансы не найдены")

                # Открытые позиции
                query = """
                SELECT symbol, side, entry_price, current_price, quantity, pnl
                FROM positions
                WHERE status = 'open'
                """
                positions = await AsyncPGPool.fetch(query)

                if positions:
                    print("\n  📂 Открытые позиции:")
                    for pos in positions:
                        pnl_color = Fore.GREEN if pos["pnl"] >= 0 else Fore.RED
                        side_emoji = "🟢" if pos["side"] == "LONG" else "🔴"

                        print(
                            f"     {side_emoji} {pos['symbol']}: "
                            f"Entry: ${pos['entry_price']:.2f} → Current: ${pos['current_price']:.2f} "
                            f"| Qty: {pos['quantity']:.4f} | PnL: {pnl_color}${pos['pnl']:.2f}{Style.RESET_ALL}"
                        )
                else:
                    print(f"\n  {Fore.CYAN}📭 Нет открытых позиций")

            except Exception as e:
                print(f"  ❌ Ошибка получения балансов: {e}")

            print(f"\n{Fore.CYAN}{'=' * 60}")
            print(f"{Fore.YELLOW}Обновление через 30 секунд... (Ctrl+C для выхода)")

            # Ждем 30 секунд
            await asyncio.sleep(30)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Мониторинг остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
            await asyncio.sleep(5)


async def main():
    """Главная функция"""
    try:
        await monitor_system()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await AsyncPGPool.close()


if __name__ == "__main__":
    asyncio.run(main())
