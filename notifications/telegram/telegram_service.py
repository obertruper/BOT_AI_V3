#!/usr/bin/env python3
"""
Telegram сервис для BOT Trading v3
Адаптированная версия из v2 для асинхронной архитектуры
"""

import asyncio
from datetime import datetime
from typing import Any

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

logger = setup_logger("telegram_service")


class TelegramNotificationService:
    """
    Telegram сервис для уведомлений и управления торговым ботом.
    Адаптирован из v2 для работы в асинхронной архитектуре v3.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Инициализация Telegram сервиса.

        Args:
            config_manager: Менеджер конфигурации системы
        """
        self.config_manager = config_manager
        self.config = config_manager.get_system_config()

        # Получаем настройки Telegram
        telegram_config = self.config.get("notifications", {}).get("telegram", {})
        self.token = telegram_config.get("bot_token")
        self.chat_id = telegram_config.get("chat_id")

        if not self.token:
            raise ValueError("Telegram bot token not found in configuration")

        # Ссылки на основные компоненты системы
        self.orchestrator = None
        self.trader_manager = None
        self.strategy_manager = None

        # Инициализация бота
        self.app = None
        self.is_running = False

        logger.info("TelegramNotificationService initialized")

    def set_orchestrator(self, orchestrator):
        """Устанавливает ссылку на SystemOrchestrator"""
        self.orchestrator = orchestrator

    def set_trader_manager(self, trader_manager):
        """Устанавливает ссылку на TraderManager"""
        self.trader_manager = trader_manager

    def set_strategy_manager(self, strategy_manager):
        """Устанавливает ссылку на StrategyManager"""
        self.strategy_manager = strategy_manager

    async def initialize(self):
        """Инициализация Telegram бота"""
        try:
            self.app = ApplicationBuilder().token(self.token).build()

            # Регистрируем обработчики команд
            self._setup_handlers()

            # Запускаем polling в отдельной задаче
            asyncio.create_task(self._run_polling())

            self.is_running = True
            logger.info("Telegram bot initialized and started")

            # Отправляем приветственное сообщение
            await self.send_notification("🚀 BOT Trading v3 started successfully!")

        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {e}")
            raise

    def _setup_handlers(self):
        """Регистрирует обработчики команд"""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("traders", self.cmd_traders))
        self.app.add_handler(CommandHandler("positions", self.cmd_positions))
        self.app.add_handler(CommandHandler("menu", self.cmd_menu))
        self.app.add_handler(CallbackQueryHandler(self.callback_handler))

    async def _run_polling(self):
        """Запускает polling для получения обновлений"""
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
        except Exception as e:
            logger.error(f"Error in Telegram polling: {e}")

    async def stop(self):
        """Останавливает Telegram бота"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        self.is_running = False
        logger.info("Telegram bot stopped")

    async def send_notification(self, message: str, parse_mode: str = "HTML"):
        """
        Отправляет уведомление в Telegram.

        Args:
            message: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
        """
        try:
            if self.app and self.chat_id:
                await self.app.bot.send_message(
                    chat_id=self.chat_id, text=message, parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")

    async def send_trade_notification(self, trade_data: dict[str, Any]):
        """Отправляет уведомление о сделке"""
        message = f"""
🔔 <b>New Trade Opened</b>

📊 Symbol: {trade_data.get("symbol", "N/A")}
🏦 Exchange: {trade_data.get("exchange", "N/A")}
📈 Side: {trade_data.get("side", "N/A")}
💰 Amount: {trade_data.get("quantity", 0):.4f}
💵 Price: {trade_data.get("price", 0):.2f}
🎯 Strategy: {trade_data.get("strategy_name", "N/A")}

🆔 Trade ID: {trade_data.get("id", "N/A")}
        """
        await self.send_notification(message)

    async def send_error_notification(self, error: str, details: str = ""):
        """Отправляет уведомление об ошибке"""
        message = f"""
❌ <b>Error Occurred</b>

