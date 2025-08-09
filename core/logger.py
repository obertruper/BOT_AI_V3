"""
Модуль логирования для BOT_AI_V3
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Настройка оптимизированного логгера с буферизацией и фильтрацией

    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Настроенный логгер
    """
    # Получаем уровень из переменной окружения или используем INFO по умолчанию
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    # Создаем логгер
    logger = logging.getLogger(name)

    # Устанавливаем уровень
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Если уже есть обработчики, не добавляем новые
    if logger.handlers:
        return logger

    # Создаем директорию для логов
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Оптимизированный форматтер (укороченный timestamp)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",  # Укороченный формат времени для экономии места
    )

    # Консольный обработчик только для WARNING и выше в production
    console_level = (
        logging.WARNING if os.getenv("ENVIRONMENT") == "production" else logging.INFO
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Буферизованный файловый обработчик для общих логов
    file_handler = logging.FileHandler(
        log_dir / f"bot_trading_{datetime.now().strftime('%Y%m%d')}.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Добавляем фильтр для исключения шумных сообщений
    def noise_filter(record):
        message = record.getMessage()
        # Исключаем частые неважные сообщения
        noise_keywords = [
            "BrokenPipeError",
            "Загружено и сохранено 0 записей",
            "WebSocket heartbeat",
            "Health check passed",
        ]
        return not any(keyword in message for keyword in noise_keywords)

    file_handler.addFilter(noise_filter)
    logger.addHandler(file_handler)

    # Файловый обработчик для ошибок (без фильтра)
    error_handler = logging.FileHandler(log_dir / "errors.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger


# Создаем основной логгер для модуля
logger = setup_logger(__name__)
