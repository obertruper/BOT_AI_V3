#!/usr/bin/env python3
"""
Мониторинг статуса бота в реальном времени
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

sys.path.append(str(Path(__file__).parent))

from colorama import Fore, Style, init

from database.connections.postgres import AsyncPGPool

init()


def print_status(label, value, is_ok=True):
    """Печатает статус с цветом."""
    color = Fore.GREEN if is_ok else Fore.RED
    print(f"{label}: {color}{value}{Style.RESET_ALL}")


async def check_api_status():
    """Проверяет статус API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8080/api/health") as resp:
                data = await resp.json()
                return data
    except:
        return None


async def monitor_bot():
    """Мониторит статус бота."""

    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'BOT TRADING V3 - СТАТУС СИСТЕМЫ':^60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

    while True:
        try:
            # 1. Проверка процессов
            import subprocess

            ps_result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            processes = ps_result.stdout

            print(f"\n{Fore.YELLOW}1. ПРОЦЕССЫ:{Style.RESET_ALL}")
            print_status(
                "unified_launcher",
                "✓ Запущен" if "unified_launcher" in processes else "✗ Не найден",
                "unified_launcher" in processes,
            )
            print_status(
                "main.py",
                "✓ Запущен" if "main.py" in processes else "✗ Не найден",
                "main.py" in processes,
            )
            print_status(
                "web/launcher",
                "✓ Запущен" if "web/launcher" in processes else "✗ Не найден",
                "web/launcher" in processes,
            )

            # 2. API статус
            print(f"\n{Fore.YELLOW}2. API СТАТУС:{Style.RESET_ALL}")
            api_status = await check_api_status()
            if api_status:
                print_status(
                    "API", api_status["status"], api_status["status"] == "healthy"
                )
                if "components" in api_status:
                    for comp, status in api_status["components"].items():
                        print(f"  - {comp}: {'✓' if status else '✗'}")
            else:
                print_status("API", "✗ Недоступен", False)

            # 3. База данных
            print(f"\n{Fore.YELLOW}3. БАЗА ДАННЫХ:{Style.RESET_ALL}")
            try:
                db_test = await AsyncPGPool.fetchval("SELECT 1")
                print_status("PostgreSQL", "✓ Подключено", True)

                # Статистика сигналов
                signal_stats = await AsyncPGPool.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN signal_type = 'LONG' THEN 1 END) as long_count,
                        COUNT(CASE WHEN signal_type = 'SHORT' THEN 1 END) as short_count,
                        COUNT(CASE WHEN signal_type = 'NEUTRAL' THEN 1 END) as neutral_count,
                        MAX(created_at) as last_signal
                    FROM signals
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """
                )

                if signal_stats["total"] > 0:
                    print("\nСигналы за последний час:")
                    print(f"  Всего: {signal_stats['total']}")
                    print(
                        f"  LONG: {signal_stats['long_count']} ({signal_stats['long_count'] / signal_stats['total'] * 100:.1f}%)"
                    )
                    print(
                        f"  SHORT: {signal_stats['short_count']} ({signal_stats['short_count'] / signal_stats['total'] * 100:.1f}%)"
                    )
                    print(
                        f"  NEUTRAL: {signal_stats['neutral_count']} ({signal_stats['neutral_count'] / signal_stats['total'] * 100:.1f}%)"
                    )
                else:
                    print("  Нет сигналов за последний час")

            except Exception as e:
                print_status("PostgreSQL", f"✗ Ошибка: {e}", False)

            # 4. ML активность
            print(f"\n{Fore.YELLOW}4. ML СИСТЕМА:{Style.RESET_ALL}")
            ml_stats = await AsyncPGPool.fetchrow(
                """
                SELECT
                    COUNT(*) as predictions,
                    MAX(created_at) as last_prediction
                FROM processed_market_data
                WHERE created_at > NOW() - INTERVAL '5 minutes'
            """
            )

            if ml_stats["predictions"] > 0:
                print_status(
                    "ML предсказания", f"✓ {ml_stats['predictions']} за 5 минут", True
                )
                if ml_stats["last_prediction"]:
                    time_diff = datetime.now(timezone.utc) - ml_stats["last_prediction"]
                    print(f"  Последнее: {time_diff.total_seconds():.0f} сек назад")
            else:
                # Проверим логи на ML активность
                import os

                log_file = "data/logs/bot_trading_20250806.log"
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        lines = f.readlines()[-100:]
                        ml_lines = [l for l in lines if "ML" in l or "ml_" in l]
                        if ml_lines:
                            print_status(
                                "ML активность",
                                f"✓ Обнаружена в логах ({len(ml_lines)} записей)",
                                True,
                            )
                        else:
                            print_status("ML активность", "✗ Не обнаружена", False)
                else:
                    print_status("ML активность", "✗ Лог файл не найден", False)

            # 5. Торговая активность
            print(f"\n{Fore.YELLOW}5. ТОРГОВЛЯ:{Style.RESET_ALL}")
            trade_stats = await AsyncPGPool.fetchrow(
                """
                SELECT
                    COUNT(*) as order_count,
                    COUNT(CASE WHEN status = 'filled' THEN 1 END) as filled_count,
                    COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count
                FROM orders
                WHERE created_at > NOW() - INTERVAL '1 hour'
            """
            )

            if trade_stats["order_count"] > 0:
                print(f"  Ордеров за час: {trade_stats['order_count']}")
                print(f"  Исполнено: {trade_stats['filled_count']}")
                print(f"  Отклонено: {trade_stats['rejected_count']}")
            else:
                print("  Нет ордеров за последний час")

            # 6. Параметры торговли
            print(f"\n{Fore.YELLOW}6. ПАРАМЕТРЫ:{Style.RESET_ALL}")
            print("  MAX_POSITION_SIZE: $1000")
            print("  DEFAULT_LEVERAGE: 5x")
            print("  RISK_LIMIT: 2%")
            print("  Тестовый баланс: $150")

            print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
            print("Обновление через 10 секунд... (Ctrl+C для выхода)")

            await asyncio.sleep(10)
            print("\033[2J\033[H")  # Очистка экрана

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Мониторинг остановлен{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(monitor_bot())
