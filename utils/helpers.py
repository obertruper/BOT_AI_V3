"""
Вспомогательные функции для BOT_Trading v3.0
"""

import signal
import sys
from datetime import datetime
from typing import Any

import psutil


def print_banner() -> None:
    """Вывод баннера системы"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║                          BOT_Trading v3.0                                    ║
    ║                   Мульти-трейдер торговая система                             ║
    ║                                                                               ║
    ║  🚀 Мульти-трейдер архитектура                                               ║
    ║  🔄 Поддержка 7+ криптобирж                                                  ║
    ║  🤖 ML-предсказания и стратегии                                              ║
    ║  📊 Real-time мониторинг                                                     ║
    ║  🛡️ Продвинутое управление рисками                                           ║
    ║                                                                               ║
    ║  © 2025 OberTrading Team                                                     ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def get_system_resources() -> dict[str, Any]:
    """Получение информации о системных ресурсах"""
    try:
        # Память
        memory = psutil.virtual_memory()

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)

        # Диск
        disk = psutil.disk_usage("/")

        # Сетевые соединения
        net_connections = len(psutil.net_connections())

        return {
            "memory_total_mb": round(memory.total / (1024 * 1024), 2),
            "memory_available_mb": round(memory.available / (1024 * 1024), 2),
            "memory_percent": memory.percent,
            "cpu_percent": cpu_percent,
            "cpu_count": psutil.cpu_count(),
            "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
            "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
            "disk_used_percent": round((disk.used / disk.total) * 100, 2),
            "net_connections": net_connections,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": f"Не удалось получить системные ресурсы: {e}",
            "timestamp": datetime.now().isoformat(),
        }


def setup_signal_handlers(shutdown_callback) -> None:
    """Настройка обработчиков системных сигналов"""

    def signal_handler(signum, frame):
        print(f"\n📨 Получен сигнал {signum} - начинаем graceful shutdown...")
        shutdown_callback()

    # Регистрация обработчиков
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Завершение процесса

    # Только для Unix-систем
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, signal_handler)  # Hangup


def validate_python_version() -> bool:
    """Проверка версии Python"""
    required_version = (3, 8)
    current_version = sys.version_info[:2]

    if current_version < required_version:
        print(f"❌ Требуется Python {required_version[0]}.{required_version[1]} или выше")
        print(f"❌ Текущая версия: {current_version[0]}.{current_version[1]}")
        return False

    return True


def format_bytes(bytes_value: int) -> str:
    """Форматирование байтов в читаемый формат"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_duration(seconds: float) -> str:
    """Форматирование времени в читаемый формат"""
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} мин"
    elif seconds < 86400:
        return f"{seconds / 3600:.1f} ч"
    else:
        return f"{seconds / 86400:.1f} дн"


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def truncate_string(text: str, max_length: int = 100) -> str:
    """Обрезка строки до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def get_config_from_env(key: str, default: Any = None) -> Any:
    """Получение конфигурации из переменных окружения"""
    import os

    value = os.getenv(key, default)

    # Попытка преобразования булевых значений
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        elif value.lower() in ("false", "0", "no", "off"):
            return False

    return value


def generate_id(prefix: str = "id") -> str:
    """Генерация уникального ID"""
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def is_valid_symbol(symbol: str) -> bool:
    """Проверка валидности торгового символа"""
    if not symbol or not isinstance(symbol, str):
        return False

    # Базовая проверка формата
    if len(symbol) < 3 or len(symbol) > 20:
        return False

    # Проверка на допустимые символы
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return all(c in allowed_chars for c in symbol.upper())


def normalize_symbol(symbol: str) -> str:
    """Нормализация торгового символа"""
    if not symbol:
        return ""

    return symbol.upper().strip()


def get_timestamp() -> str:
    """Получение текущего timestamp в ISO формате"""
    return datetime.now().isoformat()


def parse_timeframe(timeframe: str) -> int:
    """Преобразование таймфрейма в секунды"""
    timeframe_map = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "1w": 604800,
    }

    return timeframe_map.get(timeframe.lower(), 60)


def create_directory_if_not_exists(path: str) -> None:
    """Создание директории если не существует"""
    import os

    os.makedirs(path, exist_ok=True)


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Проверка доступности порта"""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
            return True
    except OSError:
        return False


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """Декоратор для повторных попыток при исключениях"""
    import asyncio
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(delay * (2**attempt))

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (2**attempt))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
