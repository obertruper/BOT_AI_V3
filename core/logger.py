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
    Настройка логгера

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

    # Форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик для общих логов
    file_handler = logging.FileHandler(
        log_dir / f"bot_trading_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Файловый обработчик для ошибок
    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger


# Создаем основной логгер для модуля
logger = setup_logger(__name__)
