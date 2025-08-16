"""
Shared context для связи между main.py и web API
"""

import threading
from typing import Any


class SharedContext:
    """Синглтон для хранения глобальных компонентов системы"""

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
        if not self._initialized:
            self.orchestrator = None
            self.trader_manager = None
            self.exchange_factory = None
            self.config_manager = None
            self._initialized = True

    def set_orchestrator(self, orchestrator: Any):
        """Установить orchestrator"""
        self.orchestrator = orchestrator
        if orchestrator:
            self.trader_manager = getattr(orchestrator, "trader_manager", None)
            self.exchange_factory = getattr(orchestrator, "exchange_factory", None)
            self.config_manager = getattr(orchestrator, "config_manager", None)

    def get_orchestrator(self) -> Any | None:
        """Получить orchestrator"""
        return self.orchestrator

    def is_initialized(self) -> bool:
        """Проверить инициализацию"""
        return self.orchestrator is not None


# Глобальный экземпляр
shared_context = SharedContext()
