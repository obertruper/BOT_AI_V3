"""
Trader Factory для BOT_Trading v3.0

Фабрика для создания и инициализации трейдеров с поддержкой:
- Различных бирж (Bybit, Binance, OKX и др.)
- Множественных стратегий
- Автоматической настройки компонентов
- Валидации конфигураций
- Dependency injection
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from core.config.config_manager import ConfigManager
from core.config.validation import ConfigValidator, ValidationLevel
from core.exceptions import (
    TraderFactoryError,
    TraderInitializationError,
    UnsupportedExchangeError,
    UnsupportedStrategyError,
)
from core.traders.trader_context import TraderContext


@dataclass
class TraderComponents:
    """Компоненты трейдера"""

    exchange_client: Any = None
    strategy: Any = None
    database_repository: Any = None
    ml_model: Any = None
    risk_manager: Any = None
    indicator_engine: Any = None


class TraderFactory:
    """
    Фабрика для создания трейдеров BOT_Trading v3.0

    Поддерживает:
    - Создание трейдеров для различных бирж
    - Автоматическое внедрение зависимостей
    - Валидацию конфигураций
    - Регистрацию пользовательских компонентов
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.validator = ConfigValidator()
        self.logger = logging.getLogger(__name__)

        # Реестры компонентов
        self._exchange_registry: Dict[str, Type] = {}
        self._strategy_registry: Dict[str, Type] = {}
        self._risk_manager_registry: Dict[str, Type] = {}

        # Инициализация стандартных компонентов
        self._register_default_components()

    def _register_default_components(self) -> None:
        """Регистрация стандартных компонентов системы"""
        # Регистрация бирж
        self._register_exchanges()

        # Регистрация стратегий
        self._register_strategies()

        # Регистрация риск-менеджеров
        self._register_risk_managers()

    def _register_exchanges(self) -> None:
        """Регистрация поддерживаемых бирж"""
        # Ленивая загрузка для избежания циклических импортов
        try:
            from exchanges.bybit.bybit_client import BybitClient

            self._exchange_registry["bybit"] = BybitClient
        except ImportError:
            self.logger.warning("Bybit client недоступен")

        try:
            from exchanges.binance.binance_client import BinanceClient

            self._exchange_registry["binance"] = BinanceClient
        except ImportError:
            self.logger.warning("Binance client недоступен")

        try:
            from exchanges.okx.okx_client import OKXClient

            self._exchange_registry["okx"] = OKXClient
        except ImportError:
            self.logger.warning("OKX client недоступен")

        try:
            from exchanges.bitget.bitget_client import BitgetClient

            self._exchange_registry["bitget"] = BitgetClient
        except ImportError:
            self.logger.warning("Bitget client недоступен")

        try:
            from exchanges.gateio.gateio_client import GateIOClient

            self._exchange_registry["gateio"] = GateIOClient
        except ImportError:
            self.logger.warning("Gate.io client недоступен")

        try:
            from exchanges.kucoin.kucoin_client import KucoinClient

            self._exchange_registry["kucoin"] = KucoinClient
        except ImportError:
            self.logger.warning("Kucoin client недоступен")

        try:
            from exchanges.huobi.huobi_client import HuobiClient

            self._exchange_registry["huobi"] = HuobiClient
        except ImportError:
            self.logger.warning("Huobi client недоступен")

    def _register_strategies(self) -> None:
        """Регистрация стратегий"""
        try:
            from strategies.ml_strategy import MLStrategy

            self._strategy_registry["ml_strategy"] = MLStrategy
        except ImportError:
            self.logger.warning("ML Strategy недоступна")

        try:
            from strategies.indicator_strategy import IndicatorStrategy

            self._strategy_registry["indicator_strategy"] = IndicatorStrategy
        except ImportError:
            self.logger.warning("Indicator Strategy недоступна")

        try:
            from strategies.arbitrage_strategy import ArbitrageStrategy

            self._strategy_registry["arbitrage_strategy"] = ArbitrageStrategy
        except ImportError:
            self.logger.warning("Arbitrage Strategy недоступна")

        try:
            from strategies.scalping_strategy import ScalpingStrategy

            self._strategy_registry["scalping_strategy"] = ScalpingStrategy
        except ImportError:
            self.logger.warning("Scalping Strategy недоступна")

        try:
            from strategies.grid_strategy import GridStrategy

            self._strategy_registry["grid_strategy"] = GridStrategy
        except ImportError:
            self.logger.warning("Grid Strategy недоступна")

    def _register_risk_managers(self) -> None:
        """Регистрация риск-менеджеров"""
        try:
            from risk.basic_risk_manager import BasicRiskManager

            self._risk_manager_registry["basic"] = BasicRiskManager
        except ImportError:
            self.logger.warning("Basic Risk Manager недоступен")

        try:
            from risk.advanced_risk_manager import AdvancedRiskManager

            self._risk_manager_registry["advanced"] = AdvancedRiskManager
        except ImportError:
            self.logger.warning("Advanced Risk Manager недоступен")

        try:
            from risk.ml_risk_manager import MLRiskManager

            self._risk_manager_registry["ml"] = MLRiskManager
        except ImportError:
            self.logger.warning("ML Risk Manager недоступен")

    async def create_trader(self, trader_id: str) -> TraderContext:
        """
        Создание трейдера с полной инициализацией

        Args:
            trader_id: Идентификатор трейдера

        Returns:
            Инициализированный TraderContext

        Raises:
            TraderFactoryError: Ошибка создания трейдера
        """
        try:
            self.logger.info(f"Создание трейдера {trader_id}...")

            # Создание контекста трейдера
            trader_context = TraderContext(trader_id, self.config_manager)
            await trader_context.initialize()

            # Валидация конфигурации
            await self._validate_trader_config(trader_context)

            # Создание и настройка компонентов
            components = await self._create_components(trader_context)

            # Внедрение зависимостей
            await self._inject_dependencies(trader_context, components)

            self.logger.info(f"Трейдер {trader_id} успешно создан")
            return trader_context

        except Exception as e:
            error_msg = f"Ошибка создания трейдера {trader_id}: {e}"
            self.logger.error(error_msg)
            raise TraderFactoryError(error_msg) from e

    async def _validate_trader_config(self, trader_context: TraderContext) -> None:
        """Валидация конфигурации трейдера"""
        trader_config = trader_context.get_trader_config()
        validation_results = self.validator.validate_trader_config(
            trader_context.trader_id, trader_config
        )

        # Проверка критических ошибок
        errors = [r for r in validation_results if r.level == ValidationLevel.ERROR]
        if errors:
            error_messages = [f"{r.field}: {r.message}" for r in errors]
            raise TraderInitializationError(
                f"Критические ошибки конфигурации трейдера {trader_context.trader_id}: {'; '.join(error_messages)}"
            )

        # Логирование предупреждений
        warnings = [r for r in validation_results if r.level == ValidationLevel.WARNING]
        for warning in warnings:
            trader_context.logger.warning(
                f"Предупреждение конфигурации {warning.field}: {warning.message}"
            )

    async def _create_components(
        self, trader_context: TraderContext
    ) -> TraderComponents:
        """Создание компонентов трейдера"""
        components = TraderComponents()

        # Создание клиента биржи
        components.exchange_client = await self._create_exchange_client(trader_context)

        # Создание стратегии
        components.strategy = await self._create_strategy(trader_context)

        # Создание репозитория БД
        components.database_repository = await self._create_database_repository(
            trader_context
        )

        # Создание ML модели (опционально)
        components.ml_model = await self._create_ml_model(trader_context)

        # Создание риск-менеджера
        components.risk_manager = await self._create_risk_manager(trader_context)

        # Создание движка индикаторов
        components.indicator_engine = await self._create_indicator_engine(
            trader_context
        )

        return components

    async def _create_exchange_client(self, trader_context: TraderContext):
        """Создание клиента биржи"""
        exchange_name = trader_context.get_exchange_name()

        if exchange_name not in self._exchange_registry:
            available_exchanges = list(self._exchange_registry.keys())
            raise UnsupportedExchangeError(
                f"Биржа '{exchange_name}' не поддерживается. "
                f"Доступные биржи: {', '.join(available_exchanges)}"
            )

        exchange_class = self._exchange_registry[exchange_name]
        exchange_config = trader_context.get_trader_config("exchange_config", {})

        # Создание экземпляра клиента биржи
        exchange_client = exchange_class(
            api_key=exchange_config.get("api_key"),
            api_secret=exchange_config.get("api_secret"),
            testnet=exchange_config.get("testnet", False),
            market_type=trader_context.get_market_type(),
        )

        # Инициализация соединения
        await exchange_client.initialize()

        trader_context.logger.info(f"Создан клиент биржи {exchange_name}")
        return exchange_client

    async def _create_strategy(self, trader_context: TraderContext):
        """Создание стратегии"""
        strategy_name = trader_context.get_strategy_name()

        if strategy_name not in self._strategy_registry:
            available_strategies = list(self._strategy_registry.keys())
            raise UnsupportedStrategyError(
                f"Стратегия '{strategy_name}' не поддерживается. "
                f"Доступные стратегии: {', '.join(available_strategies)}"
            )

        strategy_class = self._strategy_registry[strategy_name]
        strategy_config = trader_context.get_trader_config("strategy_config", {})

        # Создание экземпляра стратегии
        strategy = strategy_class(config=strategy_config, trader_context=trader_context)

        await strategy.initialize()

        trader_context.logger.info(f"Создана стратегия {strategy_name}")
        return strategy

    async def _create_database_repository(self, trader_context: TraderContext):
        """Создание репозитория базы данных"""
        try:
            from db.repositories.factory import RepositoryFactory

            # Создание фабрики репозиториев
            repository_factory = RepositoryFactory(
                db_config=self.config_manager.get_database_config(),
                trader_id=trader_context.trader_id,
            )

            # Инициализация соединения
            await repository_factory.initialize()

            trader_context.logger.info("Создан репозиторий базы данных")
            return repository_factory

        except ImportError as e:
            trader_context.logger.warning(f"Репозиторий БД недоступен: {e}")
            return None

    async def _create_ml_model(self, trader_context: TraderContext):
        """Создание ML модели"""
        strategy_name = trader_context.get_strategy_name()

        # ML модель нужна только для ML стратегии
        if strategy_name != "ml_strategy":
            return None

        try:
            from ml.predictor import ModelPredictor

            # Создание предиктора ML
            ml_config = trader_context.get_trader_config("ml_config", {})
            predictor = ModelPredictor(
                config=ml_config, trader_id=trader_context.trader_id
            )

            await predictor.initialize()

            trader_context.logger.info("Создана ML модель")
            return predictor

        except ImportError as e:
            trader_context.logger.warning(f"ML модель недоступна: {e}")
            return None

    async def _create_risk_manager(self, trader_context: TraderContext):
        """Создание риск-менеджера"""
        risk_config = trader_context.get_trader_config("risk_management", {})
        risk_type = risk_config.get("type", "basic")

        if risk_type not in self._risk_manager_registry:
            risk_type = "basic"  # Fallback к базовому

        risk_manager_class = self._risk_manager_registry.get(risk_type)
        if not risk_manager_class:
            trader_context.logger.warning("Риск-менеджер недоступен")
            return None

        # Создание экземпляра риск-менеджера
        risk_manager = risk_manager_class(
            config=risk_config, trader_context=trader_context
        )

        await risk_manager.initialize()

        trader_context.logger.info(f"Создан риск-менеджер {risk_type}")
        return risk_manager

    async def _create_indicator_engine(self, trader_context: TraderContext):
        """Создание движка индикаторов"""
        try:
            from indicators.indicator_engine import IndicatorEngine

            # Создание движка индикаторов
            indicator_config = trader_context.get_trader_config("indicators", {})
            indicator_engine = IndicatorEngine(
                config=indicator_config, trader_context=trader_context
            )

            await indicator_engine.initialize()

            trader_context.logger.info("Создан движок индикаторов")
            return indicator_engine

        except ImportError as e:
            trader_context.logger.warning(f"Движок индикаторов недоступен: {e}")
            return None

    async def _inject_dependencies(
        self, trader_context: TraderContext, components: TraderComponents
    ) -> None:
        """Внедрение зависимостей в контекст трейдера"""
        # Внедрение компонентов в контекст
        trader_context.exchange = components.exchange_client
        trader_context.strategy = components.strategy
        trader_context.database = components.database_repository
        trader_context.ml_model = components.ml_model
        trader_context.risk_manager = components.risk_manager

        # Настройка связей между компонентами
        if components.strategy:
            components.strategy.set_exchange_client(components.exchange_client)
            components.strategy.set_risk_manager(components.risk_manager)
            components.strategy.set_ml_model(components.ml_model)
            components.strategy.set_indicator_engine(components.indicator_engine)

        if components.risk_manager:
            components.risk_manager.set_exchange_client(components.exchange_client)

    def register_exchange(self, name: str, exchange_class: Type) -> None:
        """Регистрация пользовательского клиента биржи"""
        self._exchange_registry[name] = exchange_class
        self.logger.info(f"Зарегистрирована биржа: {name}")

    def register_strategy(self, name: str, strategy_class: Type) -> None:
        """Регистрация пользовательской стратегии"""
        self._strategy_registry[name] = strategy_class
        self.logger.info(f"Зарегистрирована стратегия: {name}")

    def register_risk_manager(self, name: str, risk_manager_class: Type) -> None:
        """Регистрация пользовательского риск-менеджера"""
        self._risk_manager_registry[name] = risk_manager_class
        self.logger.info(f"Зарегистрирован риск-менеджер: {name}")

    def get_supported_exchanges(self) -> List[str]:
        """Получение списка поддерживаемых бирж"""
        return list(self._exchange_registry.keys())

    def get_supported_strategies(self) -> List[str]:
        """Получение списка поддерживаемых стратегий"""
        return list(self._strategy_registry.keys())

    def get_supported_risk_managers(self) -> List[str]:
        """Получение списка поддерживаемых риск-менеджеров"""
        return list(self._risk_manager_registry.keys())

    async def validate_trader_creation(self, trader_id: str) -> List[str]:
        """
        Валидация возможности создания трейдера

        Args:
            trader_id: Идентификатор трейдера

        Returns:
            Список ошибок валидации (пустой если все OK)
        """
        errors = []

        # Проверка конфигурации трейдера
        trader_config = self.config_manager.get_trader_config(trader_id)
        if not trader_config:
            errors.append(f"Конфигурация трейдера {trader_id} не найдена")
            return errors

        # Проверка биржи
        exchange_name = trader_config.get("exchange")
        if not exchange_name:
            errors.append("Не указана биржа")
        elif exchange_name not in self._exchange_registry:
            errors.append(f"Биржа '{exchange_name}' не поддерживается")

        # Проверка стратегии
        strategy_name = trader_config.get("strategy")
        if not strategy_name:
            errors.append("Не указана стратегия")
        elif strategy_name not in self._strategy_registry:
            errors.append(f"Стратегия '{strategy_name}' не поддерживается")

        # Проверка API ключей
        exchange_config = trader_config.get("exchange_config", {})
        if not exchange_config.get("api_key"):
            errors.append("Не указан API ключ биржи")
        if not exchange_config.get("api_secret"):
            errors.append("Не указан API секрет биржи")

        return errors


# Глобальная фабрика для удобства использования
_global_trader_factory: Optional[TraderFactory] = None


def get_global_trader_factory() -> TraderFactory:
    """Получение глобального экземпляра TraderFactory"""
    global _global_trader_factory
    if _global_trader_factory is None:
        from core.config.config_manager import get_global_config_manager

        _global_trader_factory = TraderFactory(get_global_config_manager())
    return _global_trader_factory
