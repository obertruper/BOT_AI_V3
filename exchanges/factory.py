"""
Exchange Factory для BOT_Trading v3.0

Централизованная фабрика для создания клиентов различных бирж
с унифицированным интерфейсом и автоматической конфигурацией.

Поддерживает:
- Автоматическое создание клиентов по названию биржи
- Загрузку конфигурации из различных источников
- Кеширование экземпляров клиентов
- Валидацию параметров подключения
- Graceful fallback при ошибках
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from core.logger import setup_logger

from .base.exceptions import AuthenticationError, ExchangeError
from .base.exchange_interface import BaseExchangeInterface


class ExchangeType(Enum):
    """Поддерживаемые типы бирж"""

    BYBIT = "bybit"
    BINANCE = "binance"
    OKX = "okx"
    BITGET = "bitget"
    GATEIO = "gateio"
    KUCOIN = "kucoin"
    HUOBI = "huobi"


@dataclass
class ExchangeCredentials:
    """Учетные данные для биржи"""

    api_key: str
    api_secret: str
    passphrase: Optional[str] = None  # Для некоторых бирж (OKX, KuCoin)
    sandbox: bool = False
    timeout: int = 30


@dataclass
class ExchangeConfig:
    """Конфигурация биржи"""

    exchange_type: ExchangeType
    credentials: ExchangeCredentials
    settings: Optional[Dict[str, Any]] = None


class ExchangeFactory:
    """
    Фабрика для создания клиентов бирж

    Обеспечивает:
    - Унифицированное создание клиентов всех поддерживаемых бирж
    - Автоматическую валидацию параметров
    - Кеширование экземпляров
    - Graceful error handling
    """

    # Реестр классов клиентов
    _exchange_classes: Dict[ExchangeType, Type[BaseExchangeInterface]] = {}

    # Кеш экземпляров
    _client_cache: Dict[str, BaseExchangeInterface] = {}

    def __init__(self):
        # Логирование
        self.logger = setup_logger("exchange_factory")

        # Регистрируем доступные биржи
        self._register_exchanges()

    def _register_exchanges(self):
        """Регистрация всех доступных бирж"""
        try:
            # Bybit
            from .bybit import BybitExchange

            ExchangeFactory._exchange_classes[ExchangeType.BYBIT] = BybitExchange
            self.logger.info("Registered Bybit exchange")

        except ImportError as e:
            self.logger.warning(f"Failed to register Bybit: {e}")

        try:
            # Binance (будет добавлен позже)
            # from .binance.client import BinanceClient
            # ExchangeFactory._exchange_classes[ExchangeType.BINANCE] = BinanceClient
            self.logger.debug("Binance not yet implemented")

        except ImportError as e:
            self.logger.debug(f"Binance not available: {e}")

        # Аналогично для других бирж...

        self.logger.info(
            f"Exchange factory initialized with {len(ExchangeFactory._exchange_classes)} exchanges"
        )

    def create_client(
        self,
        exchange_type: Union[str, ExchangeType],
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        sandbox: bool = False,
        timeout: int = 30,
        cache_key: Optional[str] = None,
        force_new: bool = False,
        **kwargs,
    ) -> BaseExchangeInterface:
        """
        Создание клиента биржи

        Args:
            exchange_type: Тип биржи (строка или enum)
            api_key: API ключ
            api_secret: Секретный ключ
            passphrase: Пароль (для некоторых бирж)
            sandbox: Использовать песочницу
            timeout: Таймаут соединения
            cache_key: Ключ для кеширования (опционально)
            force_new: Принудительно создать новый экземпляр
            **kwargs: Дополнительные параметры для клиента

        Returns:
            Экземпляр клиента биржи

        Raises:
            ExchangeError: При ошибке создания клиента
        """
        try:
            # Преобразуем строку в enum
            if isinstance(exchange_type, str):
                exchange_type = ExchangeType(exchange_type.lower())

            # Проверяем поддержку биржи
            if exchange_type not in ExchangeFactory._exchange_classes:
                available = [e.value for e in ExchangeFactory._exchange_classes.keys()]
                raise ExchangeError(
                    exchange_type.value,
                    f"Exchange {exchange_type.value} not supported. Available: {available}",
                )

            # Создаем ключ кеша
            if not cache_key:
                cache_key = f"{exchange_type.value}_{api_key[:8]}_{sandbox}"

            # Проверяем кеш
            if not force_new and cache_key in self._client_cache:
                self.logger.debug(f"Returning cached client for {exchange_type.value}")
                return self._client_cache[cache_key]

            # Валидируем учетные данные
            self._validate_credentials(api_key, api_secret, exchange_type)

            # Получаем класс клиента
            client_class = ExchangeFactory._exchange_classes[exchange_type]

            # Создаем экземпляр
            client = client_class(
                api_key=api_key,
                api_secret=api_secret,
                sandbox=sandbox,
                timeout=timeout,
                **kwargs,
            )

            # Кешируем экземпляр
            self._client_cache[cache_key] = client

            self.logger.info(
                f"Created {exchange_type.value} client (sandbox={sandbox})"
            )
            return client

        except Exception as e:
            error_msg = f"Failed to create {exchange_type} client: {e}"
            self.logger.error(error_msg)
            raise ExchangeError(str(exchange_type), error_msg)

    def create_exchange(
        self, exchange_type: Union[str, ExchangeType], **kwargs
    ) -> BaseExchangeInterface:
        """
        Создание клиента биржи (алиас для create_client для совместимости)

        Args:
            exchange_type: Тип биржи
            **kwargs: Дополнительные параметры

        Returns:
            Клиент биржи
        """
        return self.create_client(exchange_type, **kwargs)

    def create_from_config(
        self,
        config: ExchangeConfig,
        cache_key: Optional[str] = None,
        force_new: bool = False,
    ) -> BaseExchangeInterface:
        """
        Создание клиента из конфигурации

        Args:
            config: Конфигурация биржи
            cache_key: Ключ кеша
            force_new: Принудительно создать новый экземпляр

        Returns:
            Экземпляр клиента биржи
        """
        creds = config.credentials
        settings = config.settings or {}

        return self.create_client(
            exchange_type=config.exchange_type,
            api_key=creds.api_key,
            api_secret=creds.api_secret,
            passphrase=creds.passphrase,
            sandbox=creds.sandbox,
            timeout=creds.timeout,
            cache_key=cache_key,
            force_new=force_new,
            **settings,
        )

    async def create_and_connect(self, *args, **kwargs) -> BaseExchangeInterface:
        """
        Создание клиента с автоматическим подключением

        Args:
            *args, **kwargs: Параметры для create_client

        Returns:
            Подключенный экземпляр клиента
        """
        client = self.create_client(*args, **kwargs)

        try:
            connected = await client.connect()
            if not connected:
                raise ExchangeError(client.name, "Failed to establish connection")

            self.logger.info(f"Successfully connected to {client.name}")
            return client

        except Exception as e:
            self.logger.error(f"Failed to connect client: {e}")
            raise ExchangeError(client.name, f"Connection failed: {e}")

    def get_supported_exchanges(self) -> List[str]:
        """Получение списка поддерживаемых бирж"""
        return [exchange.value for exchange in ExchangeFactory._exchange_classes.keys()]

    def is_exchange_supported(self, exchange_type: Union[str, ExchangeType]) -> bool:
        """Проверка поддержки биржи"""
        try:
            if isinstance(exchange_type, str):
                exchange_type = ExchangeType(exchange_type.lower())
            return exchange_type in ExchangeFactory._exchange_classes
        except (ValueError, AttributeError):
            return False

    def clear_cache(self, exchange_type: Optional[Union[str, ExchangeType]] = None):
        """
        Очистка кеша клиентов

        Args:
            exchange_type: Тип биржи для очистки (или None для всех)
        """
        if exchange_type is None:
            # Очищаем весь кеш
            count = len(self._client_cache)
            self._client_cache.clear()
            self.logger.info(f"Cleared {count} clients from cache")
        else:
            # Очищаем только указанную биржу
            if isinstance(exchange_type, str):
                exchange_type = exchange_type.lower()

            keys_to_remove = [
                key
                for key in self._client_cache.keys()
                if key.startswith(f"{exchange_type}_")
            ]

            for key in keys_to_remove:
                del self._client_cache[key]

    @staticmethod
    async def create_exchange_client(exchange_name: str) -> Optional[Any]:
        """Статический метод для создания клиента биржи"""
        import os

        factory = get_exchange_factory()
        exchange_name = exchange_name.lower()

        try:
            if exchange_name == "bybit":
                # Получаем креденшалы из переменных окружения
                api_key = os.getenv("BYBIT_API_KEY")
                api_secret = os.getenv("BYBIT_API_SECRET")
                testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

                if not api_key or not api_secret:
                    factory.logger.error(
                        "Bybit credentials not available in environment"
                    )
                    return None

                client = factory.create_client(
                    ExchangeType.BYBIT,
                    api_key=api_key,
                    api_secret=api_secret,
                    sandbox=testnet,
                )

                # Тестируем подключение
                try:
                    # Проверяем авторизацию
                    await client.get_account_info()
                    factory.logger.info("✅ Bybit client authenticated successfully")
                    return client
                except Exception as e:
                    factory.logger.error(f"❌ Bybit authentication failed: {e}")
                    await client.close()
                    return None

            else:
                factory.logger.error(f"Unknown exchange: {exchange_name}")
                return None

        except Exception as e:
            factory.logger.error(f"Failed to create {exchange_name} client: {e}")
            return None

    async def disconnect_all(self):
        """Отключение всех кешированных клиентов"""
        disconnect_tasks = []

        for client in self._client_cache.values():
            if hasattr(client, "disconnect"):
                disconnect_tasks.append(client.disconnect())

        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            self.logger.info(f"Disconnected {len(disconnect_tasks)} clients")

        self.clear_cache()

    def _validate_credentials(
        self, api_key: str, api_secret: str, exchange_type: ExchangeType
    ):
        """Валидация учетных данных"""
        # Разрешаем публичный доступ для загрузки рыночных данных
        if api_key == "public_access" and api_secret == "public_access":
            self.logger.info(f"Using public access for {exchange_type.value}")
            return

        if not api_key or not api_secret:
            raise AuthenticationError(
                exchange_type.value, "API key and secret are required"
            )

        # Дополнительная валидация для конкретных бирж
        if exchange_type == ExchangeType.BYBIT:
            # Логируем для отладки
            self.logger.debug(
                f"Validating Bybit credentials: key_len={len(api_key)}, secret_len={len(api_secret)}"
            )

            # Проверяем минимальную длину (Bybit ключи обычно 18+ символов)
            if len(api_key) < 10 or len(api_secret) < 10:
                raise AuthenticationError(
                    "bybit",
                    f"Invalid Bybit API credentials format: key_len={len(api_key)}, secret_len={len(api_secret)}",
                )

    def get_client_info(self) -> Dict[str, Any]:
        """Получение информации о клиентах в кеше"""
        info = {
            "total_clients": len(self._client_cache),
            "supported_exchanges": self.get_supported_exchanges(),
            "cached_clients": {},
        }

        for key, client in self._client_cache.items():
            info["cached_clients"][key] = {
                "exchange": client.name,
                "connected": getattr(client, "_connected", False),
            }

        return info


# Глобальный экземпляр фабрики
_global_factory: Optional[ExchangeFactory] = None


def get_exchange_factory() -> ExchangeFactory:
    """Получение глобального экземпляра фабрики"""
    global _global_factory
    if _global_factory is None:
        _global_factory = ExchangeFactory()
    return _global_factory


# Convenience функции
def create_bybit_client(
    api_key: str, api_secret: str, sandbox: bool = False, **kwargs
) -> BaseExchangeInterface:
    """Быстрое создание Bybit клиента"""
    factory = get_exchange_factory()
    return factory.create_client(
        ExchangeType.BYBIT, api_key, api_secret, sandbox=sandbox, **kwargs
    )


def create_binance_client(
    api_key: str, api_secret: str, sandbox: bool = False, **kwargs
) -> BaseExchangeInterface:
    """Быстрое создание Binance клиента (будет реализовано)"""
    factory = get_exchange_factory()
    return factory.create_client(
        ExchangeType.BINANCE, api_key, api_secret, sandbox=sandbox, **kwargs
    )


# Глобальный экземпляр фабрики
exchange_factory = get_exchange_factory()

# Экспорт
__all__ = [
    "ExchangeFactory",
    "ExchangeType",
    "ExchangeCredentials",
    "ExchangeConfig",
    "get_exchange_factory",
    "exchange_factory",
    "create_bybit_client",
    "create_binance_client",
]
