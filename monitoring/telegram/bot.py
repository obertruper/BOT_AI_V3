"""
Telegram бот для BOT Trading v3.
Адаптирован из v2 для работы с асинхронной архитектурой.
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from core.config.config_manager import ConfigManager
from core.logger import get_logger
from core.system.orchestrator import SystemOrchestrator
from database.connections import get_async_db
from database.models.base_models import Balance, Trade
from database.models.signal import Signal

logger = get_logger(__name__)


class TelegramBotV3:
    """Telegram бот для управления BOT Trading v3."""

    def __init__(self, orchestrator: SystemOrchestrator, config: ConfigManager):
        """
        Инициализация Telegram бота.

        Args:
            orchestrator: Системный оркестратор
            config: Менеджер конфигурации
        """
        self.orchestrator = orchestrator
        self.config = config

        # Получаем токен из конфигурации
        self.token = config.get_value("telegram.bot_token")
        if not self.token:
            raise ValueError("Telegram bot token not found in config")

        # Получаем chat_id для уведомлений
        self.chat_id = config.get_value("telegram.chat_id")

        # Создаем приложение
        self.app = ApplicationBuilder().token(self.token).build()

        # Регистрируем обработчики
        self._setup_handlers()

        # Статистика ошибок для мониторинга (из v2)
        self.error_stats = {"errors": 0, "error_times": []}

        logger.info("Telegram bot v3 initialized")

    def _setup_handlers(self):
        """Регистрирует обработчики команд."""
        handlers = [
            ("start", self.cmd_start),
            ("stop", self.cmd_stop),
            ("status", self.cmd_status),
            ("stats", self.cmd_stats),
            ("sessionpnl", self.cmd_sessionpnl),
            ("traders", self.cmd_traders),
            ("strategies", self.cmd_strategies),
            ("menu", self.cmd_menu),
            ("help", self.cmd_help),
            ("update_config", self.cmd_update_config),
        ]

        for command, handler in handlers:
            self.app.add_handler(CommandHandler(command, handler))

        self.app.add_handler(CallbackQueryHandler(self.callback_handler))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        try:
            # Запускаем систему через оркестратор
            is_running = self.orchestrator.is_running

            if not is_running:
                await self.orchestrator.start()

                msg = "🚀 BOT Trading v3 запущен!\n"
                msg += f"Активных трейдеров: {len(self.orchestrator.trader_manager.traders)}\n"
                msg += "Используй /menu для управления."
            else:
                msg = "🤖 Бот уже запущен! Нажми /menu для команд."

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            await update.message.reply_text(f"❌ Ошибка запуска: {e!s}")

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop."""
        try:
            is_running = self.orchestrator.is_running

            if is_running:
                # Останавливаем систему
                await self.orchestrator.stop()
                await update.message.reply_text("⏹️ BOT Trading v3 остановлен.")
            else:
                await update.message.reply_text("⏹️ Торговый цикл уже был остановлен.")

        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            await update.message.reply_text(f"❌ Ошибка остановки: {e!s}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status."""
        status = "🟢 Активен" if self.orchestrator.is_running else "🔴 Остановлен"

        msg = f"📊 Статус системы: {status}\n"
        msg += "📅 Версия: 3.0.0-alpha\n\n"

        if self.orchestrator.is_running:
            # Получаем информацию о трейдерах
            traders = self.orchestrator.trader_manager.traders
            msg += f"👥 Активных трейдеров: {len(traders)}\n"

            for trader_id, trader in traders.items():
                strategy_count = len(trader.strategy_manager.strategies)
                msg += f"\n🤖 {trader_id}:\n"
                msg += f"  - Стратегий: {strategy_count}\n"
                msg += f"  - Статус: {'✅ Активен' if trader.is_running else '⏸️ Остановлен'}\n"

        await update.message.reply_text(msg)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats."""
        try:
            async with get_async_db() as db:
                # Получаем общую статистику
                result = await db.execute(
                    select(func.count(Trade.id), func.sum(Trade.pnl)).where(
                        Trade.status == "closed"
                    )
                )
                count, total_pnl = result.fetchone()

                msg = "📈 Общая статистика:\n"
                msg += f"Закрытых сделок: {count or 0}\n"
                msg += f"Общий PnL: {(total_pnl or 0):.2f} USDT\n"

                # Статистика по трейдерам
                result = await db.execute(
                    select(Trade.trader_id, func.count(Trade.id), func.sum(Trade.pnl))
                    .where(Trade.status == "closed")
                    .group_by(Trade.trader_id)
                )

                trader_stats = result.fetchall()
                if trader_stats:
                    msg += "\n📊 По трейдерам:\n"
                    for trader_id, t_count, t_pnl in trader_stats:
                        win_rate = await self._calculate_win_rate(db, trader_id)
                        msg += f"\n🤖 {trader_id}:\n"
                        msg += f"  Сделок: {t_count}\n"
                        msg += f"  PnL: {t_pnl:.2f} USDT\n"
                        msg += f"  Win Rate: {win_rate:.1f}%\n"

                await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e!s}")

    async def cmd_sessionpnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /sessionpnl для совместимости с v2."""
        try:
            async with get_async_db() as db:
                # Получаем текущую сессию (последние 24 часа)
                session_start = datetime.utcnow() - timedelta(days=1)

                result = await db.execute(
                    select(func.count(Trade.id), func.sum(Trade.pnl)).where(
                        and_(Trade.status == "closed", Trade.created_at >= session_start)
                    )
                )
                count, pnl = result.fetchone()

                session_id = f"Session_{datetime.now().strftime('%Y_%m_%d')}"
                msg = f"📒 Текущая сессия: {session_id}\n"
                msg += f"Сделок: {count or 0}, PnL: {(pnl or 0):.2f} USDT"

                await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error getting session PnL: {e}")
            await update.message.reply_text(f"❌ Ошибка: {e!s}")

    async def cmd_traders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает список трейдеров."""
        traders = self.orchestrator.trader_manager.list_traders()

        if not traders:
            await update.message.reply_text("📭 Нет активных трейдеров")
            return

        msg = "👥 Список трейдеров:\n\n"
        for trader_info in traders:
            msg += f"🤖 {trader_info['id']}:\n"
            msg += f"  - Стратегий: {trader_info['strategy_count']}\n"
            msg += f"  - Статус: {trader_info['status']}\n"
            msg += f"  - Создан: {trader_info['created_at']}\n\n"

        await update.message.reply_text(msg)

    async def cmd_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает активные стратегии."""
        msg = "📋 Активные стратегии:\n\n"

        traders = self.orchestrator.trader_manager.traders
        if not traders:
            msg += "Нет активных трейдеров"
        else:
            for trader_id, trader in traders.items():
                strategies = trader.strategy_manager.list_strategies()

                if strategies:
                    msg += f"🤖 Трейдер {trader_id}:\n"
                    for strategy in strategies:
                        status_emoji = "✅" if strategy["status"] == "active" else "⏸️"
                        msg += f"  - {strategy['name']} {status_emoji}\n"
                    msg += "\n"

        await update.message.reply_text(msg)

    async def cmd_update_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновляет параметры SL/TP из конфигурации (совместимость с v2)."""
        try:
            # Перезагружаем конфигурацию
            self.config.reload()

            # Обновляем конфигурацию трейдеров
            for trader_id, trader in self.orchestrator.trader_manager.traders.items():
                trader.reload_config()

            msg = "✅ Конфигурация обновлена!\n"
            msg += "Новые параметры будут применены к новым сделкам."

            await update.message.reply_text(msg)

        except Exception as e:
            logger.error(f"Error updating config: {e}")
            await update.message.reply_text(f"❌ Ошибка обновления: {e!s}")

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Главное меню с кнопками."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Статистика", callback_data="stats"),
                InlineKeyboardButton("📈 Сигналы", callback_data="view_signals"),
            ],
            [
                InlineKeyboardButton("👥 Трейдеры", callback_data="traders"),
                InlineKeyboardButton("📋 Стратегии", callback_data="strategies"),
            ],
            [
                InlineKeyboardButton("💰 Баланс", callback_data="balance"),
                InlineKeyboardButton("🔄 Обновить SL/TP", callback_data="refresh_once"),
            ],
            [
                InlineKeyboardButton("📈 Последние сделки", callback_data="recent_trades"),
                InlineKeyboardButton("📊 Мониторинг", callback_data="monitor_trades"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        version = self.config.get_value("bot_version", "3.0.0-alpha")
        msg = f"🎛️ BOT Trading v3 ({version})\n"
        msg += "Выберите действие:"

        await update.message.reply_text(msg, reply_markup=reply_markup)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по командам."""
        version = self.config.get_value("bot_version", "3.0.0-alpha")
        msg = f"""
📚 BOT Trading v3 ({version}) - Команды:

/start - Запустить систему
/stop - Остановить систему
/status - Текущий статус
/stats - Общая статистика
/sessionpnl - PnL текущей сессии
/traders - Список трейдеров
/strategies - Активные стратегии
/update_config - Обновить конфигурацию
/menu - Главное меню
/help - Эта справка

🔧 Дополнительные возможности доступны через /menu
        """
        await update.message.reply_text(msg)

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок."""
        query = update.callback_query
        await query.answer()

        handlers = {
            "stats": self._handle_stats_callback,
            "view_signals": self._handle_signals_callback,
            "traders": self._handle_traders_callback,
            "strategies": self._handle_strategies_callback,
            "balance": self._handle_balance_callback,
            "refresh_once": self._handle_refresh_config_callback,
            "recent_trades": self._handle_recent_trades_callback,
            "monitor_trades": self._handle_monitor_trades_callback,
        }

        handler = handlers.get(query.data)
        if handler:
            await handler(query)
        else:
            await query.edit_message_text(f"❌ Неизвестная команда: {query.data}")

    async def _handle_stats_callback(self, query):
        """Обработчик кнопки статистики."""

        # Создаем фейковый объект для переиспользования cmd_stats
        class FakeUpdate:
            message = query

        await self.cmd_stats(FakeUpdate(), None)

    async def _handle_signals_callback(self, query):
        """Показывает последние сигналы."""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(Signal).order_by(Signal.created_at.desc()).limit(10)
                )
                signals = result.scalars().all()

                if not signals:
                    await query.edit_message_text("📡 Нет сигналов")
                    return

                msg = "📡 Последние 10 сигналов:\n\n"
                for signal in signals:
                    emoji = "🟢" if signal.action == "buy" else "🔴"
                    msg += f"{emoji} {signal.symbol} - {signal.action.upper()}\n"
                    msg += f"  Источник: {signal.source}\n"
                    msg += f"  Сила: {signal.strength:.2f}\n"
                    msg += f"  {signal.created_at.strftime('%H:%M:%S')}\n\n"

                await query.edit_message_text(msg)

        except Exception as e:
            logger.error(f"Error getting signals: {e}")
            await query.edit_message_text(f"❌ Ошибка: {e!s}")

    async def _handle_balance_callback(self, query):
        """Показывает баланс."""
        try:
            async with get_async_db() as db:
                result = await db.execute(select(Balance).order_by(Balance.asset))
                balances = result.scalars().all()

                if not balances:
                    await query.edit_message_text("💰 Нет данных о балансе")
                    return

                msg = "💰 Баланс по активам:\n\n"

                # Группируем по активам
                asset_totals = {}
                for balance in balances:
                    if balance.asset not in asset_totals:
                        asset_totals[balance.asset] = {"free": 0, "locked": 0}

                    asset_totals[balance.asset]["free"] += balance.free
                    asset_totals[balance.asset]["locked"] += balance.locked

                for asset, totals in asset_totals.items():
                    total = totals["free"] + totals["locked"]
                    if total > 0.0001:  # Показываем только значимые балансы
                        msg += f"{asset}:\n"
                        msg += f"  Свободно: {totals['free']:.4f}\n"
                        if totals["locked"] > 0:
                            msg += f"  Заблокировано: {totals['locked']:.4f}\n"
                        msg += f"  Всего: {total:.4f}\n\n"

                await query.edit_message_text(msg)

        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            await query.edit_message_text(f"❌ Ошибка: {e!s}")

    async def _handle_refresh_config_callback(self, query):
        """Обновляет конфигурацию (совместимость с v2)."""
        try:
            # Перезагружаем конфигурацию
            self.config.reload()

            msg = "✅ Конфигурация SL/TP обновлена из config файлов!\n"
            msg += "Новые параметры будут применены к новым сделкам."

            await query.edit_message_text(msg)

        except Exception as e:
            logger.error(f"Error refreshing config: {e}")
            await query.edit_message_text(f"❌ Ошибка: {e!s}")

    async def _handle_recent_trades_callback(self, query):
        """Показывает последние сделки."""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(Trade)
                    .where(Trade.status == "closed")
                    .order_by(Trade.created_at.desc())
                    .limit(10)
                )
                trades = result.scalars().all()

                if not trades:
                    await query.edit_message_text("📈 Нет закрытых сделок")
                    return

                msg = "📈 Последние 10 сделок:\n\n"
                for trade in trades:
                    emoji = "🟢" if trade.pnl > 0 else "🔴"
                    msg += f"{emoji} {trade.symbol} {trade.side.upper()}\n"
                    msg += f"  Объем: {trade.quantity}\n"
                    msg += f"  Вход: {trade.entry_price} → Выход: {trade.exit_price}\n"
                    msg += f"  PnL: {trade.pnl:.2f} USDT ({trade.pnl_percentage:.2f}%)\n"
                    msg += f"  {trade.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"

                await query.edit_message_text(msg)

        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            await query.edit_message_text(f"❌ Ошибка: {e!s}")

    async def _handle_monitor_trades_callback(self, query):
        """Мониторинг открытых позиций."""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(Trade).where(Trade.status == "open").order_by(Trade.created_at.desc())
                )
                open_trades = result.scalars().all()

                if not open_trades:
                    await query.edit_message_text("📊 Нет открытых позиций")
                    return

                msg = "📊 Открытые позиции:\n\n"
                total_pnl = 0

                for trade in open_trades:
                    # Здесь можно добавить расчет текущего PnL
                    msg += f"{'🟢' if trade.side == 'buy' else '🔴'} {trade.symbol}\n"
                    msg += f"  Трейдер: {trade.trader_id}\n"
                    msg += f"  Объем: {trade.quantity}\n"
                    msg += f"  Вход: {trade.entry_price}\n"
                    msg += f"  SL: {trade.stop_loss or 'Не установлен'}\n"
                    msg += f"  TP: {trade.take_profit or 'Не установлен'}\n"
                    msg += f"  Время: {trade.created_at.strftime('%H:%M:%S')}\n\n"

                await query.edit_message_text(msg)

        except Exception as e:
            logger.error(f"Error monitoring trades: {e}")
            await query.edit_message_text(f"❌ Ошибка: {e!s}")

    async def _handle_traders_callback(self, query):
        """Обработчик кнопки трейдеров."""

        class FakeUpdate:
            message = query

        await self.cmd_traders(FakeUpdate(), None)

    async def _handle_strategies_callback(self, query):
        """Обработчик кнопки стратегий."""

        class FakeUpdate:
            message = query

        await self.cmd_strategies(FakeUpdate(), None)

    async def _calculate_win_rate(self, db, trader_id: str) -> float:
        """Рассчитывает Win Rate для трейдера."""
        result = await db.execute(
            select(func.count(Trade.id).filter(Trade.pnl > 0), func.count(Trade.id)).where(
                and_(Trade.trader_id == trader_id, Trade.status == "closed")
            )
        )
        wins, total = result.fetchone()

        if total == 0:
            return 0.0

        return (wins / total) * 100

    async def send_notification(self, message: str, parse_mode: str = None):
        """
        Отправляет уведомление в Telegram.

        Args:
            message: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
        """
        if not self.chat_id:
            logger.warning("Chat ID not configured, skipping notification")
            return

        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id, text=message, parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    async def send_trade_notification(self, trade: Trade):
        """Отправляет уведомление о сделке."""
        emoji = "🟢" if trade.side == "buy" else "🔴"
        status_emoji = "✅" if trade.status == "closed" else "🔄"

        msg = f"{status_emoji} <b>Сделка {trade.status.upper()}</b>\n\n"
        msg += f"{emoji} {trade.symbol} {trade.side.upper()}\n"
        msg += f"Трейдер: {trade.trader_id}\n"
        msg += f"Объем: {trade.quantity}\n"

        if trade.status == "open":
            msg += f"Цена входа: {trade.entry_price}\n"
            if trade.stop_loss:
                msg += f"Stop Loss: {trade.stop_loss}\n"
            if trade.take_profit:
                msg += f"Take Profit: {trade.take_profit}\n"
        else:  # closed
            msg += f"Вход: {trade.entry_price} → Выход: {trade.exit_price}\n"
            pnl_emoji = "💰" if trade.pnl > 0 else "💸"
            msg += f"{pnl_emoji} PnL: {trade.pnl:.2f} USDT ({trade.pnl_percentage:.2f}%)\n"

        await self.send_notification(msg, parse_mode="HTML")

    async def send_error_notification(self, error: str, critical: bool = False):
        """Отправляет уведомление об ошибке."""
        emoji = "🚨" if critical else "⚠️"

        msg = f"{emoji} <b>{'КРИТИЧЕСКАЯ ОШИБКА' if critical else 'Ошибка'}</b>\n\n"
        msg += f"{error}\n\n"
        msg += f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await self.send_notification(msg, parse_mode="HTML")

        # Обновляем статистику ошибок
        self.error_stats["errors"] += 1
        self.error_stats["error_times"].append(datetime.now())

        # Проверяем пороги ошибок (из v2)
        self._check_error_threshold()

    def _check_error_threshold(self):
        """Проверяет пороги ошибок для автоматических действий."""
        # Очищаем старые ошибки (старше 1 часа)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.error_stats["error_times"] = [
            t for t in self.error_stats["error_times"] if t > cutoff_time
        ]

        # Проверяем количество ошибок за последний час
        recent_errors = len(self.error_stats["error_times"])

        error_threshold = self.config.get_value("telegram.error_threshold", 10)

        if recent_errors >= error_threshold:
            logger.critical(f"Error threshold reached: {recent_errors} errors in last hour")
            # Здесь можно добавить автоматические действия

    async def run(self):
        """Запускает Telegram бота."""
        logger.info("Starting Telegram bot...")

        # Отправляем стартовое уведомление
        await self.send_notification("🤖 BOT Trading v3 Telegram Bot запущен!")

        # Запускаем polling
        await self.app.run_polling()

    async def stop(self):
        """Останавливает Telegram бота."""
        logger.info("Stopping Telegram bot...")
        await self.app.stop()
        await self.send_notification("🛑 BOT Trading v3 Telegram Bot остановлен.")
