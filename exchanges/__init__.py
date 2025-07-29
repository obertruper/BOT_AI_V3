"""
Exchanges Module для BOT_Trading v3.0

Унифицированная система для работы с криптовалютными биржами:
- Единый интерфейс для всех бирж
- Автоматическое создание клиентов
- Централизованное управление соединениями
- Обратная совместимость с legacy кодом

Поддерживаемые биржи:
- Bybit (полная поддержка)
- Binance (планируется)
- OKX (планируется)
- Bitget (планируется)
- Gate.io (планируется)
- KuCoin (планируется)
- Huobi (планируется)

Использование:
    # Создание клиента через фабрику
    from exchanges import get_exchange_factory
    
    factory = get_exchange_factory()
    bybit_client = factory.create_client("bybit", api_key, api_secret)
    
    # Быстрое создание
    from exchanges import create_bybit_client
    
    client = create_bybit_client(api_key, api_secret)
    
    # Legacy совместимость
    from exchanges.bybit import get_bybit_client
    
    legacy_client = get_bybit_client(api_key, api_secret)
"""

# Основные компоненты
from .factory import (
    ExchangeFactory,
    ExchangeType,
    ExchangeCredentials, 
    ExchangeConfig,
    get_exchange_factory,
    create_bybit_client,
    create_binance_client
)

from .registry import (
    ExchangeRegistry,
    ExchangeMetadata,
    ExchangeStatus,
    get_exchange_registry,
    get_supported_exchanges,
    is_exchange_supported,
    get_exchange_info
)

# Базовые интерфейсы
from .base.exchange_interface import BaseExchangeInterface, ExchangeCapabilities
from .base.models import (
    Position, Order, Balance, Instrument, Ticker, OrderBook, 
    Kline, AccountInfo, ExchangeInfo
)
from .base.order_types import (
    OrderRequest, OrderResponse, OrderStatus, OrderSide, 
    OrderType, TimeInForce
)
from .base.exceptions import (
    ExchangeError, ConnectionError, AuthenticationError, 
    APIError, RateLimitError, OrderError, PositionError, 
    MarketDataError
)

# Специфичные клиенты (для прямого импорта)
from .bybit import BybitClient, clean_symbol

# Версия модуля
__version__ = "3.0.0"

# Экспорт всех публичных классов и функций
__all__ = [
    # Фабрика и конфигурация
    'ExchangeFactory',
    'ExchangeType',
    'ExchangeCredentials',
    'ExchangeConfig',
    'get_exchange_factory',
    'create_bybit_client',
    'create_binance_client',
    
    # Реестр бирж
    'ExchangeRegistry',
    'ExchangeMetadata', 
    'ExchangeStatus',
    'get_exchange_registry',
    'get_supported_exchanges',
    'is_exchange_supported',
    'get_exchange_info',
    
    # Базовые интерфейсы
    'BaseExchangeInterface',
    'ExchangeCapabilities',
    
    # Модели данных
    'Position',
    'Order', 
    'Balance',
    'Instrument',
    'Ticker',
    'OrderBook',
    'Kline',
    'AccountInfo',
    'ExchangeInfo',
    
    # Типы ордеров
    'OrderRequest',
    'OrderResponse', 
    'OrderStatus',
    'OrderSide',
    'OrderType',
    'TimeInForce',
    
    # Исключения
    'ExchangeError',
    'ConnectionError',
    'AuthenticationError',
    'APIError',
    'RateLimitError',
    'OrderError',
    'PositionError',
    'MarketDataError',
    
    # Специфичные клиенты
    'BybitClient',
    'clean_symbol'
]


# Информация о модуле
def get_module_info():
    """Получение информации о модуле exchanges"""
    registry = get_exchange_registry()
    factory = get_exchange_factory()
    
    return {
        "version": __version__,
        "supported_exchanges": get_supported_exchanges(),
        "total_exchanges": len(registry.get_all_exchanges()),
        "active_exchanges": len(registry.get_active_exchanges()),
        "factory_clients": len(factory._client_cache),
        "capabilities": [
            "Unified exchange interface",
            "Legacy compatibility",
            "Automatic client creation",
            "Connection pooling",
            "Rate limiting",
            "Error handling",
            "WebSocket support"
        ]
    }


# Вспомогательные функции для быстрого старта
async def quick_connect(exchange_name: str, api_key: str, api_secret: str, 
                       sandbox: bool = False, **kwargs) -> BaseExchangeInterface:
    """
    Быстрое подключение к бирже
    
    Args:
        exchange_name: Название биржи
        api_key: API ключ
        api_secret: Секретный ключ
        sandbox: Использовать песочницу
        **kwargs: Дополнительные параметры
        
    Returns:
        Подключенный клиент биржи
    """
    factory = get_exchange_factory()
    return await factory.create_and_connect(
        exchange_name, api_key, api_secret, 
        sandbox=sandbox, **kwargs
    )


def validate_exchange_support(exchange_name: str) -> bool:
    """Быстрая проверка поддержки биржи"""
    return is_exchange_supported(exchange_name)


def list_exchange_features(exchange_name: str) -> dict:
    """Получение списка возможностей биржи"""
    info = get_exchange_info(exchange_name)
    return info['capabilities'] if info else {}


# Примеры использования в docstring модуля
__doc__ += """

Примеры использования:

1. Создание клиента через фабрику:
    ```python
    from exchanges import get_exchange_factory
    
    factory = get_exchange_factory()
    client = factory.create_client("bybit", "api_key", "api_secret")
    
    # С автоматическим подключением
    client = await factory.create_and_connect("bybit", "api_key", "api_secret")
    ```

2. Быстрое создание клиента:
    ```python
    from exchanges import create_bybit_client, quick_connect
    
    # Синхронное создание
    client = create_bybit_client("api_key", "api_secret")
    
    # С автоматическим подключением
    client = await quick_connect("bybit", "api_key", "api_secret")
    ```

3. Проверка поддержки биржи:
    ```python
    from exchanges import is_exchange_supported, get_exchange_info
    
    if is_exchange_supported("bybit"):
        info = get_exchange_info("bybit")
        print(f"Bybit поддерживает: {info['capabilities']}")
    ```

4. Legacy совместимость:
    ```python
    from exchanges.bybit import get_bybit_client
    
    # Старый API продолжает работать
    legacy_client = get_bybit_client("api_key", "api_secret")
    ```

5. Работа с ордерами:
    ```python
    from exchanges.base.order_types import OrderRequest, OrderSide, OrderType
    
    order = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.001
    )
    
    response = await client.place_order(order)
    ```
"""