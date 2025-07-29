"""
Реестр торговых стратегий
Централизованное управление регистрацией и доступом к стратегиям
"""

import logging
from threading import RLock
from typing import Dict, List, Optional, Type

from .base import StrategyABC

logger = logging.getLogger(__name__)


class StrategyRegistryError(Exception):
    """Ошибка реестра стратегий"""

    pass


class StrategyRegistry:
    """
    Синглтон реестр для всех торговых стратегий
    Thread-safe регистрация и доступ к стратегиям
    """

    _instance = None
    _lock = RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._strategies: Dict[str, Type[StrategyABC]] = {}
        self._metadata: Dict[str, Dict[str, any]] = {}
        self._initialized = True
        logger.info("StrategyRegistry initialized")

    def register(
        self,
        name: str,
        strategy_class: Type[StrategyABC],
        metadata: Optional[Dict[str, any]] = None,
    ) -> None:
        """
        Регистрация стратегии в реестре

        Args:
            name: Уникальное имя стратегии
            strategy_class: Класс стратегии (должен наследоваться от StrategyABC)
            metadata: Дополнительные метаданные стратегии

        Raises:
            StrategyRegistryError: Если стратегия уже зарегистрирована или невалидна
        """
        with self._lock:
            # Валидация
            if not name:
                raise StrategyRegistryError("Strategy name cannot be empty")

            if name in self._strategies:
                raise StrategyRegistryError(f"Strategy '{name}' already registered")

            if not issubclass(strategy_class, StrategyABC):
                raise StrategyRegistryError(
                    f"Strategy class must inherit from StrategyABC, got {strategy_class}"
                )

            # Регистрация
            self._strategies[name] = strategy_class
            self._metadata[name] = metadata or {
                "description": strategy_class.__doc__ or "No description",
                "version": getattr(strategy_class, "__version__", "1.0.0"),
                "author": getattr(strategy_class, "__author__", "Unknown"),
                "tags": getattr(strategy_class, "__tags__", []),
            }

            logger.info(f"Registered strategy: {name} ({strategy_class.__name__})")

    def unregister(self, name: str) -> None:
        """
        Удаление стратегии из реестра

        Args:
            name: Имя стратегии для удаления

        Raises:
            StrategyRegistryError: Если стратегия не найдена
        """
        with self._lock:
            if name not in self._strategies:
                raise StrategyRegistryError(f"Strategy '{name}' not found")

            del self._strategies[name]
            del self._metadata[name]
            logger.info(f"Unregistered strategy: {name}")

    def get_strategy_class(self, name: str) -> Type[StrategyABC]:
        """
        Получение класса стратегии по имени

        Args:
            name: Имя стратегии

        Returns:
            Класс стратегии

        Raises:
            StrategyRegistryError: Если стратегия не найдена
        """
        with self._lock:
            if name not in self._strategies:
                raise StrategyRegistryError(
                    f"Strategy '{name}' not found. Available: {self.list_strategies()}"
                )

            return self._strategies[name]

    def get_metadata(self, name: str) -> Dict[str, any]:
        """
        Получение метаданных стратегии

        Args:
            name: Имя стратегии

        Returns:
            Метаданные стратегии
        """
        with self._lock:
            if name not in self._metadata:
                raise StrategyRegistryError(f"Strategy '{name}' not found")

            return self._metadata[name].copy()

    def list_strategies(self) -> List[str]:
        """
        Получение списка всех зарегистрированных стратегий

        Returns:
            Список имен стратегий
        """
        with self._lock:
            return list(self._strategies.keys())

    def get_all_metadata(self) -> Dict[str, Dict[str, any]]:
        """
        Получение метаданных всех стратегий

        Returns:
            Словарь с метаданными всех стратегий
        """
        with self._lock:
            return {name: metadata.copy() for name, metadata in self._metadata.items()}

    def is_registered(self, name: str) -> bool:
        """
        Проверка, зарегистрирована ли стратегия

        Args:
            name: Имя стратегии

        Returns:
            True если зарегистрирована
        """
        with self._lock:
            return name in self._strategies

    def get_strategies_by_tag(self, tag: str) -> List[str]:
        """
        Получение стратегий по тегу

        Args:
            tag: Тег для поиска

        Returns:
            Список имен стратегий с данным тегом
        """
        with self._lock:
            strategies = []
            for name, metadata in self._metadata.items():
                if tag in metadata.get("tags", []):
                    strategies.append(name)
            return strategies

    def clear(self) -> None:
        """Очистка реестра (для тестирования)"""
        with self._lock:
            self._strategies.clear()
            self._metadata.clear()
            logger.warning("Strategy registry cleared")

    def __repr__(self) -> str:
        return f"StrategyRegistry(strategies={len(self._strategies)})"


# Декоратор для автоматической регистрации стратегий
def register_strategy(name: str, **metadata):
    """
    Декоратор для автоматической регистрации стратегии

    Пример:
        @register_strategy("my_strategy", version="1.0", tags=["scalping"])
        class MyStrategy(StrategyABC):
            pass
    """

    def decorator(strategy_class: Type[StrategyABC]):
        registry = StrategyRegistry()
        registry.register(name, strategy_class, metadata)
        return strategy_class

    return decorator


# Глобальный экземпляр реестра
strategy_registry = StrategyRegistry()
