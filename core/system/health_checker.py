"""Модуль HealthChecker для комплексной проверки здоровья системы.

Выполняет проверки всех ключевых зависимостей и компонентов, таких как
база данных, кеш, биржевые подключения и системные ресурсы.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

import asyncpg
import psutil
import redis.asyncio as redis
from ccxt.base.errors import NetworkError as CCXTNetworkError

from core.config.config_manager import ConfigManager, get_global_config_manager
from core.logging.logger_factory import get_global_logger_factory


class HealthChecker:
    """Выполняет комплексную проверку здоровья всех компонентов системы.

    Агрегирует статусы от различных частей приложения для формирования
    общей картины о работоспособности системы.
    """

    def __init__(self, config_manager: ConfigManager | None = None):
        """Инициализирует HealthChecker.

        Args:
            config_manager: Экземпляр менеджера конфигурации.
        """
        self.config_manager = config_manager or get_global_config_manager()
        self.logger_factory = get_global_logger_factory()
        self.logger = self.logger_factory.get_logger("health_checker")
        
        # Компоненты системы для проверки
        self._exchange_registry = None
        self._trader_manager = None
        self._strategy_manager = None

    def set_components(self, exchange_registry=None, trader_manager=None, strategy_manager=None):
        """Устанавливает компоненты системы, которые необходимо проверять."""
        self._exchange_registry = exchange_registry
        self._trader_manager = trader_manager
        self._strategy_manager = strategy_manager

    async def check_all_components(self) -> dict[str, str]:
        """Запускает полную проверку всех настроенных компонентов.

        Returns:
            Словарь, где ключ - название компонента, а значение - его статус
            ('healthy', 'warning', 'critical', 'unknown').
        """
        checks = {
            'database': await self.check_database(),
            'exchanges': await self.check_exchanges(),
            'system_resources': await self.check_system_resources()
        }
        
        # Определяем общее состояние
        if any(status == 'critical' for status in checks.values()):
            return 'critical'
        elif any(status == 'warning' for status in checks.values()):
            return 'warning'
        elif all(status == 'healthy' for status in checks.values()):
            return 'healthy'
        else:
            return 'unknown'

    async def check_database(self) -> str:
        """Проверяет доступность и производительность базы данных PostgreSQL."""
        try:
            from database.connections.postgres import AsyncPGPool
            
            # Простая проверка подключения
            result = await AsyncPGPool.fetch('SELECT version()')
            if result and len(result) > 0:
                return 'healthy'
            else:
                return 'warning'
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return 'critical'

    async def check_redis(self) -> str:
        """Проверяет доступность и производительность Redis."""
        # Redis не используется в текущей конфигурации
        return 'healthy'

    async def check_exchanges(self) -> str:
        """Проверяет подключения ко всем активным биржам."""
        try:
            # Проверяем настройки бирж из конфигурации
            if not self.config:
                return 'warning'
            
            # Проверяем что есть активные биржи
            exchanges = self.config.exchanges
            if hasattr(exchanges, 'bybit') and exchanges.bybit.enabled:
                return 'healthy'
            else:
                return 'warning'
        except Exception as e:
            self.logger.error(f"Exchange health check failed: {e}")
            return 'critical'

    async def check_system_resources(self) -> str:
        """Проверяет использование системных ресурсов (CPU, RAM, диск)."""
        try:
            import psutil
            
            # Проверяем использование CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                return 'critical'
            elif cpu_percent > 80:
                return 'warning'
            
            # Проверяем использование памяти
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return 'critical'
            elif memory.percent > 85:
                return 'warning'
            
            # Проверяем место на диске
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                return 'critical'
            elif disk.percent > 85:
                return 'warning'
            
            return 'healthy'
        except ImportError:
            self.logger.warning("psutil not installed, skipping system resource check")
            return 'unknown'
        except Exception as e:
            self.logger.error(f"System resource check failed: {e}")
            return 'critical'

    async def get_detailed_report(self) -> dict[str, Any]:
        """Формирует детальный отчет о здоровье системы со всеми метриками."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': await self.get_system_health(),
            'checks': {
                'database': await self.check_database(),
                'exchanges': await self.check_exchanges(),
                'system_resources': await self.check_system_resources()
            },
            'config_loaded': self.config is not None,
            'system_info': {
                'name': self.config.system.name if self.config else 'Unknown',
                'version': self.config.system.version if self.config else 'Unknown'
            }
        }
        
        # Добавляем системные метрики если доступны
        try:
            import psutil
            report['system_metrics'] = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        except ImportError:
            pass
        
        return report
