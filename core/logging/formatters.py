"""
Log Formatters для BOT_Trading v3.0

Специализированные форматтеры для различных компонентов системы:
- TraderFormatter: для логов трейдеров с контекстом
- ExchangeFormatter: для логов бирж с API метриками
- StrategyFormatter: для логов стратегий с сигналами
- MLFormatter: для логов ML системы с предсказаниями
- SystemFormatter: для системных логов с метриками
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(Enum):
    """Расширенные уровни логирования"""

    TRADE = 25  # Между INFO и WARNING
    SIGNAL = 22  # Сигналы стратегий
    ML_PREDICTION = 23  # ML предсказания
    EXCHANGE_API = 21  # API вызовы бирж
    POSITION = 24  # Операции с позициями


class BaseFormatter(logging.Formatter):
    """Базовый форматтер с общими возможностями"""

    def __init__(self, format_string: str, include_extra: bool = True):
        super().__init__(format_string, datefmt="%Y-%m-%d %H:%M:%S")
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        # Добавляем timestamp в ISO формате
        record.isotime = datetime.fromtimestamp(record.created).isoformat()

        # Обрабатываем дополнительные поля
        if self.include_extra and hasattr(record, "extra"):
            for key, value in record.extra.items():
                setattr(record, key, value)

        return super().format(record)


class TraderFormatter(BaseFormatter):
    """
    Форматтер для логов трейдеров

    Включает:
    - trader_id и session_id
    - Текущее состояние трейдера
    - Метрики производительности
    - Контекст торговой сессии
    """

    def __init__(
        self,
        trader_id: str,
        session_id: str | None = None,
        include_metrics: bool = True,
    ):
        format_string = (
            "%(isotime)s [TRADER:%(trader_id)s] %(levelname)-8s %(name)s:%(lineno)d - %(message)s"
        )
        if include_metrics:
            format_string += " | %(trader_metrics)s"

        super().__init__(format_string)
        self.trader_id = trader_id
        self.session_id = session_id
        self.include_metrics = include_metrics

    def format(self, record: logging.LogRecord) -> str:
        # Добавляем трейдер информацию
        record.trader_id = self.trader_id
        if self.session_id:
            record.session_id = self.session_id

        # Добавляем метрики если доступны
        if self.include_metrics:
            metrics = getattr(record, "trader_metrics", {})
            if metrics:
                record.trader_metrics = self._format_metrics(metrics)
            else:
                record.trader_metrics = ""

        return super().format(record)

    def _format_metrics(self, metrics: dict[str, Any]) -> str:
        """Форматирование метрик трейдера"""
        parts = []

        if "pnl" in metrics:
            parts.append(f"PnL:{metrics['pnl']:.2f}")
        if "trades" in metrics:
            parts.append(f"Trades:{metrics['trades']}")
        if "success_rate" in metrics:
            parts.append(f"SR:{metrics['success_rate']:.1f}%")
        if "positions" in metrics:
            parts.append(f"Pos:{metrics['positions']}")

        return f"[{' | '.join(parts)}]" if parts else ""


class ExchangeFormatter(BaseFormatter):
    """
    Форматтер для логов бирж

    Включает:
    - Название биржи и endpoint
    - API rate limiting информацию
    - Latency метрики
    - Response статусы
    """

    def __init__(self, exchange_name: str, include_api_metrics: bool = True):
        format_string = (
            "%(isotime)s [EXCHANGE:%(exchange_name)s] %(levelname)-8s %(name)s - %(message)s"
        )
        if include_api_metrics:
            format_string += " | %(api_metrics)s"

        super().__init__(format_string)
        self.exchange_name = exchange_name
        self.include_api_metrics = include_api_metrics

    def format(self, record: logging.LogRecord) -> str:
        record.exchange_name = self.exchange_name

        # Добавляем API метрики
        if self.include_api_metrics:
            api_metrics = getattr(record, "api_metrics", {})
            if api_metrics:
                record.api_metrics = self._format_api_metrics(api_metrics)
            else:
                record.api_metrics = ""

        return super().format(record)

    def _format_api_metrics(self, metrics: dict[str, Any]) -> str:
        """Форматирование API метрик"""
        parts = []

        if "latency_ms" in metrics:
            parts.append(f"Latency:{metrics['latency_ms']:.0f}ms")
        if "rate_limit" in metrics:
            parts.append(f"Rate:{metrics['rate_limit']}")
        if "status_code" in metrics:
            parts.append(f"Status:{metrics['status_code']}")
        if "endpoint" in metrics:
            parts.append(f"EP:{metrics['endpoint']}")

        return f"[{' | '.join(parts)}]" if parts else ""


class StrategyFormatter(BaseFormatter):
    """
    Форматтер для логов стратегий

    Включает:
    - Название стратегии
    - Тип сигнала (BUY/SELL/HOLD)
    - Confidence уровень
    - Используемые индикаторы
    """

    def __init__(self, strategy_name: str, trader_id: str | None = None):
        format_string = "%(isotime)s [STRATEGY:%(strategy_name)s"
        if trader_id:
            format_string += ":%(trader_id)s"
        format_string += "] %(levelname)-8s %(name)s - %(message)s | %(signal_info)s"

        super().__init__(format_string)
        self.strategy_name = strategy_name
        self.trader_id = trader_id

    def format(self, record: logging.LogRecord) -> str:
        record.strategy_name = self.strategy_name
        if self.trader_id:
            record.trader_id = self.trader_id

        # Добавляем информацию о сигнале
        signal_info = getattr(record, "signal_info", {})
        if signal_info:
            record.signal_info = self._format_signal_info(signal_info)
        else:
            record.signal_info = ""

        return super().format(record)

    def _format_signal_info(self, signal: dict[str, Any]) -> str:
        """Форматирование информации о сигнале"""
        parts = []

        if "signal_type" in signal:
            parts.append(f"Signal:{signal['signal_type']}")
        if "confidence" in signal:
            parts.append(f"Conf:{signal['confidence']:.2f}")
        if "symbol" in signal:
            parts.append(f"Symbol:{signal['symbol']}")
        if "price" in signal:
            parts.append(f"Price:{signal['price']}")
        if "indicators" in signal:
            indicators = signal["indicators"]
            if isinstance(indicators, list):
                parts.append(f"Indicators:{','.join(indicators)}")

        return f"[{' | '.join(parts)}]" if parts else ""


class MLFormatter(BaseFormatter):
    """
    Форматтер для логов ML системы

    Включает:
    - Тип модели и версию
    - Предсказания и confidence
    - Feature importance
    - Model performance метрики
    """

    def __init__(self, model_name: str, model_version: str | None = None):
        format_string = "%(isotime)s [ML:%(model_name)s"
        if model_version:
            format_string += ":%(model_version)s"
        format_string += "] %(levelname)-8s %(name)s - %(message)s | %(ml_info)s"

        super().__init__(format_string)
        self.model_name = model_name
        self.model_version = model_version

    def format(self, record: logging.LogRecord) -> str:
        record.model_name = self.model_name
        if self.model_version:
            record.model_version = self.model_version

        # Добавляем ML информацию
        ml_info = getattr(record, "ml_info", {})
        if ml_info:
            record.ml_info = self._format_ml_info(ml_info)
        else:
            record.ml_info = ""

        return super().format(record)

    def _format_ml_info(self, ml_data: dict[str, Any]) -> str:
        """Форматирование ML информации"""
        parts = []

        if "prediction" in ml_data:
            parts.append(f"Pred:{ml_data['prediction']}")
        if "confidence" in ml_data:
            parts.append(f"Conf:{ml_data['confidence']:.3f}")
        if "features_count" in ml_data:
            parts.append(f"Features:{ml_data['features_count']}")
        if "model_score" in ml_data:
            parts.append(f"Score:{ml_data['model_score']:.3f}")
        if "processing_time_ms" in ml_data:
            parts.append(f"Time:{ml_data['processing_time_ms']:.1f}ms")

        return f"[{' | '.join(parts)}]" if parts else ""


class SystemFormatter(BaseFormatter):
    """
    Форматтер для системных логов

    Включает:
    - Системные метрики (CPU, Memory, etc.)
    - Component health status
    - Performance indicators
    """

    def __init__(self, component_name: str, include_system_metrics: bool = True):
        format_string = (
            "%(isotime)s [SYSTEM:%(component_name)s] %(levelname)-8s %(name)s - %(message)s"
        )
        if include_system_metrics:
            format_string += " | %(system_metrics)s"

        super().__init__(format_string)
        self.component_name = component_name
        self.include_system_metrics = include_system_metrics

    def format(self, record: logging.LogRecord) -> str:
        record.component_name = self.component_name

        # Добавляем системные метрики
        if self.include_system_metrics:
            system_metrics = getattr(record, "system_metrics", {})
            if system_metrics:
                record.system_metrics = self._format_system_metrics(system_metrics)
            else:
                record.system_metrics = ""

        return super().format(record)

    def _format_system_metrics(self, metrics: dict[str, Any]) -> str:
        """Форматирование системных метрик"""
        parts = []

        if "cpu_percent" in metrics:
            parts.append(f"CPU:{metrics['cpu_percent']:.1f}%")
        if "memory_mb" in metrics:
            parts.append(f"MEM:{metrics['memory_mb']:.0f}MB")
        if "disk_usage_percent" in metrics:
            parts.append(f"DISK:{metrics['disk_usage_percent']:.1f}%")
        if "network_io" in metrics:
            parts.append(f"NET:{metrics['network_io']}")
        if "active_connections" in metrics:
            parts.append(f"CONN:{metrics['active_connections']}")

        return f"[{' | '.join(parts)}]" if parts else ""


class JSONStructuredFormatter(logging.Formatter):
    """
    JSON форматтер для structured logging

    Создает JSON записи для легкой обработки в системах мониторинга
    """

    def __init__(self, component_type: str, component_id: str | None = None):
        super().__init__()
        self.component_type = component_type
        self.component_id = component_id

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "component_type": self.component_type,
            "logger_name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
            "thread_id": record.thread,
            "process_id": record.process,
        }

        # Добавляем component_id если есть
        if self.component_id:
            log_entry["component_id"] = self.component_id

        # Добавляем exception информацию
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Добавляем все дополнительные поля из record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class MultiLineFormatter(BaseFormatter):
    """
    Форматтер для многострочных сообщений

    Удобен для форматирования сложных данных, JSON, и debug информации
    """

    def __init__(self, prefix: str = "", indent: str = "  "):
        format_string = f"%(isotime)s {prefix}%(levelname)-8s %(name)s - %(message)s"
        super().__init__(format_string)
        self.indent = indent

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)

        # Если сообщение многострочное, добавляем отступы
        if "\n" in formatted:
            lines = formatted.split("\n")
            if len(lines) > 1:
                # Первая строка как есть, остальные с отступом
                formatted = lines[0] + "\n" + "\n".join(self.indent + line for line in lines[1:])

        return formatted


# Фабричные функции для создания форматтеров
def create_trader_formatter(trader_id: str, session_id: str | None = None) -> TraderFormatter:
    """Создание форматтера для трейдера"""
    return TraderFormatter(trader_id, session_id)


def create_exchange_formatter(exchange_name: str) -> ExchangeFormatter:
    """Создание форматтера для биржи"""
    return ExchangeFormatter(exchange_name)


def create_strategy_formatter(
    strategy_name: str, trader_id: str | None = None
) -> StrategyFormatter:
    """Создание форматтера для стратегии"""
    return StrategyFormatter(strategy_name, trader_id)


def create_ml_formatter(model_name: str, model_version: str | None = None) -> MLFormatter:
    """Создание форматтера для ML компонента"""
    return MLFormatter(model_name, model_version)


def create_system_formatter(component_name: str) -> SystemFormatter:
    """Создание форматтера для системного компонента"""
    return SystemFormatter(component_name)


def create_json_formatter(
    component_type: str, component_id: str | None = None
) -> JSONStructuredFormatter:
    """Создание JSON форматтера"""
    return JSONStructuredFormatter(component_type, component_id)


# Utility функции для добавления контекста в log records
def add_trader_context(
    record: logging.LogRecord, trader_id: str, metrics: dict[str, Any] | None = None
):
    """Добавление контекста трейдера к log record"""
    record.trader_id = trader_id
    if metrics:
        record.trader_metrics = metrics


def add_exchange_context(
    record: logging.LogRecord,
    exchange: str,
    api_metrics: dict[str, Any] | None = None,
):
    """Добавление контекста биржи к log record"""
    record.exchange_name = exchange
    if api_metrics:
        record.api_metrics = api_metrics


def add_signal_context(
    record: logging.LogRecord,
    signal_type: str,
    symbol: str,
    confidence: float | None = None,
):
    """Добавление контекста сигнала к log record"""
    signal_info = {"signal_type": signal_type, "symbol": symbol}
    if confidence is not None:
        signal_info["confidence"] = confidence

    record.signal_info = signal_info


def add_ml_context(
    record: logging.LogRecord,
    prediction: Any,
    confidence: float | None = None,
    model_score: float | None = None,
):
    """Добавление ML контекста к log record"""
    ml_info = {"prediction": prediction}
    if confidence is not None:
        ml_info["confidence"] = confidence
    if model_score is not None:
        ml_info["model_score"] = model_score

    record.ml_info = ml_info
