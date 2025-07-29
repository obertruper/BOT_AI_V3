"""
API Endpoints для BOT_Trading v3.0 Web Interface

Модули endpoints:
- traders: Управление трейдерами
- monitoring: Мониторинг системы
- exchanges: Управление биржами
- strategies: Управление стратегиями
- auth: Аутентификация и авторизация
"""

from .auth import router as auth_router
from .exchanges import router as exchanges_router
from .monitoring import router as monitoring_router
from .strategies import router as strategies_router
from .traders import router as traders_router

__all__ = [
    "traders_router",
    "monitoring_router",
    "exchanges_router",
    "strategies_router",
    "auth_router",
]