Error: {error}
{f"Details: {details}" if details else ""}

Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        await self.send_notification(message)

    # Обработчики команд
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await update.message.reply_text(
            "🤖 Welcome to BOT Trading v3!\n\n"
            "Use /help to see available commands.\n"
            "Use /menu for interactive menu."
        )

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop"""
        if self.orchestrator:
            await update.message.reply_text("⏹️ Stopping trading system...")
            await self.orchestrator.shutdown()
            await update.message.reply_text("✅ System stopped successfully")
        else:
            await update.message.reply_text("❌ System orchestrator not available")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
<b>Available Commands:</b>

/start - Start the bot
/stop - Stop trading system
/status - System status
/stats - Trading statistics
/traders - List active traders
/positions - Current positions
/menu - Interactive menu
/help - Show this help

<b>BOT Trading v3.0</b>
        """
        await update.message.reply_text(help_text, parse_mode="HTML")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        if not self.orchestrator:
            await update.message.reply_text("❌ System orchestrator not available")
            return

        try:
            status = await self.orchestrator.get_system_status()

            message = f"""
<b>System Status</b>

🟢 Status: {(status["system"]["is_running"] and "Running") or "Stopped"}
📊 Version: {status["system"]["version"]}
⏱️ Uptime: {status["system"]["uptime_seconds"] or 0:.0f}s

<b>Health:</b>
{"✅" if status["health"]["is_healthy"] else "❌"} Healthy: {status["health"]["is_healthy"]}
📈 Active Traders: {status["traders"]["active"]}
💰 Total Trades: {status["traders"]["total_trades"]}

<b>Resources:</b>
💾 Memory: {status["resources"].get("memory_percent", 0):.1f}%
🖥️ CPU: {status["resources"].get("cpu_percent", 0):.1f}%
            """

            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await update.message.reply_text("❌ Error getting system status")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        if not self.trader_manager:
            await update.message.reply_text("❌ Trader manager not available")
            return

        try:
            stats = await self.trader_manager.get_statistics()

            message = f"""
<b>Trading Statistics</b>

📊 Active Traders: {stats.active_traders}
💰 Total Trades: {stats.total_trades}
✅ Winning Trades: {stats.winning_trades}
❌ Losing Trades: {stats.losing_trades}
📈 Win Rate: {stats.win_rate:.1f}%

💵 Total PnL: ${stats.total_pnl:.2f}
📊 Total Volume: ${stats.total_volume:.2f}
            """

            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            await update.message.reply_text("❌ Error getting statistics")

    async def cmd_traders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /traders"""
        if not self.trader_manager:
            await update.message.reply_text("❌ Trader manager not available")
            return

        try:
            traders = await self.trader_manager.get_all_traders()

            if not traders:
                await update.message.reply_text("📊 No active traders")
                return

            message = "<b>Active Traders:</b>\n\n"

            for trader_id, trader in traders.items():
                status = "🟢" if trader.is_running else "🔴"
                message += f"{status} {trader_id}\n"
                message += f"  Strategy: {trader.strategy_name}\n"
                message += f"  Symbol: {trader.symbol}\n"
                message += f"  Exchange: {trader.exchange_name}\n\n"

            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error getting traders: {e}")
            await update.message.reply_text("❌ Error getting traders list")

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /positions"""
        await update.message.reply_text("📊 Position tracking coming soon...")

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /menu - показывает интерактивное меню"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("📈 Stats", callback_data="stats"),
            ],
            [
                InlineKeyboardButton("👥 Traders", callback_data="traders"),
                InlineKeyboardButton("💰 Positions", callback_data="positions"),
            ],
            [
                InlineKeyboardButton("▶️ Start All", callback_data="start_all"),
                InlineKeyboardButton("⏹️ Stop All", callback_data="stop_all"),
            ],
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_menu")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🤖 <b>BOT Trading v3 Control Panel</b>\n\nSelect an action:",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов от inline кнопок"""
        query = update.callback_query
        await query.answer()

        handlers = {
            "status": self.cmd_status,
            "stats": self.cmd_stats,
            "traders": self.cmd_traders,
            "positions": self.cmd_positions,
            "start_all": self._handle_start_all,
            "stop_all": self._handle_stop_all,
            "refresh_menu": self._handle_refresh_menu,
        }

        handler = handlers.get(query.data)
        if handler:
            # Создаем фейковый update с message для совместимости
            fake_update = type("obj", (object,), {"message": query.message})
            await handler(fake_update, context)
        else:
            await query.message.reply_text(f"Unknown action: {query.data}")

    async def _handle_start_all(self, update, context):
        """Запускает всех трейдеров"""
        if self.trader_manager:
            await update.message.reply_text("▶️ Starting all traders...")
            await self.trader_manager.start_all_traders()
            await update.message.reply_text("✅ All traders started")
        else:
            await update.message.reply_text("❌ Trader manager not available")

    async def _handle_stop_all(self, update, context):
        """Останавливает всех трейдеров"""
        if self.trader_manager:
            await update.message.reply_text("⏹️ Stopping all traders...")
            await self.trader_manager.stop_all_traders()
            await update.message.reply_text("✅ All traders stopped")
        else:
            await update.message.reply_text("❌ Trader manager not available")

    async def _handle_refresh_menu(self, update, context):
        """Обновляет меню"""
        await self.cmd_menu(update, context)
