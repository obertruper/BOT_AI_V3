"""Модуль TraderFactory для создания экземпляров трейдеров.

Использует паттерн "Фабрика" для инкапсуляции логики создания и
конфигурирования трейдеров с различными стратегиями и подключениями к биржам.
"""

import logging
from dataclasses import dataclass
from typing import Any

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
    """Датакласс для хранения всех компонентов, необходимых трейдеру."""

    exchange_client: Any = None
    strategy: Any = None
    database_repository: Any = None
    ml_model: Any = None
    risk_manager: Any = None
    indicator_engine: Any = None


class TraderFactory:
    """Фабрика для создания и полной инициализации экземпляров трейдеров.

    Автоматически создает и внедряет все необходимые зависимости для трейдера,
    такие как клиент биржи, стратегия, риск-менеджер и т.д., на основе
    его конфигурации.
    """

    def __init__(self, config_manager: ConfigManager):
        """Инициализирует фабрику.

        Args:
            config_manager: Менеджер конфигурации для доступа к настройкам.
        """
        self.config_manager = config_manager
        self.validator = ConfigValidator()
        self.logger = logging.getLogger(__name__)
        self.trader_types: dict[str, type | None] = {}  # Инициализация trader_types
        self._exchange_registry: dict[str, type] = {}
        self._strategy_registry: dict[str, type] = {}
        self._risk_manager_registry: dict[str, type] = {}
        self._register_default_components()

    async def create_trader(self, trader_id: str) -> TraderContext:
        """Создает, валидирует и полностью инициализирует трейдера со всеми зависимостями.

        Args:
            trader_id: Уникальный идентификатор трейдера.

        Returns:
            Готовый к работе экземпляр TraderContext.

        Raises:
            TraderFactoryError: Если не удалось создать трейдера.
        """
        try:
            self.logger.info(f"Создание трейдера {trader_id}...")
            trader_context = TraderContext(trader_id, self.config_manager)
            await trader_context.initialize()
            await self._validate_trader_config(trader_context)
            components = await self._create_components(trader_context)
            await self._inject_dependencies(trader_context, components)
            self.logger.info(f"Трейдер {trader_id} успешно создан")
            return trader_context
        except Exception as e:
            error_msg = f"Ошибка создания трейдера {trader_id}: {e}"
            self.logger.error(error_msg)
            raise TraderFactoryError(error_msg) from e

    def _validate_trader_config(self, config: dict) -> None:
        """Валидация конфигурации трейдера."""
        required_fields = ['id', 'type', 'exchange', 'strategy']
        
        for field in required_fields:
            if field not in config:
                raise ConfigurationError(f"Отсутствует обязательное поле '{field}' в конфигурации трейдера")
    
    def _create_trader_instance(self, config: dict):
        """Создает экземпляр трейдера на основе типа."""
        trader_type = config.get('type', 'basic')
        
        # Здесь можно добавить различные типы трейдеров
        if trader_type == 'multi_crypto':
            from trading.traders.multi_crypto_trader import MultiCryptoTrader
            return MultiCryptoTrader(config)
        else:
            # Базовый трейдер по умолчанию
            from trading.traders.base_trader import BaseTrader
            return BaseTrader(config)
    
    def register_trader_type(self, trader_type: str, trader_class):
        """Регистрирует новый тип трейдера."""
        self.trader_types[trader_type] = trader_class
        self.logger.info(f"Зарегистрирован новый тип трейдера: {trader_type}")
    
    def get_registered_types(self) -> list[str]:
        """Возвращает список зарегистрированных типов трейдеров."""
        return list(self.trader_types.keys())
    
    def _register_default_components(self) -> None:
        """Регистрирует компоненты по умолчанию."""
        try:
            # Регистрируем основные типы трейдеров
            self.trader_types.update({
                "base": None,  # Базовый трейдер
                "crypto": None,  # Криптовалютный трейдер
                "scalping": None,  # Скальпинговый трейдер
            })
            
            self.logger.info(f"✅ Зарегистрировано {len(self.trader_types)} типов трейдеров по умолчанию")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка регистрации компонентов по умолчанию: {e}")
            # Не критическая ошибка, продолжаем работу


# Глобальная переменная для singleton instance
_global_trader_factory: TraderFactory | None = None


def get_global_trader_factory() -> TraderFactory:
    """Получает глобальный экземпляр TraderFactory (singleton)"""
    global _global_trader_factory
    if _global_trader_factory is None:
        from core.config.config_manager import get_global_config_manager
        config_manager = get_global_config_manager()
        _global_trader_factory = TraderFactory(config_manager)
    return _global_trader_factory
