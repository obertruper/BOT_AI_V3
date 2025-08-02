"""
Bybit Exchange Module для BOT_Trading v3.0

Обеспечивает полную интеграцию с Bybit API v5 через:
- Унифицированный клиент (BybitClient)
- Legacy адаптер для обратной совместимости
- Утилиты для работы с символами

Использование:
    # Новый унифицированный API
    from exchanges.bybit import BybitClient

    # Legacy совместимость
    from exchanges.bybit import get_bybit_client, BybitAPIClient

    # Утилиты
    from exchanges.bybit import clean_symbol
"""

from .adapter import BybitAPIClient, BybitLegacyAdapter, get_bybit_client
from .bybit_exchange import BybitExchange, create_bybit_exchange
from .client import BybitClient, clean_symbol

# Экспорт всех публичных классов и функций
__all__ = [
    # Основной exchange класс
    "BybitExchange",
    "create_bybit_exchange",
    # Основной унифицированный клиент
    "BybitClient",
    # Legacy совместимость
    "BybitLegacyAdapter",
    "BybitAPIClient",
    "get_bybit_client",
    # Утилиты
    "clean_symbol",
]

# Версия модуля
__version__ = "3.0.0"

# Информация о модуле
__author__ = "BOT_Trading v3.0"
__description__ = "Unified Bybit exchange integration with legacy compatibility"
