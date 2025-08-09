"""
Exchange Registry для BOT_Trading v3.0

Централизованный реестр всех доступных бирж с метаданными,
возможностями и конфигурацией по умолчанию.

Обеспечивает:
- Информацию о всех поддерживаемых биржах
- Метаданные возможностей каждой биржи
- Валидацию доступности бирж
- Настройки по умолчанию
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from core.logging.logger_factory import get_global_logger_factory

from .base.exchange_interface import ExchangeCapabilities
from .factory import ExchangeType


class ExchangeStatus(Enum):
    """Статус биржи в системе"""

    ACTIVE = "active"  # Полностью поддерживается
    BETA = "beta"  # В бета тестировании
    DEPRECATED = "deprecated"  # Устаревшая, будет удалена
    MAINTENANCE = "maintenance"  # На техническом обслуживании
    DISABLED = "disabled"  # Отключена


@dataclass
class ExchangeMetadata:
    """Метаданные биржи"""

    name: str
    display_name: str
    exchange_type: ExchangeType
    status: ExchangeStatus
    version: str
    description: str
    website: str
    api_docs: str

    # Технические характеристики
    capabilities: ExchangeCapabilities
    default_timeout: int = 30
    rate_limits: Dict[str, int] = field(default_factory=dict)

    # Поддерживаемые регионы
    supported_regions: List[str] = field(default_factory=list)
    restricted_regions: List[str] = field(default_factory=list)

    # Дополнительные настройки
    sandbox_available: bool = True
    requires_passphrase: bool = False
    supports_websocket: bool = True

    # Дата добавления и обновления
    added_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None


class ExchangeRegistry:
    """
    Реестр всех поддерживаемых бирж

    Централизованное хранилище информации о биржах,
    их возможностях и настройках.
    """

    def __init__(self):
        # Логирование
        logger_factory = get_global_logger_factory()
        self.logger = logger_factory.get_logger("exchange_registry")

        # Реестр бирж
        self._exchanges: Dict[ExchangeType, ExchangeMetadata] = {}

        # Инициализация
        self._initialize_exchanges()

    def _initialize_exchanges(self):
        """Инициализация всех поддерживаемых бирж"""

        # Bybit
        bybit_capabilities = ExchangeCapabilities(
            spot_trading=True,
            futures_trading=True,
            margin_trading=True,
            market_orders=True,
            limit_orders=True,
            stop_orders=True,
            stop_limit_orders=True,
            websocket_public=True,
            websocket_private=True,
            position_management=True,
            leverage_trading=True,
            max_leverage=100.0,
            min_order_size=0.001,
            max_order_size=1000000.0,
            rate_limit_public=120,
            rate_limit_private=120,
        )

        self._exchanges[ExchangeType.BYBIT] = ExchangeMetadata(
            name="bybit",
            display_name="Bybit",
            exchange_type=ExchangeType.BYBIT,
            status=ExchangeStatus.ACTIVE,
            version="5.0",
            description="Leading cryptocurrency derivatives exchange",
            website="https://www.bybit.com",
            api_docs="https://bybit-exchange.github.io/docs/v5/intro",
            capabilities=bybit_capabilities,
            default_timeout=30,
            rate_limits={
                "public": 120,
                "private": 120,
                "order": 100,
            },  # requests per minute
            supported_regions=["global"],
            restricted_regions=["US"],
            sandbox_available=True,
            requires_passphrase=False,
            supports_websocket=True,
            added_date=datetime(2024, 1, 1),
            updated_date=datetime.now(),
        )

        # Binance (планируется)
        binance_capabilities = ExchangeCapabilities(
            spot_trading=True,
            futures_trading=True,
            margin_trading=True,
            market_orders=True,
            limit_orders=True,
            stop_orders=True,
            stop_limit_orders=True,
            websocket_public=True,
            websocket_private=True,
            position_management=True,
            leverage_trading=True,
            max_leverage=125.0,
            min_order_size=0.00001,
            max_order_size=9000000.0,
            rate_limit_public=1200,
            rate_limit_private=1200,
        )

        self._exchanges[ExchangeType.BINANCE] = ExchangeMetadata(
            name="binance",
            display_name="Binance",
            exchange_type=ExchangeType.BINANCE,
            status=ExchangeStatus.BETA,  # Планируется
            version="3.0",
            description="World's largest cryptocurrency exchange",
            website="https://www.binance.com",
            api_docs="https://binance-docs.github.io/apidocs/futures/en/",
            capabilities=binance_capabilities,
            default_timeout=30,
            rate_limits={"public": 1200, "private": 1200, "order": 50},
            supported_regions=["global"],
            restricted_regions=["US"],
            sandbox_available=True,
            requires_passphrase=False,
            supports_websocket=True,
            added_date=datetime(2024, 2, 1),
            updated_date=datetime.now(),
        )

        # OKX (планируется)
        okx_capabilities = ExchangeCapabilities(
            spot_trading=True,
            futures_trading=True,
            margin_trading=True,
            market_orders=True,
            limit_orders=True,
            stop_orders=True,
            stop_limit_orders=True,
            websocket_public=True,
            websocket_private=True,
            position_management=True,
            leverage_trading=True,
            max_leverage=100.0,
            min_order_size=0.001,
            max_order_size=1000000.0,
            rate_limit_public=600,
            rate_limit_private=600,
        )

        self._exchanges[ExchangeType.OKX] = ExchangeMetadata(
            name="okx",
            display_name="OKX",
            exchange_type=ExchangeType.OKX,
            status=ExchangeStatus.BETA,  # Планируется
            version="5.0",
            description="Global crypto exchange and Web3 ecosystem",
            website="https://www.okx.com",
            api_docs="https://www.okx.com/docs-v5/en/",
            capabilities=okx_capabilities,
            default_timeout=30,
            rate_limits={"public": 600, "private": 600, "order": 60},
            supported_regions=["global"],
            restricted_regions=["US"],
            sandbox_available=True,
            requires_passphrase=True,  # OKX требует passphrase
            supports_websocket=True,
            added_date=datetime(2024, 3, 1),
            updated_date=datetime.now(),
        )

        self.logger.info(
            f"Initialized exchange registry with {len(self._exchanges)} exchanges"
        )

    def get_exchange(self, exchange_type: ExchangeType) -> Optional[ExchangeMetadata]:
        """Получение метаданных биржи"""
        return self._exchanges.get(exchange_type)

    def get_all_exchanges(self) -> Dict[ExchangeType, ExchangeMetadata]:
        """Получение всех бирж"""
        return self._exchanges.copy()

    def get_active_exchanges(self) -> Dict[ExchangeType, ExchangeMetadata]:
        """Получение только активных бирж"""
        return {
            exchange_type: metadata
            for exchange_type, metadata in self._exchanges.items()
            if metadata.status == ExchangeStatus.ACTIVE
        }

    def get_exchanges_by_status(
        self, status: ExchangeStatus
    ) -> Dict[ExchangeType, ExchangeMetadata]:
        """Получение бирж по статусу"""
        return {
            exchange_type: metadata
            for exchange_type, metadata in self._exchanges.items()
            if metadata.status == status
        }

    def is_exchange_available(self, exchange_type: ExchangeType) -> bool:
        """Проверка доступности биржи"""
        metadata = self.get_exchange(exchange_type)
        if not metadata:
            return False

        return metadata.status in [ExchangeStatus.ACTIVE, ExchangeStatus.BETA]

    def get_exchange_capabilities(
        self, exchange_type: ExchangeType
    ) -> Optional[ExchangeCapabilities]:
        """Получение возможностей биржи"""
        metadata = self.get_exchange(exchange_type)
        return metadata.capabilities if metadata else None

    def supports_feature(self, exchange_type: ExchangeType, feature: str) -> bool:
        """Проверка поддержки функции биржей"""
        capabilities = self.get_exchange_capabilities(exchange_type)
        if not capabilities:
            return False

        return getattr(capabilities, feature, False)

    def get_rate_limits(self, exchange_type: ExchangeType) -> Dict[str, int]:
        """Получение лимитов запросов"""
        metadata = self.get_exchange(exchange_type)
        return metadata.rate_limits if metadata else {}

    def search_exchanges(self, **criteria) -> List[ExchangeMetadata]:
        """
        Поиск бирж по критериям

        Args:
            **criteria: Критерии поиска (status, spot_trading, futures_trading, etc.)
        """
        results = []

        for metadata in self._exchanges.values():
            match = True

            # Проверяем каждый критерий
            for key, value in criteria.items():
                if key == "status":
                    if metadata.status != value:
                        match = False
                        break
                elif hasattr(metadata.capabilities, key):
                    if getattr(metadata.capabilities, key) != value:
                        match = False
                        break
                elif hasattr(metadata, key):
                    if getattr(metadata, key) != value:
                        match = False
                        break

            if match:
                results.append(metadata)

        return results

    async def initialize(self):
        """Инициализация реестра бирж"""
        self.logger.info("Exchange Registry инициализирован")
        return True

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return True

    def get_exchange_summary(self) -> Dict[str, Any]:
        """Получение сводки по биржам"""
        status_counts = {}
        for status in ExchangeStatus:
            status_counts[status.value] = len(self.get_exchanges_by_status(status))

        features = {
            "spot_trading": 0,
            "futures_trading": 0,
            "margin_trading": 0,
            "websocket_support": 0,
            "leverage_trading": 0,
        }

        for metadata in self._exchanges.values():
            if metadata.capabilities.spot_trading:
                features["spot_trading"] += 1
            if metadata.capabilities.futures_trading:
                features["futures_trading"] += 1
            if metadata.capabilities.margin_trading:
                features["margin_trading"] += 1
            if metadata.supports_websocket:
                features["websocket_support"] += 1
            if metadata.capabilities.leverage_trading:
                features["leverage_trading"] += 1

        return {
            "total_exchanges": len(self._exchanges),
            "status_breakdown": status_counts,
            "feature_support": features,
            "supported_exchanges": [e.value for e in self._exchanges.keys()],
        }

    def validate_exchange_config(
        self, exchange_type: ExchangeType, config: Dict[str, Any]
    ) -> List[str]:
        """
        Валидация конфигурации биржи

        Returns:
            Список ошибок валидации (пустой если все OK)
        """
        errors = []
        metadata = self.get_exchange(exchange_type)

        if not metadata:
            errors.append(f"Exchange {exchange_type.value} not found in registry")
            return errors

        # Проверяем статус
        if metadata.status not in [ExchangeStatus.ACTIVE, ExchangeStatus.BETA]:
            errors.append(f"Exchange {exchange_type.value} is {metadata.status.value}")

        # Проверяем обязательные поля
        required_fields = ["api_key", "api_secret"]
        if metadata.requires_passphrase:
            required_fields.append("passphrase")

        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"Missing required field: {field}")

        # Проверяем таймаут
        timeout = config.get("timeout", metadata.default_timeout)
        if not isinstance(timeout, int) or timeout <= 0:
            errors.append("Invalid timeout value")

        return errors


# Глобальный экземпляр реестра
_global_registry: Optional[ExchangeRegistry] = None


def get_exchange_registry() -> ExchangeRegistry:
    """Получение глобального экземпляра реестра"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ExchangeRegistry()
    return _global_registry


