"""
API Endpoints для BOT_Trading v3.0 Web Interface

Модули endpoints:
- traders: Управление трейдерами
- monitoring: Мониторинг системы
- exchanges: Управление биржами
- strategies: Управление стратегиями
- auth: Аутентификация и авторизация
- system: Системные операции
"""

from .auth import router as auth_router
from .exchanges import router as exchanges_router
from .monitoring import router as monitoring_router
from .orders import router as orders_router
from .positions import router as positions_router
from .strategies import router as strategies_router
from .system import router as system_router
from .traders import router as traders_router

__all__ = [
    "auth_router",
    "exchanges_router",
    "monitoring_router",
    "orders_router",
    "positions_router",
    "strategies_router",
    "system_router",
    "traders_router",
]
