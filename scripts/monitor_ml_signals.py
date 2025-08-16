#!/usr/bin/env python3
"""Мониторинг ML сигналов через веб-интерфейс"""

import os
import time
from datetime import datetime

import requests
from colorama import Fore, Style, init

init(autoreset=True)

API_URL = "http://localhost:8080"


def clear_screen():
    """Очистка экрана"""
    os.system("clear" if os.name == "posix" else "cls")


def get_health_status():
    """Получение статуса системы"""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        return response.json()
    except:
        return None


def get_ml_signals():
    """Получение последних ML сигналов"""
    try:
        response = requests.get(f"{API_URL}/api/ml/signals/latest", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def get_traders_status():
    """Получение статуса трейдеров"""
    try:
        response = requests.get(f"{API_URL}/api/traders/list", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def format_signal(signal):
    """Форматирование сигнала для отображения"""
    signal_type = signal.get("signal_type", "UNKNOWN")

    if signal_type == "LONG":
        color = Fore.GREEN
        emoji = "🟢"
    elif signal_type == "SHORT":
        color = Fore.RED
        emoji = "🔴"
    else:
        color = Fore.YELLOW
        emoji = "⚪"

    confidence = signal.get("confidence", 0) * 100
    strength = signal.get("strength", 0)

    return f"{emoji} {color}{signal_type}{Style.RESET_ALL} | Conf: {confidence:.1f}% | Str: {strength:.2f}"


def monitor_loop():
    """Основной цикл мониторинга"""
    print(f"{Fore.CYAN}🤖 ML Trading Monitor")
    print(f"{Fore.CYAN}{'=' * 60}\n")

    while True:
        try:
            clear_screen()

            # Заголовок
            print(f"{Fore.YELLOW}⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.CYAN}{'=' * 60}\n")

            # 1. Статус системы
            print(f"{Fore.GREEN}📊 SYSTEM STATUS:")
            health = get_health_status()
            if health:
                status = health.get("status", "unknown")
                if status == "healthy":
                    status_color = Fore.GREEN
                elif status == "degraded":
                    status_color = Fore.YELLOW
                else:
                    status_color = Fore.RED

                print(f"  Status: {status_color}{status.upper()}{Style.RESET_ALL}")

                # Компоненты
                components = health.get("basic_components", {})
                if components:
                    print("  Components:")
                    for comp, active in components.items():
                        emoji = "✅" if active else "❌"
                        print(f"    {emoji} {comp}: {'active' if active else 'inactive'}")
            else:
                print(f"  {Fore.RED}❌ Cannot connect to API{Style.RESET_ALL}")

            # 2. ML сигналы
            print(f"\n{Fore.GREEN}🔔 ML SIGNALS:")
            signals = get_ml_signals()
            if signals:
                if isinstance(signals, list) and signals:
                    for signal in signals[:10]:  # Последние 10 сигналов
                        symbol = signal.get("symbol", "UNKNOWN")
                        timestamp = signal.get("timestamp", "")
                        formatted = format_signal(signal)
                        print(f"  {symbol}: {formatted} | {timestamp}")
                else:
                    print(f"  {Fore.YELLOW}⚠️  No recent signals{Style.RESET_ALL}")
            else:
                print(f"  {Fore.YELLOW}⚠️  ML signals endpoint not available{Style.RESET_ALL}")

            # 3. Трейдеры
            print(f"\n{Fore.GREEN}👥 TRADERS:")
            traders = get_traders_status()
            if traders and not traders.get("error"):
                traders_list = traders.get("traders", [])
                if traders_list:
                    for trader in traders_list:
                        trader_id = trader.get("id", "unknown")
                        status = trader.get("status", "unknown")
                        strategy = trader.get("strategy", "none")

                        status_emoji = {
                            "running": "🟢",
                            "stopped": "🔴",
                            "error": "❌",
                        }.get(status, "⚪")

                        print(f"  {status_emoji} {trader_id}: {strategy} ({status})")
                else:
                    print(f"  {Fore.YELLOW}⚠️  No traders configured{Style.RESET_ALL}")
            else:
                print(f"  {Fore.YELLOW}⚠️  Traders not available{Style.RESET_ALL}")

            # 4. Инструкции
            print(f"\n{Fore.CYAN}{'=' * 60}")
            print(f"{Fore.YELLOW}Press Ctrl+C to exit. Refreshing every 10 seconds...")

            time.sleep(10)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Monitor stopped")
            break
        except Exception as e:
            print(f"\n{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
            time.sleep(5)


if __name__ == "__main__":
    try:
        # Проверяем доступность API
        print(f"{Fore.CYAN}🔍 Checking API availability...")
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"{Fore.GREEN}✅ API is available{Style.RESET_ALL}")
            print(f"{Fore.GREEN}🌐 Web interface: {API_URL}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}📚 API docs: {API_URL}/api/docs{Style.RESET_ALL}\n")
            time.sleep(2)
            monitor_loop()
        else:
            print(f"{Fore.RED}❌ API returned status code: {response.status_code}{Style.RESET_ALL}")
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}❌ Cannot connect to API at {API_URL}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Make sure the trading system is running{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
