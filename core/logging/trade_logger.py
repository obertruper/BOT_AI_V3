#!/usr/bin/env python3
"""
Enhanced Trade Logger для BOT Trading v3

Централизованная система логирования всех торговых операций
с детальным отслеживанием каждого этапа сделки.
"""

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder

# Настройка structlog для красивого вывода
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        CallsiteParameterAdder(parameters=[CallsiteParameter.FILENAME, CallsiteParameter.LINENO]),
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


class TradeLogger:
    """
    Централизованный логгер для всех торговых операций.

    Обеспечивает детальное логирование:
    - Сигналов и их обработки
    - Создания и исполнения ордеров
    - Установки и изменения SL/TP
    - Частичных закрытий позиций
    - Работы trailing stop
    - PnL и финансовых результатов
    """

    def __init__(self, name: str = "trade_logger", log_dir: str = "data/logs"):
        """
        Инициализация логгера.

        Args:
            name: Имя логгера
            log_dir: Директория для логов
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Основной структурированный логгер
        self.logger = structlog.get_logger(name)

        # Файловый логгер для торговых операций
        self.trade_log_file = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.log"
        self._setup_file_logger()

        # Счетчики для статистики
        self.stats = {
            "signals_received": 0,
            "orders_created": 0,
            "orders_executed": 0,
            "sltp_set": 0,
            "sltp_triggered": 0,
            "partial_closes": 0,
            "trailing_updates": 0,
            "errors": 0,
        }

    def _setup_file_logger(self):
        """Настройка файлового логгера"""
        file_handler = logging.FileHandler(self.trade_log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        file_logger = logging.getLogger(f"{self.name}_file")
        file_logger.addHandler(file_handler)
        file_logger.setLevel(logging.DEBUG)
        self.file_logger = file_logger

    def _log_to_file(self, level: str, message: str, data: dict = None):
        """Запись в файл с JSON данными"""
        if data:
            message = f"{message} | DATA: {json.dumps(data, default=str, ensure_ascii=False)}"

        getattr(self.file_logger, level.lower())(message)

    # ========== SIGNAL LOGGING ==========

    def log_signal_received(self, signal: dict[str, Any]):
        """Логирование получения сигнала"""
        self.stats["signals_received"] += 1

        log_data = {
            "signal_id": signal.get("id"),
            "symbol": signal.get("symbol"),
            "signal_type": signal.get("signal_type"),
            "strength": signal.get("strength"),
            "confidence": signal.get("confidence"),
            "source": signal.get("source"),
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"📡 СИГНАЛ ПОЛУЧЕН: {signal.get('symbol')} {signal.get('signal_type')}",
            **log_data,
        )
        self._log_to_file("info", "SIGNAL_RECEIVED", log_data)

        return log_data

    def log_signal_processing(self, signal_id: str, action: str, details: dict = None):
        """Логирование обработки сигнала"""
        log_data = {
            "signal_id": signal_id,
            "action": action,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"⚙️ ОБРАБОТКА СИГНАЛА: {action}", **log_data)
        self._log_to_file("info", "SIGNAL_PROCESSING", log_data)

    def log_signal_rejected(self, signal_id: str, reason: str):
        """Логирование отклонения сигнала"""
        log_data = {
            "signal_id": signal_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.warning(f"❌ СИГНАЛ ОТКЛОНЕН: {reason}", **log_data)
        self._log_to_file("warning", "SIGNAL_REJECTED", log_data)

    # ========== ORDER LOGGING ==========

    def log_order_creation(self, order: dict[str, Any]):
        """Логирование создания ордера"""
        self.stats["orders_created"] += 1

        log_data = {
            "order_id": order.get("id"),
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "type": order.get("order_type"),
            "quantity": str(order.get("quantity", 0)),
            "price": str(order.get("price", 0)),
            "leverage": order.get("leverage"),
            "signal_id": order.get("signal_id"),
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"📝 ОРДЕР СОЗДАН: {order.get('symbol')} {order.get('side')} "
            f"qty={order.get('quantity')} @ {order.get('price')}",
            **log_data,
        )
        self._log_to_file("info", "ORDER_CREATED", log_data)

        return log_data

    def log_order_submission(self, order_id: str, exchange: str, response: dict = None):
        """Логирование отправки ордера на биржу"""
        log_data = {
            "order_id": order_id,
            "exchange": exchange,
            "response": response or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"📤 ОРДЕР ОТПРАВЛЕН на {exchange}", **log_data)
        self._log_to_file("info", "ORDER_SUBMITTED", log_data)

    def log_order_execution(self, order_id: str, execution_data: dict):
        """Логирование исполнения ордера"""
        self.stats["orders_executed"] += 1

        log_data = {
            "order_id": order_id,
            "executed_qty": str(execution_data.get("executed_qty", 0)),
            "executed_price": str(execution_data.get("executed_price", 0)),
            "commission": str(execution_data.get("commission", 0)),
            "status": execution_data.get("status"),
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"✅ ОРДЕР ИСПОЛНЕН: {order_id} "
            f"qty={execution_data.get('executed_qty')} @ {execution_data.get('executed_price')}",
            **log_data,
        )
        self._log_to_file("info", "ORDER_EXECUTED", log_data)

    def log_order_cancelled(self, order_id: str, reason: str):
        """Логирование отмены ордера"""
        log_data = {
            "order_id": order_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.warning(f"🚫 ОРДЕР ОТМЕНЕН: {order_id} - {reason}", **log_data)
        self._log_to_file("warning", "ORDER_CANCELLED", log_data)

    # ========== SL/TP LOGGING ==========

    def log_sltp_setup(
        self,
        position_id: str,
        sl_price: float = None,
        tp_price: float = None,
        partial_levels: list = None,
    ):
        """Логирование установки SL/TP"""
        self.stats["sltp_set"] += 1

        log_data = {
            "position_id": position_id,
            "sl_price": str(sl_price) if sl_price else None,
            "tp_price": str(tp_price) if tp_price else None,
            "partial_levels": partial_levels,
            "timestamp": datetime.now().isoformat(),
        }

        message = f"🎯 SL/TP УСТАНОВЛЕН для позиции {position_id}"
        if sl_price:
            message += f" | SL: {sl_price}"
        if tp_price:
            message += f" | TP: {tp_price}"
        if partial_levels:
            message += f" | Частичные уровни: {len(partial_levels)}"

        self.logger.info(message, **log_data)
        self._log_to_file("info", "SLTP_SETUP", log_data)

    def log_sltp_modification(
        self,
        position_id: str,
        modification_type: str,
        old_value: float,
        new_value: float,
        reason: str = "",
    ):
        """Логирование изменения SL/TP"""
        log_data = {
            "position_id": position_id,
            "type": modification_type,  # "SL" или "TP"
            "old_value": str(old_value),
            "new_value": str(new_value),
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"📝 {modification_type} ИЗМЕНЕН: {old_value} → {new_value} | {reason}",
            **log_data,
        )
        self._log_to_file("info", "SLTP_MODIFIED", log_data)

    def log_sltp_triggered(
        self, position_id: str, trigger_type: str, trigger_price: float, pnl: float
    ):
        """Логирование срабатывания SL/TP"""
        self.stats["sltp_triggered"] += 1

        log_data = {
            "position_id": position_id,
            "trigger_type": trigger_type,  # "SL" или "TP"
            "trigger_price": str(trigger_price),
            "pnl": str(pnl),
            "timestamp": datetime.now().isoformat(),
        }

        emoji = "🔴" if trigger_type == "SL" else "🟢"
        self.logger.info(
            f"{emoji} {trigger_type} СРАБОТАЛ @ {trigger_price} | PnL: {pnl}",
            **log_data,
        )
        self._log_to_file("info", "SLTP_TRIGGERED", log_data)

    # ========== PARTIAL CLOSE LOGGING ==========

    def log_partial_close(
        self,
        position_id: str,
        level: int,
        percent: float,
        quantity: float,
        price: float,
    ):
        """Логирование частичного закрытия"""
        self.stats["partial_closes"] += 1

        log_data = {
            "position_id": position_id,
            "level": level,
            "percent": percent,
            "quantity": str(quantity),
            "price": str(price),
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"📊 ЧАСТИЧНОЕ ЗАКРЫТИЕ L{level}: {percent}% @ {price} | qty: {quantity}",
            **log_data,
        )
        self._log_to_file("info", "PARTIAL_CLOSE", log_data)

    def log_sl_moved_to_breakeven(self, position_id: str, entry_price: float, new_sl: float):
        """Логирование переноса SL в безубыток"""
        log_data = {
            "position_id": position_id,
            "entry_price": str(entry_price),
            "new_sl": str(new_sl),
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(f"🔒 SL ПЕРЕНЕСЕН В БЕЗУБЫТОК: {new_sl} (вход: {entry_price})", **log_data)
        self._log_to_file("info", "SL_TO_BREAKEVEN", log_data)

    # ========== TRAILING STOP LOGGING ==========

    def log_trailing_activated(
        self, position_id: str, activation_price: float, profit_percent: float
    ):
        """Логирование активации trailing stop"""
        log_data = {
            "position_id": position_id,
            "activation_price": str(activation_price),
            "profit_percent": profit_percent,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"🎯 TRAILING STOP АКТИВИРОВАН при +{profit_percent}% @ {activation_price}",
            **log_data,
        )
        self._log_to_file("info", "TRAILING_ACTIVATED", log_data)

    def log_trailing_update(
        self, position_id: str, old_sl: float, new_sl: float, current_price: float
    ):
        """Логирование обновления trailing stop"""
        self.stats["trailing_updates"] += 1

        log_data = {
            "position_id": position_id,
            "old_sl": str(old_sl),
            "new_sl": str(new_sl),
            "current_price": str(current_price),
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"📈 TRAILING UPDATE: SL {old_sl} → {new_sl} | Цена: {current_price}",
            **log_data,
        )
        self._log_to_file("info", "TRAILING_UPDATE", log_data)

    # ========== POSITION LOGGING ==========

    def log_position_opened(self, position: dict[str, Any]):
        """Логирование открытия позиции"""
        log_data = {
            "position_id": position.get("id"),
            "symbol": position.get("symbol"),
            "side": position.get("side"),
            "size": str(position.get("size", 0)),
            "entry_price": str(position.get("entry_price", 0)),
            "leverage": position.get("leverage"),
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.info(
            f"🟢 ПОЗИЦИЯ ОТКРЫТА: {position.get('symbol')} {position.get('side')} "
            f"size={position.get('size')} @ {position.get('entry_price')}",
            **log_data,
        )
        self._log_to_file("info", "POSITION_OPENED", log_data)

    def log_position_closed(
        self, position_id: str, close_price: float, pnl: float, close_reason: str = ""
    ):
        """Логирование закрытия позиции"""
        log_data = {
            "position_id": position_id,
            "close_price": str(close_price),
            "pnl": str(pnl),
            "close_reason": close_reason,
            "timestamp": datetime.now().isoformat(),
        }

        emoji = "🟢" if pnl > 0 else "🔴"
        self.logger.info(
            f"{emoji} ПОЗИЦИЯ ЗАКРЫТА @ {close_price} | PnL: {pnl} | {close_reason}",
            **log_data,
        )
        self._log_to_file("info", "POSITION_CLOSED", log_data)

    def log_position_update(self, position_id: str, update_type: str, data: dict):
        """Логирование обновления позиции"""
        log_data = {
            "position_id": position_id,
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        self.logger.debug(f"📝 ПОЗИЦИЯ ОБНОВЛЕНА: {update_type}", **log_data)
        self._log_to_file("debug", "POSITION_UPDATE", log_data)

    # ========== PNL LOGGING ==========

    def log_pnl_update(
        self,
        position_id: str,
        unrealized_pnl: float,
        realized_pnl: float = 0,
        pnl_percent: float = 0,
    ):
        """Логирование обновления PnL"""
        log_data = {
            "position_id": position_id,
            "unrealized_pnl": str(unrealized_pnl),
            "realized_pnl": str(realized_pnl),
            "pnl_percent": pnl_percent,
            "timestamp": datetime.now().isoformat(),
        }

        emoji = "📈" if unrealized_pnl > 0 else "📉"
        self.logger.debug(
            f"{emoji} PNL: Unrealized={unrealized_pnl} ({pnl_percent}%) | Realized={realized_pnl}",
            **log_data,
        )

        # В файл пишем только значительные изменения
        if abs(pnl_percent) > 0.5:  # Более 0.5%
            self._log_to_file("info", "PNL_UPDATE", log_data)

    # ========== ERROR LOGGING ==========

    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: dict = None,
        exception: Exception = None,
    ):
        """Логирование ошибок"""
        self.stats["errors"] += 1

        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }

        if exception:
            log_data["traceback"] = traceback.format_exc()

        self.logger.error(f"❌ ОШИБКА [{error_type}]: {error_message}", **log_data)
        self._log_to_file("error", "ERROR", log_data)

    # ========== STATISTICS ==========

    def log_daily_summary(self):
        """Логирование дневной статистики"""
        log_data = {"stats": self.stats.copy(), "timestamp": datetime.now().isoformat()}

        self.logger.info(
            f"📊 ДНЕВНАЯ СТАТИСТИКА: "
            f"Сигналов: {self.stats['signals_received']} | "
            f"Ордеров: {self.stats['orders_created']}/{self.stats['orders_executed']} | "
            f"SL/TP: {self.stats['sltp_set']}/{self.stats['sltp_triggered']} | "
            f"Ошибок: {self.stats['errors']}",
            **log_data,
        )
        self._log_to_file("info", "DAILY_SUMMARY", log_data)

    def get_statistics(self) -> dict:
        """Получение текущей статистики"""
        return self.stats.copy()

    def reset_statistics(self):
        """Сброс статистики"""
        for key in self.stats:
            self.stats[key] = 0

        self.logger.info("📊 Статистика сброшена")


# Глобальный экземпляр логгера
_trade_logger: TradeLogger | None = None


def get_trade_logger() -> TradeLogger:
    """Получение глобального экземпляра trade logger"""
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger


# Удобные функции для быстрого доступа
def log_trade_event(event_type: str, **kwargs):
    """Быстрое логирование торгового события"""
    logger = get_trade_logger()

    # Маппинг типов событий на методы логгера
    event_methods = {
        "signal_received": logger.log_signal_received,
        "order_created": logger.log_order_creation,
        "order_executed": logger.log_order_execution,
        "sltp_setup": logger.log_sltp_setup,
        "position_opened": logger.log_position_opened,
        "position_closed": logger.log_position_closed,
        "partial_close": logger.log_partial_close,
        "trailing_update": logger.log_trailing_update,
        "error": logger.log_error,
    }

    method = event_methods.get(event_type)
    if method:
        return method(**kwargs)
    else:
        logger.logger.warning(f"Неизвестный тип события: {event_type}", **kwargs)
