"""
Health Checker для системы BOT_Trading v3.0

Компонент для проверки здоровья всех критических подсистем:
- База данных PostgreSQL
- Redis кеш
- Подключения к биржам
- Системные ресурсы
- Внутренние компоненты
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import asyncpg
import psutil
import redis.asyncio as redis
from ccxt.base.errors import NetworkError as CCXTNetworkError

from core.config.config_manager import ConfigManager, get_global_config_manager
from core.logging.logger_factory import get_global_logger_factory


class HealthChecker:
    """
    Проверка здоровья всех компонентов системы

    Выполняет комплексную проверку:
    - Доступность и производительность БД
    - Работоспособность Redis
    - Подключения к биржам и их API
    - Системные ресурсы (CPU, RAM, диск)
    - Критические внутренние компоненты
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or get_global_config_manager()
        self.logger_factory = get_global_logger_factory()
        self.logger = self.logger_factory.get_logger("health_checker")

        # Конфигурация проверок
        self.system_config = self.config_manager.get_system_config()
        self.health_config = self.system_config.get("health_check", {})

        # Таймауты для проверок (в секундах)
        self.db_timeout = self.health_config.get("db_timeout", 5.0)
        self.redis_timeout = self.health_config.get("redis_timeout", 3.0)
        self.exchange_timeout = self.health_config.get("exchange_timeout", 10.0)

        # Пороги для системных ресурсов
        self.cpu_threshold = self.health_config.get("cpu_threshold", 85.0)
        self.memory_threshold = self.health_config.get("memory_threshold", 90.0)
        self.disk_threshold = self.health_config.get("disk_threshold", 95.0)

        # Кеш результатов проверок
        self._cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_ttl = timedelta(seconds=self.health_config.get("cache_ttl", 30))

        # Компоненты для проверки
        self._exchange_registry = None
        self._trader_manager = None
        self._strategy_manager = None

    def set_components(
        self, exchange_registry=None, trader_manager=None, strategy_manager=None
    ):
        """Установка компонентов для проверки"""
        self._exchange_registry = exchange_registry
        self._trader_manager = trader_manager
        self._strategy_manager = strategy_manager

    async def check_all_components(self) -> Dict[str, str]:
        """
        Проверка всех компонентов системы

        Returns:
            Dict[str, str]: Статус каждого компонента
            Возможные статусы: "healthy", "warning", "critical", "unknown"
        """
        self.logger.info("Начало комплексной проверки здоровья системы")

        results = {}

        # Параллельная проверка всех компонентов
        checks = [
            ("database", self.check_database()),
            ("redis", self.check_redis()),
            ("exchanges", self.check_exchanges()),
            ("system_resources", self.check_system_resources()),
            ("traders", self.check_traders()),
            ("strategies", self.check_strategies()),
        ]

        # Выполняем все проверки параллельно
        check_results = await asyncio.gather(
            *[check[1] for check in checks], return_exceptions=True
        )

        # Обрабатываем результаты
        for (name, _), result in zip(checks, check_results):
            if isinstance(result, Exception):
                self.logger.error(f"Ошибка проверки {name}: {result}")
                results[name] = "critical"
            else:
                results[name] = result

        # Логируем общий результат
        critical_count = sum(1 for status in results.values() if status == "critical")
        warning_count = sum(1 for status in results.values() if status == "warning")

        if critical_count > 0:
            self.logger.error(
                f"Проверка здоровья: {critical_count} критических проблем",
                extra={"results": results},
            )
        elif warning_count > 0:
            self.logger.warning(
                f"Проверка здоровья: {warning_count} предупреждений",
                extra={"results": results},
            )
        else:
            self.logger.info("Проверка здоровья: все компоненты работают нормально")

        return results

    async def check_database(self) -> str:
        """Проверка подключения и производительности PostgreSQL"""
        # Проверяем кеш
        cached = self._get_cached_result("database")
        if cached:
            return cached

        try:
            # Получаем конфигурацию БД
            db_config = self.config_manager.get_database_config()

            # Создаем подключение с таймаутом
            start_time = time.time()
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=db_config["host"],
                    port=db_config["port"],
                    user=db_config["user"],
                    password=db_config["password"],
                    database=db_config["database"],
                ),
                timeout=self.db_timeout,
            )

            try:
                # Проверяем простой запрос
                result = await conn.fetchval("SELECT 1")
                if result != 1:
                    return self._cache_result("database", "critical")

                # Проверяем время отклика
                response_time = time.time() - start_time

                # Проверяем количество активных подключений
                active_connections = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                max_connections = await conn.fetchval("SHOW max_connections")

                # Проверяем размер БД
                db_size = await conn.fetchval(
                    f"SELECT pg_database_size('{db_config['database']}')"
                )

                self.logger.debug(
                    "Статус PostgreSQL",
                    extra={
                        "response_time_ms": response_time * 1000,
                        "active_connections": active_connections,
                        "max_connections": max_connections,
                        "db_size_mb": db_size / 1024 / 1024,
                    },
                )

                # Определяем статус
                if response_time > 2.0:
                    return self._cache_result("database", "warning")
                elif active_connections > int(max_connections) * 0.8:
                    return self._cache_result("database", "warning")
                else:
                    return self._cache_result("database", "healthy")

            finally:
                await conn.close()

        except asyncio.TimeoutError:
            self.logger.error("Таймаут подключения к PostgreSQL")
            return self._cache_result("database", "critical")
        except Exception as e:
            self.logger.error(f"Ошибка проверки PostgreSQL: {e}")
            return self._cache_result("database", "critical")

    async def check_redis(self) -> str:
        """Проверка подключения и производительности Redis"""
        # Проверяем кеш
        cached = self._get_cached_result("redis")
        if cached:
            return cached

        try:
            # Получаем конфигурацию Redis
            redis_config = self.config_manager.get_redis_config()

            # Создаем подключение
            start_time = time.time()
            client = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                password=redis_config.get("password"),
                decode_responses=True,
            )

            # Проверяем ping с таймаутом
            await asyncio.wait_for(client.ping(), timeout=self.redis_timeout)

            # Проверяем производительность
            test_key = "health_check_test"
            test_value = f"test_{datetime.now().isoformat()}"

            # SET операция
            await client.set(test_key, test_value, ex=60)

            # GET операция
            retrieved = await client.get(test_key)
            if retrieved != test_value:
                return self._cache_result("redis", "critical")

            # Получаем информацию о памяти
            info = await client.info("memory")
            used_memory_mb = info.get("used_memory", 0) / 1024 / 1024

            # Проверяем время отклика
            response_time = time.time() - start_time

            # Очищаем тестовый ключ
            await client.delete(test_key)

            # Закрываем подключение
            await client.close()

            self.logger.debug(
                "Статус Redis",
                extra={
                    "response_time_ms": response_time * 1000,
                    "used_memory_mb": used_memory_mb,
                },
            )

            # Определяем статус
            if response_time > 1.0:
                return self._cache_result("redis", "warning")
            else:
                return self._cache_result("redis", "healthy")

        except asyncio.TimeoutError:
            self.logger.error("Таймаут подключения к Redis")
            return self._cache_result("redis", "critical")
        except Exception as e:
            self.logger.error(f"Ошибка проверки Redis: {e}")
            return self._cache_result("redis", "critical")

    async def check_exchanges(self) -> str:
        """Проверка подключений к биржам"""
        if not self._exchange_registry:
            self.logger.warning("Exchange registry не установлен")
            return "unknown"

        # Проверяем кеш
        cached = self._get_cached_result("exchanges")
        if cached:
            return cached

        try:
            # Получаем список активных бирж
            exchanges = await self._exchange_registry.get_all_exchanges()

            if not exchanges:
                return self._cache_result("exchanges", "warning")

            results = []

            # Проверяем каждую биржу
            for exchange_name, exchange in exchanges.items():
                try:
                    # Проверяем статус биржи
                    start_time = time.time()

                    # Пытаемся получить баланс как тест подключения
                    await asyncio.wait_for(
                        exchange.fetch_balance(), timeout=self.exchange_timeout
                    )

                    latency = (time.time() - start_time) * 1000

                    self.logger.debug(
                        f"Биржа {exchange_name} доступна", extra={"latency_ms": latency}
                    )

                    results.append(
                        {
                            "exchange": exchange_name,
                            "status": "healthy" if latency < 2000 else "warning",
                            "latency_ms": latency,
                        }
                    )

                except (asyncio.TimeoutError, CCXTNetworkError) as e:
                    self.logger.warning(f"Проблема с биржей {exchange_name}: {e}")
                    results.append(
                        {
                            "exchange": exchange_name,
                            "status": "critical",
                            "error": str(e),
                        }
                    )
                except Exception as e:
                    self.logger.error(f"Ошибка проверки биржи {exchange_name}: {e}")
                    results.append(
                        {
                            "exchange": exchange_name,
                            "status": "critical",
                            "error": str(e),
                        }
                    )

            # Определяем общий статус
            critical_count = sum(1 for r in results if r["status"] == "critical")
            warning_count = sum(1 for r in results if r["status"] == "warning")

            if critical_count >= len(results) * 0.5:
                return self._cache_result("exchanges", "critical")
            elif critical_count > 0 or warning_count > 0:
                return self._cache_result("exchanges", "warning")
            else:
                return self._cache_result("exchanges", "healthy")

        except Exception as e:
            self.logger.error(f"Ошибка проверки бирж: {e}")
            return self._cache_result("exchanges", "critical")

    async def check_system_resources(self) -> str:
        """Проверка системных ресурсов"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)

            # Память
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Диск
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            # Сетевые подключения
            connections = len(psutil.net_connections())

            self.logger.debug(
                "Системные ресурсы",
                extra={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_gb": memory.available / 1024 / 1024 / 1024,
                    "disk_percent": disk_percent,
                    "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                    "network_connections": connections,
                },
            )

            # Определяем статус
            if (
                cpu_percent > self.cpu_threshold
                or memory_percent > self.memory_threshold
                or disk_percent > self.disk_threshold
            ):
                return "warning"
            else:
                return "healthy"

        except Exception as e:
            self.logger.error(f"Ошибка проверки системных ресурсов: {e}")
            return "unknown"

    async def check_traders(self) -> str:
        """Проверка состояния трейдеров"""
        if not self._trader_manager:
            return "unknown"

        try:
            # Получаем статистику трейдеров
            active_traders = await self._trader_manager.get_active_traders()
            total_traders = await self._trader_manager.get_total_traders()

            self.logger.debug(
                "Статус трейдеров",
                extra={
                    "active": len(active_traders),
                    "total": total_traders,
                },
            )

            # Если нет активных трейдеров - это может быть нормально
            return "healthy"

        except Exception as e:
            self.logger.error(f"Ошибка проверки трейдеров: {e}")
            return "warning"

    async def check_strategies(self) -> str:
        """Проверка состояния стратегий"""
        if not self._strategy_manager:
            return "unknown"

        try:
            # Получаем статистику стратегий
            active_strategies = await self._strategy_manager.get_active_strategies()

            self.logger.debug(
                "Статус стратегий", extra={"active": len(active_strategies)}
            )

            return "healthy"

        except Exception as e:
            self.logger.error(f"Ошибка проверки стратегий: {e}")
            return "warning"

    def _get_cached_result(self, component: str) -> Optional[str]:
        """Получение результата из кеша"""
        if component in self._cache:
            status, timestamp = self._cache[component]
            if datetime.now() - timestamp < self._cache_ttl:
                return status
        return None

    def _cache_result(self, component: str, status: str) -> str:
        """Кеширование результата проверки"""
        self._cache[component] = (status, datetime.now())
        return status

    async def get_detailed_report(self) -> Dict[str, Any]:
        """
        Получение детального отчета о здоровье системы

        Returns:
            Dict с подробной информацией о каждом компоненте
        """
        # Выполняем все проверки
        component_statuses = await self.check_all_components()

        # Собираем детальную информацию
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": self._calculate_overall_status(component_statuses),
            "components": component_statuses,
            "details": {},
        }

        # Добавляем детали по системным ресурсам
        try:
            cpu_info = psutil.cpu_freq()
            report["details"]["system"] = {
                "cpu": {
                    "percent": psutil.cpu_percent(interval=1),
                    "cores": psutil.cpu_count(),
                    "frequency_mhz": cpu_info.current if cpu_info else None,
                },
                "memory": {
                    "total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                    "available_gb": psutil.virtual_memory().available
                    / 1024
                    / 1024
                    / 1024,
                    "percent": psutil.virtual_memory().percent,
                },
                "disk": {
                    "total_gb": psutil.disk_usage("/").total / 1024 / 1024 / 1024,
                    "free_gb": psutil.disk_usage("/").free / 1024 / 1024 / 1024,
                    "percent": psutil.disk_usage("/").percent,
                },
            }
        except Exception as e:
            self.logger.error(f"Ошибка сбора системной информации: {e}")

        return report

    def _calculate_overall_status(self, component_statuses: Dict[str, str]) -> str:
        """Расчет общего статуса системы"""
        if any(status == "critical" for status in component_statuses.values()):
            return "critical"
        elif any(status == "warning" for status in component_statuses.values()):
            return "warning"
        elif any(status == "unknown" for status in component_statuses.values()):
            return "degraded"
        else:
            return "healthy"
