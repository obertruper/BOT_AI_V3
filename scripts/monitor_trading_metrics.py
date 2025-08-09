#!/usr/bin/env python3
"""
Real-time Trading Metrics Monitor
Отображает критические метрики торговой системы в реальном времени
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

import psutil
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from core.config import ConfigManager
from database.connections import get_async_db
from database.models.base_models import Balance, Order, Trade

console = Console()


class TradingMetricsMonitor:
    """Монитор критических метрик торговой системы"""

    def __init__(self):
        self.config = ConfigManager()
        self.running = True

    async def get_system_metrics(self):
        """Получить системные метрики"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Проверка процессов
        processes = {"core": False, "api": False, "ml": False}

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline", []))
                if "main.py" in cmdline:
                    processes["core"] = True
                elif "launcher.py" in cmdline:
                    processes["api"] = True
                elif "ml_" in cmdline:
                    processes["ml"] = True
            except:
                pass

        return {
            "cpu": cpu_percent,
            "memory": memory.percent,
            "disk": disk.percent,
            "processes": processes,
        }

    async def get_trading_metrics(self):
        """Получить торговые метрики из БД"""
        async with get_async_db() as db:
            # Активные ордера
            active_orders = await db.execute(
                select(func.count(Order.id)).where(
                    Order.status.in_(["open", "pending"])
                )
            )
            active_orders_count = active_orders.scalar()

            # Сделки за последние 24 часа
            yesterday = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            trades_today = await db.execute(
                select(func.count(Trade.id), func.sum(Trade.pnl)).where(
                    Trade.timestamp >= yesterday
                )
            )
            trades_count, total_pnl = trades_today.first()

            # Текущий баланс
            balances = await db.execute(
                select(
                    Balance.asset, Balance.free, Balance.locked, Balance.exchange
                ).where(Balance.asset == "USDT")
            )

            # Win rate
            winning_trades = await db.execute(
                select(func.count(Trade.id))
                .where(Trade.timestamp >= yesterday)
                .where(Trade.pnl > 0)
            )
            win_count = winning_trades.scalar()

            win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0

            return {
                "active_orders": active_orders_count or 0,
                "trades_today": trades_count or 0,
                "pnl_today": float(total_pnl or 0),
                "win_rate": win_rate,
                "balances": balances.all(),
            }

    def create_layout(self):
        """Создать layout для отображения"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        layout["body"].split_row(Layout(name="left"), Layout(name="right"))

        return layout

    def create_metrics_table(self, metrics):
        """Создать таблицу с метриками"""
        table = Table(title="📊 Trading Metrics", expand=True)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="white")
        table.add_column("Status", style="white", width=10)

        # Активные ордера
        orders_status = "🟢" if metrics["active_orders"] > 0 else "⚪"
        table.add_row("Active Orders", str(metrics["active_orders"]), orders_status)

        # Сделки сегодня
        trades_status = "🟢" if metrics["trades_today"] > 0 else "🔴"
        table.add_row("Trades Today", str(metrics["trades_today"]), trades_status)

        # PnL
        pnl_color = "green" if metrics["pnl_today"] > 0 else "red"
        pnl_status = "📈" if metrics["pnl_today"] > 0 else "📉"
        table.add_row(
            "PnL Today",
            Text(f"${metrics['pnl_today']:.2f}", style=pnl_color),
            pnl_status,
        )

        # Win Rate
        wr_color = "green" if metrics["win_rate"] > 50 else "red"
        wr_status = "✅" if metrics["win_rate"] > 50 else "❌"
        table.add_row(
            "Win Rate", Text(f"{metrics['win_rate']:.1f}%", style=wr_color), wr_status
        )

        return table

    def create_system_table(self, system_metrics):
        """Создать таблицу системных метрик"""
        table = Table(title="💻 System Metrics", expand=True)
        table.add_column("Resource", style="cyan", width=20)
        table.add_column("Usage", style="white")
        table.add_column("Status", style="white", width=10)

        # CPU
        cpu_color = (
            "red"
            if system_metrics["cpu"] > 80
            else "yellow"
            if system_metrics["cpu"] > 50
            else "green"
        )
        cpu_status = (
            "🔴"
            if system_metrics["cpu"] > 80
            else "🟡"
            if system_metrics["cpu"] > 50
            else "🟢"
        )
        table.add_row(
            "CPU", Text(f"{system_metrics['cpu']:.1f}%", style=cpu_color), cpu_status
        )

        # Memory
        mem_color = (
            "red"
            if system_metrics["memory"] > 80
            else "yellow"
            if system_metrics["memory"] > 50
            else "green"
        )
        mem_status = (
            "🔴"
            if system_metrics["memory"] > 80
            else "🟡"
            if system_metrics["memory"] > 50
            else "🟢"
        )
        table.add_row(
            "Memory",
            Text(f"{system_metrics['memory']:.1f}%", style=mem_color),
            mem_status,
        )

        # Disk
        disk_color = (
            "red"
            if system_metrics["disk"] > 90
            else "yellow"
            if system_metrics["disk"] > 70
            else "green"
        )
        disk_status = (
            "🔴"
            if system_metrics["disk"] > 90
            else "🟡"
            if system_metrics["disk"] > 70
            else "🟢"
        )
        table.add_row(
            "Disk",
            Text(f"{system_metrics['disk']:.1f}%", style=disk_color),
            disk_status,
        )

        # Processes
        for proc_name, is_running in system_metrics["processes"].items():
            status = "🟢" if is_running else "🔴"
            color = "green" if is_running else "red"
            table.add_row(
                f"{proc_name.upper()} Process",
                Text("Running" if is_running else "Stopped", style=color),
                status,
            )

        return table

    def create_balance_table(self, balances):
        """Создать таблицу балансов"""
        table = Table(title="💰 Balances", expand=True)
        table.add_column("Exchange", style="cyan")
        table.add_column("Free USDT", style="green")
        table.add_column("Locked USDT", style="yellow")
        table.add_column("Total USDT", style="white")

        total_free = 0
        total_locked = 0

        for balance in balances:
            free = float(balance.free)
            locked = float(balance.locked)
            total = free + locked

            total_free += free
            total_locked += locked

            table.add_row(
                balance.exchange, f"${free:.2f}", f"${locked:.2f}", f"${total:.2f}"
            )

        # Итого
        table.add_row(
            "TOTAL",
            Text(f"${total_free:.2f}", style="bold green"),
            Text(f"${total_locked:.2f}", style="bold yellow"),
            Text(f"${(total_free + total_locked):.2f}", style="bold white"),
        )

        return table

    async def run(self):
        """Запустить мониторинг"""
        layout = self.create_layout()

        with Live(layout, refresh_per_second=1, console=console) as live:
            while self.running:
                try:
                    # Получаем метрики
                    system_metrics = await self.get_system_metrics()
                    trading_metrics = await self.get_trading_metrics()

                    # Обновляем header
                    header_text = Text()
                    header_text.append("🚀 BOT_AI_V3 ", style="bold purple")
                    header_text.append("Trading Metrics Monitor | ", style="white")
                    header_text.append(
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="cyan"
                    )
                    layout["header"].update(Panel(header_text, style="bold"))

                    # Обновляем метрики
                    layout["left"].update(
                        Panel(
                            self.create_metrics_table(trading_metrics),
                            border_style="green",
                        )
                    )

                    # Обновляем системные метрики
                    layout["right"].split_column(
                        Layout(self.create_system_table(system_metrics)),
                        Layout(self.create_balance_table(trading_metrics["balances"])),
                    )

                    # Footer
                    footer_text = Text()
                    footer_text.append("Press ", style="white")
                    footer_text.append("Ctrl+C", style="bold red")
                    footer_text.append(" to exit | ", style="white")
                    footer_text.append("Updates every second", style="dim")
                    layout["footer"].update(Panel(footer_text, style="dim"))

                    await asyncio.sleep(1)

                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    await asyncio.sleep(5)


async def main():
    """Главная функция"""
    monitor = TradingMetricsMonitor()

    console.print("[bold purple]Starting Trading Metrics Monitor...[/bold purple]")
    console.print("[dim]Connecting to database...[/dim]")

    try:
        await monitor.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
    finally:
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    asyncio.run(main())
