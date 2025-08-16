"""
Logger Factory для BOT_Trading v3.0

Расширенная система логирования с поддержкой:
- Мульти-трейдер логирования с trader_id префиксами
- Structured logging для лучшей аналитики
- Централизованная конфигурация логгеров
- Thread-safe операции
- Обратная совместимость с v1.0/v2.0
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any


@dataclass
class LoggerConfig:
    """Конфигурация логгера"""

    name: str
    level: int | str = logging.INFO
    format_type: str = "standard"  # standard, detailed, json
    file_path: str | None = None
    console_output: bool = True
    rotation: str = "size"  # size, time, none
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    when: str = "midnight"  # for time rotation
    trader_id: str | None = None
    session_id: str | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)


class TraderLogFormatter(logging.Formatter):
    """Специальный форматтер для трейдеров с trader_id"""

    def __init__(
        self,
        format_string: str,
        trader_id: str | None = None,
        session_id: str | None = None,
    ):
        super().__init__(format_string, datefmt="%Y-%m-%d %H:%M:%S")
        self.trader_id = trader_id
        self.session_id = session_id

    def format(self, record: logging.LogRecord) -> str:
        # Добавляем trader_id и session_id в record
        if self.trader_id:
            record.trader_id = self.trader_id
        if self.session_id:
            record.session_id = self.session_id

        # Добавляем дополнительные поля если они есть
        if hasattr(record, "extra_fields"):
            for key, value in record.extra_fields.items():
                setattr(record, key, value)

        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON форматтер для structured logging"""

    def __init__(self, trader_id: str | None = None, session_id: str | None = None):
        super().__init__()
        self.trader_id = trader_id
        self.session_id = session_id

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Добавляем трейдер информацию
        if self.trader_id:
            log_entry["trader_id"] = self.trader_id
        if self.session_id:
            log_entry["session_id"] = self.session_id

        # Добавляем exception информацию
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Добавляем дополнительные поля
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class LoggerFactory:
    """
    Фабрика логгеров для BOT_Trading v3.0

    Обеспечивает:
    - Централизованное создание и управление логгерами
    - Поддержку мульти-трейдер логирования
    - Различные форматы вывода (standard, detailed, JSON)
    - Thread-safe операции
    - Обратную совместимость
    """

    # Форматы логирования
    FORMATS = {
        "standard": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        "trader": "%(asctime)s - [%(trader_id)s] %(name)s - %(levelname)s - %(message)s",
        "trader_detailed": "%(asctime)s - [%(trader_id)s:%(session_id)s] %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    }

    # Словарь уровней логирования
    LOG_LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(self):
        self._loggers: dict[str, logging.Logger] = {}
        self._configs: dict[str, LoggerConfig] = {}
        self._lock = asyncio.Lock() if asyncio.iscoroutinefunction(self.__init__) else None

    def get_logger(
        self,
        name: str,
        trader_id: str | None = None,
        session_id: str | None = None,
        config: LoggerConfig | None = None,
    ) -> logging.Logger:
        """
        Получение логгера с поддержкой мульти-трейдеров

        Args:
            name: Имя логгера
            trader_id: ID трейдера (для мульти-трейдер системы)
            session_id: ID сессии трейдера
            config: Пользовательская конфигурация

        Returns:
            Настроенный логгер
        """
        # Формируем уникальный ключ логгера
        logger_key = self._make_logger_key(name, trader_id, session_id)

        # Возвращаем существующий логгер если есть
        if logger_key in self._loggers:
            return self._loggers[logger_key]

        # Создаем новый логгер
        logger = self._create_logger(name, trader_id, session_id, config)
        self._loggers[logger_key] = logger

        return logger

    def _make_logger_key(self, name: str, trader_id: str | None, session_id: str | None) -> str:
        """Создание уникального ключа логгера"""
        parts = [name]
        if trader_id:
            parts.append(f"trader_{trader_id}")
        if session_id:
            parts.append(f"session_{session_id}")
        return ".".join(parts)

    def _create_logger(
        self,
        name: str,
        trader_id: str | None = None,
        session_id: str | None = None,
        config: LoggerConfig | None = None,
    ) -> logging.Logger:
        """Создание и настройка нового логгера"""

        # Используем переданную конфигурацию или создаем базовую
        if config is None:
            config = LoggerConfig(name=name, trader_id=trader_id, session_id=session_id)

        # Создаем логгер
        logger_name = self._make_logger_key(name, trader_id, session_id)
        logger = logging.getLogger(logger_name)

        # Устанавливаем уровень
        level = config.level
        if isinstance(level, str):
            level = self.LOG_LEVELS.get(level.lower(), logging.INFO)
        logger.setLevel(level)

        # Очищаем существующие handlers
        logger.handlers.clear()

        # Добавляем console handler если нужен
        if config.console_output:
            console_handler = self._create_console_handler(config, trader_id, session_id)
            logger.addHandler(console_handler)

        # Добавляем file handler если указан путь
        if config.file_path:
            file_handler = self._create_file_handler(config, trader_id, session_id)
            logger.addHandler(file_handler)

        # Предотвращаем передачу сообщений родительским логгерам
        logger.propagate = False

        # Сохраняем конфигурацию
        self._configs[logger_name] = config

        return logger

    def _create_console_handler(
        self, config: LoggerConfig, trader_id: str | None, session_id: str | None
    ) -> logging.StreamHandler:
        """Создание console handler"""
        handler = logging.StreamHandler(sys.stdout)

        # Выбираем формат в зависимости от наличия trader_id
        if trader_id and session_id:
            format_name = "trader_detailed" if config.format_type == "detailed" else "trader"
        elif trader_id:
            format_name = "trader"
        else:
            format_name = config.format_type

        # Создаем форматтер
        if config.format_type == "json":
            formatter = JSONFormatter(trader_id, session_id)
        else:
            format_string = self.FORMATS.get(format_name, self.FORMATS["standard"])
            formatter = TraderLogFormatter(format_string, trader_id, session_id)

        handler.setFormatter(formatter)
        return handler

    def _create_file_handler(
        self, config: LoggerConfig, trader_id: str | None, session_id: str | None
    ) -> logging.Handler:
        """Создание file handler с поддержкой ротации"""

        # Создаем директорию если не существует
        file_path = Path(config.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Создаем handler в зависимости от типа ротации
        if config.rotation == "size":
            handler = RotatingFileHandler(
                config.file_path,
                maxBytes=config.max_bytes,
                backupCount=config.backup_count,
                encoding="utf-8",
            )
        elif config.rotation == "time":
            handler = TimedRotatingFileHandler(
                config.file_path,
                when=config.when,
                backupCount=config.backup_count,
                encoding="utf-8",
            )
        else:
            handler = logging.FileHandler(config.file_path, encoding="utf-8")

        # Создаем форматтер
        if config.format_type == "json":
            formatter = JSONFormatter(trader_id, session_id)
        else:
            format_name = "detailed"  # Для файлов всегда используем detailed
            if trader_id:
                format_name = "trader_detailed"

            format_string = self.FORMATS.get(format_name, self.FORMATS["detailed"])
            formatter = TraderLogFormatter(format_string, trader_id, session_id)

        handler.setFormatter(formatter)
        return handler

    def get_trader_logger(
        self,
        trader_id: str,
        session_id: str | None = None,
        log_file: str | None = None,
    ) -> logging.Logger:
        """
        Создание специального логгера для трейдера

        Args:
            trader_id: ID трейдера
            session_id: ID сессии
            log_file: Путь к файлу логов (опционально)

        Returns:
            Логгер трейдера с префиксом
        """
        # Создаем конфигурацию для трейдера
        config = LoggerConfig(
            name="trader",
            trader_id=trader_id,
            session_id=session_id,
            format_type="detailed",
            file_path=log_file,
        )

        return self.get_logger("trader", trader_id, session_id, config)

    def set_level(self, level: int | str, logger_pattern: str | None = None) -> None:
        """
        Установка уровня логирования

        Args:
            level: Уровень логирования
            logger_pattern: Паттерн имени логгера (None для всех)
        """
        if isinstance(level, str):
            level = self.LOG_LEVELS.get(level.lower(), logging.INFO)

        if logger_pattern is None:
            # Для всех логгеров
            for logger in self._loggers.values():
                logger.setLevel(level)
        else:
            # Для логгеров соответствующих паттерну
            for logger_name, logger in self._loggers.items():
                if logger_pattern in logger_name:
                    logger.setLevel(level)

    def add_file_handler_to_all(
        self,
        log_file: str,
        level: int | str | None = None,
        format_type: str = "detailed",
    ) -> None:
        """Добавление file handler ко всем существующим логгерам"""

        # Нормализуем level
        if isinstance(level, str):
            level = self.LOG_LEVELS.get(level.lower(), logging.DEBUG)
        elif level is None:
            level = logging.DEBUG

        # Создаем директорию
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        for logger_name, logger in self._loggers.items():
            # Проверяем что файлового handler'а еще нет
            has_file_handler = any(
                isinstance(
                    h,
                    (
                        logging.FileHandler,
                        RotatingFileHandler,
                        TimedRotatingFileHandler,
                    ),
                )
                and getattr(h, "baseFilename", "") == os.path.abspath(log_file)
                for h in logger.handlers
            )

            if not has_file_handler:
                # Создаем файловый handler
                file_handler = RotatingFileHandler(
                    log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
                )
                file_handler.setLevel(level)

                # Определяем форматтер из конфигурации логгера
                config = self._configs.get(logger_name)
                if config and config.format_type == "json":
                    formatter = JSONFormatter(config.trader_id, config.session_id)
                else:
                    format_string = self.FORMATS.get(format_type, self.FORMATS["detailed"])
                    trader_id = config.trader_id if config else None
                    session_id = config.session_id if config else None
                    formatter = TraderLogFormatter(format_string, trader_id, session_id)

                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

    def remove_logger(
        self,
        name: str,
        trader_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Удаление логгера"""
        logger_key = self._make_logger_key(name, trader_id, session_id)

        if logger_key in self._loggers:
            logger = self._loggers[logger_key]
            # Закрываем все handlers
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()

            # Удаляем из реестров
            del self._loggers[logger_key]
            if logger_key in self._configs:
                del self._configs[logger_key]

    def get_all_loggers(self) -> dict[str, logging.Logger]:
        """Получение всех зарегистрированных логгеров"""
        return self._loggers.copy()

    def get_logger_config(
        self,
        name: str,
        trader_id: str | None = None,
        session_id: str | None = None,
    ) -> LoggerConfig | None:
        """Получение конфигурации логгера"""
        logger_key = self._make_logger_key(name, trader_id, session_id)
        return self._configs.get(logger_key)

    def shutdown(self) -> None:
        """Корректное завершение работы всех логгеров"""
        for logger in self._loggers.values():
            for handler in logger.handlers:
                handler.flush()
                handler.close()

        self._loggers.clear()
        self._configs.clear()


# Глобальный экземпляр фабрики для обратной совместимости
_global_logger_factory: LoggerFactory | None = None


def get_global_logger_factory() -> LoggerFactory:
    """Получение глобального экземпляра LoggerFactory"""
    global _global_logger_factory
    if _global_logger_factory is None:
        _global_logger_factory = LoggerFactory()
    return _global_logger_factory


# Функции обратной совместимости с v1.0/v2.0
def get_logger(name: str, level: int | None = None, detailed: bool = False) -> logging.Logger:
    """Получение логгера (совместимость с v1.0/v2.0)"""
    factory = get_global_logger_factory()

    config = LoggerConfig(
        name=name,
        level=level or logging.INFO,
        format_type="detailed" if detailed else "standard",
    )

    return factory.get_logger(name, config=config)


def set_level(level: int, logger_name: str | None = None):
    """Установка уровня логирования (совместимость с v1.0/v2.0)"""
    factory = get_global_logger_factory()
    factory.set_level(level, logger_name)


def add_file_handler(
    log_file: str,
    level: int | None = None,
    logger_name: str | None = None,
    detailed: bool = True,
    rotate: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
):
    """Добавление file handler (совместимость с v1.0/v2.0)"""
    factory = get_global_logger_factory()

    if logger_name:
        # Для конкретного логгера
        logger = factory._loggers.get(logger_name)
        if logger:
            # Создаем handler
            if rotate:
                handler = RotatingFileHandler(
                    log_file, maxBytes=max_bytes, backupCount=5, encoding="utf-8"
                )
            else:
                handler = logging.FileHandler(log_file, encoding="utf-8")

            if level is not None:
                handler.setLevel(level)
            else:
                handler.setLevel(logging.DEBUG)

            # Устанавливаем формат
            format_type = "detailed" if detailed else "standard"
            format_string = LoggerFactory.FORMATS.get(
                format_type, LoggerFactory.FORMATS["standard"]
            )
            formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)

            logger.addHandler(handler)
    else:
        # Для всех логгеров
        factory.add_file_handler_to_all(log_file, level, "detailed" if detailed else "standard")


def get_level_name(level: int) -> str:
    """Получение имени уровня логирования (совместимость с v1.0/v2.0)"""
    return logging.getLevelName(level)


def set_logger_properties(
    logger_name: str, propagate: bool = False, level: int | None = None
) -> None:
    """Установка свойств логгера (совместимость с v1.0/v2.0)"""
    logger = logging.getLogger(logger_name)
    logger.propagate = propagate

    if level is not None:
        logger.setLevel(level)


# Convenience functions (совместимость с v1.0/v2.0)
def log_info(message: str) -> None:
    """Log an info message using the root logger."""
    logging.info(message)


def log_warn(message: str) -> None:
    """Log a warning message using the root logger."""
    logging.warning(message)


def log_error(message: str) -> None:
    """Log an error message using the root logger."""
    logging.error(message)


def log_debug(message: str) -> None:
    """Log a debug message using the root logger."""
    logging.debug(message)
