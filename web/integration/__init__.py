"""
Web Integration Layer для BOT_Trading v3.0

Слой интеграции между веб-интерфейсом и основными компонентами системы:
- web_integration: Главный класс интеграции
- event_bridge: Мост событий бот ↔ веб
- data_adapters: Адаптеры данных
- dependencies: Dependency injection
- permissions: Система прав доступа
"""

from .web_integration import WebIntegration
from .event_bridge import EventBridge
from .data_adapters import DataAdapters
from .dependencies import Dependencies
from .permissions import PermissionManager

__all__ = [
    'WebIntegration',
    'EventBridge', 
    'DataAdapters',
    'Dependencies',
    'PermissionManager'
]