# Convenience функции
def get_supported_exchanges() -> List[str]:
    """Получение списка поддерживаемых бирж"""
    registry = get_exchange_registry()
    return [e.name for e in registry.get_active_exchanges().values()]


def is_exchange_supported(exchange_name: str) -> bool:
    """Проверка поддержки биржи"""
    try:
        exchange_type = ExchangeType(exchange_name.lower())
        registry = get_exchange_registry()
        return registry.is_exchange_available(exchange_type)
    except ValueError:
        return False


def get_exchange_info(exchange_name: str) -> Optional[Dict[str, Any]]:
    """Получение информации о бирже"""
    try:
        exchange_type = ExchangeType(exchange_name.lower())
        registry = get_exchange_registry()
        metadata = registry.get_exchange(exchange_type)

        if not metadata:
            return None

        return {
            "name": metadata.name,
            "display_name": metadata.display_name,
            "status": metadata.status.value,
            "version": metadata.version,
            "description": metadata.description,
            "website": metadata.website,
            "api_docs": metadata.api_docs,
            "sandbox_available": metadata.sandbox_available,
            "requires_passphrase": metadata.requires_passphrase,
            "supports_websocket": metadata.supports_websocket,
            "capabilities": {
                "spot_trading": metadata.capabilities.spot_trading,
                "futures_trading": metadata.capabilities.futures_trading,
                "margin_trading": metadata.capabilities.margin_trading,
                "max_leverage": metadata.capabilities.max_leverage,
                "rate_limits": metadata.rate_limits,
            },
        }

    except ValueError:
        return None


# Экспорт
__all__ = [
    "ExchangeRegistry",
    "ExchangeMetadata",
    "ExchangeStatus",
    "get_exchange_registry",
    "get_supported_exchanges",
    "is_exchange_supported",
    "get_exchange_info",
]
