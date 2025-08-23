"""Модуль SharedContext для связи между ядром системы и веб-API.

Предоставляет потокобезопасный синглтон для хранения ссылок на ключевые
компоненты системы, такие как оркестратор, менеджер трейдеров и т.д.
Это позволяет веб-серверу получать доступ к состоянию и функциям
основного приложения, не создавая прямых зависимостей.
"""

import threading
from typing import Any


class SharedContext:
    """Синглтон для хранения и предоставления глобальных компонентов системы.

    Реализует потокобезопасный доступ к экземпляру, гарантируя, что в приложении
    существует только один объект данного класса.

    Attributes:
        orchestrator: Экземпляр SystemOrchestrator.
        trader_manager: Экземпляр TraderManager.
        exchange_factory: Экземпляр ExchangeFactory.
        config_manager: Экземпляр ConfigManager.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Инициализирует атрибуты контекста при первом создании."""
        if not self._initialized:
            self.orchestrator: Any | None = None
            self.trader_manager: Any | None = None
            self.exchange_factory: Any | None = None
            self.config_manager: Any | None = None
            self._initialized = True

    def set_orchestrator(self, orchestrator: Any):
        """Устанавливает экземпляр оркестратора и связанные с ним компоненты.

        Args:
            orchestrator: Экземпляр SystemOrchestrator.
        """
        self.orchestrator = orchestrator
        if orchestrator:
            self.trader_manager = getattr(orchestrator, "trader_manager", None)
            self.exchange_factory = getattr(orchestrator, "exchange_factory", None)
            self.config_manager = getattr(orchestrator, "config_manager", None)

    def get_orchestrator(self) -> Any | None:
        """Возвращает сохраненный экземпляр оркестратора.

        Returns:
            Экземпляр SystemOrchestrator или None, если он не установлен.
        """
        return self.orchestrator

    def is_initialized(self) -> bool:
        """Проверяет, был ли инициализирован контекст (установлен ли оркестратор).

        Returns:
            True, если оркестратор установлен, иначе False.
        """
        return self.orchestrator is not None


# Глобальный экземпляр для импорта в других частях приложения
shared_context = SharedContext()
