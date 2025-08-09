#!/usr/bin/env python3
"""
Утилита мониторинга торговли в реальном времени
Отображает ML сигналы, ордера, позиции и метрики
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="logs/monitor.log",
)
logger = logging.getLogger(__name__)

console = Console()


class TradingMonitor:
    def __init__(self):
        self.orchestrator = None
        self.exchange_client = None
        self.start_time = datetime.now()
        self.metrics = {
            "total_signals": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "neutral_signals": 0,
            "total_orders": 0,
            "filled_orders": 0,
            "pending_orders": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": Decimal("0"),
            "max_drawdown": Decimal("0"),
            "win_rate": 0.0,
        }

    async def initialize(self):
        """Инициализация мониторинга"""
        try:
            from core.system.orchestrator import SystemOrchestrator
            from exchanges.factory import ExchangeFactory

            # Создаем оркестратор для доступа к компонентам
            self.orchestrator = SystemOrchestrator()

            # Создаем клиент биржи
            factory = ExchangeFactory()
            self.exchange_client = factory.create_client(
                "bybit", os.getenv("BYBIT_API_KEY"), os.getenv("BYBIT_API_SECRET")
            )

            await self.exchange_client.connect()

            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            return False

    async def get_account_info(self) -> Dict:
        """Получение информации об аккаунте"""
        try:
            balances = await self.exchange_client.get_balances()

            # Фильтруем только ненулевые балансы
            non_zero = {k: v for k, v in balances.items() if float(v) > 0}

            return {
                "balances": non_zero,
                "total_usdt": sum(float(v) for k, v in non_zero.items() if k == "USDT"),
            }

        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return {"balances": {}, "total_usdt": 0}

    async def get_active_positions(self) -> List[Dict]:
        """Получение активных позиций"""
        try:
            positions = await self.exchange_client.get_positions()

            # Фильтруем только активные
            active = []
            for pos in positions:
                if float(pos.get("size", 0)) != 0:
                    active.append(
                        {
                            "symbol": pos.get("symbol"),
                            "side": "LONG"
                            if float(pos.get("size", 0)) > 0
                            else "SHORT",
                            "size": abs(float(pos.get("size", 0))),
                            "entry_price": float(pos.get("entry_price", 0)),
                            "mark_price": float(pos.get("mark_price", 0)),
                            "unrealized_pnl": float(pos.get("unrealized_pnl", 0)),
                            "pnl_percent": float(pos.get("pnl_percent", 0)),
                        }
                    )

            return active

        except Exception as e:
            logger.error(f"Ошибка получения позиций: {e}")
            return []

    async def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """Получение последних ML сигналов"""
        try:
            from sqlalchemy import desc, select

            from database.connections import get_async_db
            from database.models.signal import Signal

            async with get_async_db() as db:
                result = await db.execute(
                    select(Signal).order_by(desc(Signal.created_at)).limit(limit)
                )
                signals = result.scalars().all()

                return [
                    {
                        "time": sig.created_at,
                        "symbol": sig.symbol,
                        "type": sig.signal_type.value,
                        "strength": sig.strength,
                        "confidence": sig.confidence,
                        "strategy": sig.strategy_name,
                    }
                    for sig in signals
                ]

        except Exception as e:
            logger.error(f"Ошибка получения сигналов: {e}")
            return []

    async def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Получение последних ордеров"""
        try:
            from sqlalchemy import desc, select

            from database.connections import get_async_db
            from database.models.base_models import Order

            async with get_async_db() as db:
                result = await db.execute(
                    select(Order).order_by(desc(Order.created_at)).limit(limit)
                )
                orders = result.scalars().all()

                return [
                    {
                        "time": order.created_at,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "type": order.order_type.value,
                        "quantity": order.quantity,
                        "price": order.price,
                        "status": order.status.value,
                    }
                    for order in orders
                ]

        except Exception as e:
            logger.error(f"Ошибка получения ордеров: {e}")
            return []

    async def update_metrics(self):
        """Обновление метрик торговли"""
        try:
            from sqlalchemy import func, select

            from database.connections import get_async_db
            from database.models.base_models import Order, Trade
            from database.models.signal import Signal

            async with get_async_db() as db:
                # Подсчет сигналов
                total_signals = await db.scalar(select(func.count(Signal.id)))
                self.metrics["total_signals"] = total_signals or 0

                # Подсчет ордеров
                total_orders = await db.scalar(select(func.count(Order.id)))
                self.metrics["total_orders"] = total_orders or 0

                # Подсчет сделок и PnL
                trades_result = await db.execute(select(Trade))
                trades = trades_result.scalars().all()

                self.metrics["total_trades"] = len(trades)

                total_pnl = Decimal("0")
                winning = 0
                losing = 0

                for trade in trades:
                    if trade.pnl:
                        pnl = Decimal(str(trade.pnl))
                        total_pnl += pnl
                        if pnl > 0:
                            winning += 1
                        elif pnl < 0:
                            losing += 1

                self.metrics["total_pnl"] = total_pnl
                self.metrics["winning_trades"] = winning
                self.metrics["losing_trades"] = losing

                if winning + losing > 0:
                    self.metrics["win_rate"] = (winning / (winning + losing)) * 100

        except Exception as e:
            logger.error(f"Ошибка обновления метрик: {e}")

    def create_dashboard(self) -> Layout:
        """Создание дашборда"""
        layout = Layout()

        # Разделяем на секции
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        # Разделяем body на колонки
        layout["body"].split_row(Layout(name="left"), Layout(name="right"))

        # Разделяем левую колонку
        layout["left"].split_column(
            Layout(name="account", size=10),
            Layout(name="positions", size=15),
            Layout(name="metrics", size=15),
        )

        # Разделяем правую колонку
        layout["right"].split_column(
            Layout(name="signals", size=20), Layout(name="orders", size=20)
        )

        return layout

    async def render_header(self) -> Panel:
        """Рендеринг заголовка"""
        uptime = datetime.now() - self.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        header_text = Text()
        header_text.append("🤖 BOT_AI_V3 - ", style="bold cyan")
        header_text.append("Live Trading Monitor", style="bold white")
        header_text.append(f"\n⏱️ Uptime: {hours}h {minutes}m", style="dim")
        header_text.append(
            f" | 📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim"
        )

        return Panel(header_text, style="bold blue")

    async def render_account(self) -> Panel:
        """Рендеринг информации об аккаунте"""
        account_info = await self.get_account_info()

        table = Table(show_header=False, box=None)
        table.add_column("Asset", style="cyan")
        table.add_column("Balance", justify="right", style="white")

        for asset, balance in account_info["balances"].items():
            if float(balance) > 0.01:  # Показываем только значимые балансы
                table.add_row(asset, f"{float(balance):.4f}")

        total_usdt = account_info["total_usdt"]
        table.add_row("", "")
        table.add_row("Total USDT", f"${total_usdt:.2f}", style="bold green")

        return Panel(table, title="💰 Account Balance", style="green")

    async def render_positions(self) -> Panel:
        """Рендеринг активных позиций"""
        positions = await self.get_active_positions()

        if not positions:
            return Panel("No active positions", title="📊 Positions", style="yellow")

        table = Table()
        table.add_column("Symbol", style="cyan")
        table.add_column("Side", style="white")
        table.add_column("Size", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("PnL", justify="right")
        table.add_column("%", justify="right")

        for pos in positions:
            pnl_style = "green" if pos["unrealized_pnl"] >= 0 else "red"
            table.add_row(
                pos["symbol"],
                pos["side"],
                f"{pos['size']:.4f}",
                f"${pos['entry_price']:.2f}",
                f"${pos['unrealized_pnl']:.2f}",
                f"{pos['pnl_percent']:.2f}%",
                style=pnl_style,
            )

        return Panel(table, title="📊 Active Positions", style="yellow")

    async def render_metrics(self) -> Panel:
        """Рендеринг метрик торговли"""
        await self.update_metrics()

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="white")

        table.add_row("Total Signals", str(self.metrics["total_signals"]))
        table.add_row("Total Orders", str(self.metrics["total_orders"]))
        table.add_row("Total Trades", str(self.metrics["total_trades"]))
        table.add_row("", "")
        table.add_row("Win Rate", f"{self.metrics['win_rate']:.1f}%")
        table.add_row("Winning", str(self.metrics["winning_trades"]), style="green")
        table.add_row("Losing", str(self.metrics["losing_trades"]), style="red")
        table.add_row("", "")

        pnl_style = "green" if self.metrics["total_pnl"] >= 0 else "red"
        table.add_row("Total PnL", f"${self.metrics['total_pnl']:.2f}", style=pnl_style)

        return Panel(table, title="📈 Trading Metrics", style="magenta")

    async def render_signals(self) -> Panel:
        """Рендеринг последних сигналов"""
        signals = await self.get_recent_signals(8)

        if not signals:
            return Panel("No recent signals", title="🎯 ML Signals", style="blue")

        table = Table()
        table.add_column("Time", style="dim")
        table.add_column("Symbol", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Str", justify="right")
        table.add_column("Conf", justify="right")

        for sig in signals:
            signal_style = (
                "green"
                if sig["type"] == "LONG"
                else "red"
                if sig["type"] == "SHORT"
                else "yellow"
            )
            table.add_row(
                sig["time"].strftime("%H:%M:%S"),
                sig["symbol"],
                sig["type"],
                f"{sig['strength']:.2f}" if sig["strength"] else "N/A",
                f"{sig['confidence']:.0f}%" if sig["confidence"] else "N/A",
                style=signal_style,
            )

        return Panel(table, title="🎯 Recent ML Signals", style="blue")

    async def render_orders(self) -> Panel:
        """Рендеринг последних ордеров"""
        orders = await self.get_recent_orders(8)

        if not orders:
            return Panel("No recent orders", title="📋 Orders", style="cyan")

        table = Table()
        table.add_column("Time", style="dim")
        table.add_column("Symbol", style="cyan")
        table.add_column("Side", style="white")
        table.add_column("Qty", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("Status")

        for order in orders:
            side_style = "green" if order["side"] == "BUY" else "red"
            status_style = (
                "green"
                if order["status"] == "FILLED"
                else "yellow"
                if order["status"] == "PENDING"
                else "dim"
            )

            table.add_row(
                order["time"].strftime("%H:%M:%S"),
                order["symbol"],
                order["side"],
                f"{order['quantity']:.4f}",
                f"${order['price']:.2f}" if order["price"] else "MARKET",
                order["status"],
                style=f"{side_style} {status_style}",
            )

        return Panel(table, title="📋 Recent Orders", style="cyan")

    async def render_footer(self) -> Panel:
        """Рендеринг футера"""
        footer_text = Text()
        footer_text.append("Commands: ", style="bold")
        footer_text.append("q", style="bold red")
        footer_text.append(" - quit | ", style="dim")
        footer_text.append("r", style="bold green")
        footer_text.append(" - refresh | ", style="dim")
        footer_text.append("p", style="bold yellow")
        footer_text.append(" - pause/resume", style="dim")

        return Panel(footer_text, style="dim")

    async def update_display(self, layout: Layout):
        """Обновление всего дисплея"""
        layout["header"].update(await self.render_header())
        layout["account"].update(await self.render_account())
        layout["positions"].update(await self.render_positions())
        layout["metrics"].update(await self.render_metrics())
        layout["signals"].update(await self.render_signals())
        layout["orders"].update(await self.render_orders())
        layout["footer"].update(await self.render_footer())

    async def run(self):
        """Запуск мониторинга"""
        console.clear()
        console.print("🚀 Initializing Trading Monitor...", style="bold cyan")

        if not await self.initialize():
            console.print("❌ Failed to initialize monitor", style="bold red")
            return

        console.print("✅ Monitor initialized successfully", style="bold green")
        await asyncio.sleep(2)

        layout = self.create_dashboard()

        with Live(layout, refresh_per_second=0.5, screen=True) as live:
            try:
                while True:
                    await self.update_display(layout)
                    await asyncio.sleep(5)  # Обновляем каждые 5 секунд

            except KeyboardInterrupt:
                console.print("\n👋 Monitor stopped by user", style="bold yellow")


async def main():
    """Основная функция"""
    monitor = TradingMonitor()
    await monitor.run()


if __name__ == "__main__":
    try:
        # Проверяем наличие rich
        import rich
    except ImportError:
        print("❌ Пожалуйста, установите rich: pip install rich")
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
