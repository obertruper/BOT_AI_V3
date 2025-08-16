#!/usr/bin/env python3
"""
Скрипт мониторинга состояния торговой системы BOT Trading v3
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp
from colorama import Fore, Style, init
from tabulate import tabulate

# Инициализация colorama для цветного вывода
init(autoreset=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8080/api"


class SystemMonitor:
    """Монитор состояния системы"""

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_health(self) -> dict[str, Any]:
        """Получить статус здоровья системы"""
        try:
            async with self.session.get(f"{API_BASE_URL}/health") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"status": "unhealthy", "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    async def get_traders(self) -> dict[str, Any]:
        """Получить список трейдеров"""
        try:
            async with self.session.get(f"{API_BASE_URL}/traders") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_signals(self, limit: int = 10) -> dict[str, Any]:
        """Получить последние сигналы"""
        try:
            async with self.session.get(f"{API_BASE_URL}/signals?limit={limit}") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_metrics(self) -> dict[str, Any]:
        """Получить метрики системы"""
        try:
            async with self.session.get(f"{API_BASE_URL}/metrics") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}

    def print_header(self):
        """Печать заголовка"""
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}BOT TRADING V3 - SYSTEM MONITOR{Style.RESET_ALL}".center(80))
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
        print("=" * 80 + "\n")

    def print_health_status(self, health: dict[str, Any]):
        """Печать статуса здоровья"""
        print(f"{Fore.YELLOW}📊 SYSTEM HEALTH{Style.RESET_ALL}")
        print("-" * 40)

        status = health.get("status", "unknown")
        if status == "healthy":
            status_color = Fore.GREEN
            status_icon = "✅"
        elif status == "degraded":
            status_color = Fore.YELLOW
            status_icon = "⚠️"
        else:
            status_color = Fore.RED
            status_icon = "❌"

        print(f"Status: {status_color}{status_icon} {status.upper()}{Style.RESET_ALL}")

        if "error" in health:
            print(f"Error: {Fore.RED}{health['error']}{Style.RESET_ALL}")

        if "components" in health:
            print("\nComponents:")
            for comp, status in health["components"].items():
                if status.get("healthy", False):
                    comp_color = Fore.GREEN
                    comp_icon = "✓"
                else:
                    comp_color = Fore.RED
                    comp_icon = "✗"
                print(
                    f"  {comp_color}{comp_icon} {comp}: {status.get('status', 'unknown')}{Style.RESET_ALL}"
                )
                if "error" in status:
                    print(f"    Error: {status['error']}")

    def print_traders(self, traders_data: dict[str, Any]):
        """Печать информации о трейдерах"""
        print(f"\n{Fore.YELLOW}🤖 ACTIVE TRADERS{Style.RESET_ALL}")
        print("-" * 40)

        if "error" in traders_data:
            print(f"{Fore.RED}Error: {traders_data['error']}{Style.RESET_ALL}")
            return

        traders = traders_data.get("traders", [])
        if not traders:
            print("No active traders")
            return

        table_data = []
        for trader in traders:
            status_color = Fore.GREEN if trader.get("state") == "RUNNING" else Fore.YELLOW
            table_data.append(
                [
                    trader.get("trader_id", "Unknown"),
                    f"{status_color}{trader.get('state', 'Unknown')}{Style.RESET_ALL}",
                    trader.get("strategy", "Unknown"),
                    trader.get("exchange", "Unknown"),
                    trader.get("symbol", "Unknown"),
                ]
            )

        headers = ["Trader ID", "State", "Strategy", "Exchange", "Symbol"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def print_signals(self, signals_data: dict[str, Any]):
        """Печать последних сигналов"""
        print(f"\n{Fore.YELLOW}📈 RECENT SIGNALS{Style.RESET_ALL}")
        print("-" * 40)

        if "error" in signals_data:
            print(f"{Fore.RED}Error: {signals_data['error']}{Style.RESET_ALL}")
            return

        signals = signals_data.get("signals", [])
        if not signals:
            print("No recent signals")
            return

        table_data = []
        for signal in signals[:5]:  # Показываем только 5 последних
            signal_type = signal.get("type", "Unknown")
            if signal_type == "BUY":
                type_color = Fore.GREEN
                type_icon = "🟢"
            elif signal_type == "SELL":
                type_color = Fore.RED
                type_icon = "🔴"
            else:
                type_color = Fore.YELLOW
                type_icon = "🟡"

            table_data.append(
                [
                    signal.get("timestamp", "Unknown")[:19],
                    f"{type_color}{type_icon} {signal_type}{Style.RESET_ALL}",
                    signal.get("symbol", "Unknown"),
                    f"{signal.get('confidence', 0):.2%}",
                    f"{signal.get('strength', 0):.2f}",
                ]
            )

        headers = ["Time", "Type", "Symbol", "Confidence", "Strength"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def print_metrics(self, metrics: dict[str, Any]):
        """Печать метрик системы"""
        print(f"\n{Fore.YELLOW}📊 SYSTEM METRICS{Style.RESET_ALL}")
        print("-" * 40)

        if "error" in metrics:
            print(f"{Fore.RED}Error: {metrics['error']}{Style.RESET_ALL}")
            return

        # Торговые метрики
        trading = metrics.get("trading", {})
        if trading:
            print("\nTrading Metrics:")
            print(f"  Total Trades: {trading.get('total_trades', 0)}")
            print(f"  Open Positions: {trading.get('open_positions', 0)}")
            print(f"  Today's PnL: ${trading.get('daily_pnl', 0):.2f}")
            print(f"  Win Rate: {trading.get('win_rate', 0):.2%}")

        # Системные метрики
        system = metrics.get("system", {})
        if system:
            print("\nSystem Metrics:")
            print(f"  CPU Usage: {system.get('cpu_percent', 0):.1f}%")
            print(f"  Memory Usage: {system.get('memory_percent', 0):.1f}%")
            print(f"  Uptime: {system.get('uptime', 'Unknown')}")

    async def monitor_loop(self, interval: int = 5):
        """Основной цикл мониторинга"""
        while True:
            try:
                # Очищаем экран
                print("\033[2J\033[H", end="")

                # Печатаем заголовок
                self.print_header()

                # Получаем данные
                health = await self.get_health()
                traders = await self.get_traders()
                signals = await self.get_signals()
                metrics = await self.get_metrics()

                # Выводим информацию
                self.print_health_status(health)
                self.print_traders(traders)
                self.print_signals(signals)
                self.print_metrics(metrics)

                print(
                    f"\n{Fore.CYAN}Refreshing in {interval} seconds... (Press Ctrl+C to exit){Style.RESET_ALL}"
                )

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            await asyncio.sleep(interval)


async def main():
    """Основная функция"""
    try:
        # Проверяем доступность API
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{API_BASE_URL}/health", timeout=2) as resp:
                    if resp.status != 200:
                        print(
                            f"{Fore.YELLOW}⚠️  API might not be fully available (status: {resp.status}){Style.RESET_ALL}"
                        )
            except Exception:
                print(f"{Fore.YELLOW}⚠️  Cannot connect to API at {API_BASE_URL}{Style.RESET_ALL}")
                print("    Make sure the web server is running: python3 web/launcher.py")

        # Запускаем мониторинг
        async with SystemMonitor() as monitor:
            await monitor.monitor_loop()

    except KeyboardInterrupt:
        print(f"\n{Fore.CYAN}Monitoring stopped by user{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
