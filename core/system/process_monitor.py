"""
Мониторинг процессов и компонентов системы в реальном времени
"""

import asyncio
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import psutil
import redis.asyncio as redis

from database.db_manager import get_db

logger = logging.getLogger(__name__)


@dataclass
class ComponentHealth:
    """Состояние здоровья компонента"""

    component_name: str
    status: str  # 'healthy', 'warning', 'critical', 'unknown'
    last_heartbeat: datetime
    error_count: int = 0
    warning_count: int = 0
    uptime_seconds: float = 0
    memory_usage_mb: float = 0
    cpu_usage_percent: float = 0
    active_tasks: int = 0
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """Системные метрики"""

    timestamp: datetime
    total_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    cpu_percent: float
    disk_usage_percent: float
    active_connections: int
    redis_connections: int = 0
    postgres_connections: int = 0
    network_io: dict[str, int] = field(default_factory=dict)


class ProcessMonitor:
    """
    Мониторинг процессов и компонентов системы

    Основные функции:
    - Мониторинг здоровья всех компонентов системы
    - Сбор системных метрик (CPU, память, диск)
    - Отслеживание производительности процессов
    - Обнаружение аномалий и проблем
    - Автоматические уведомления и алерты
    - Ведение истории метрик
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis_client = redis_client
        self.db_manager = None
        self.components: dict[str, ComponentHealth] = {}
        self.system_metrics: deque = deque(maxlen=1000)  # Последние 1000 замеров
        self.alert_rules: dict[str, dict] = {}
        self.active_alerts: dict[str, datetime] = {}

        # Настройки мониторинга
        self.monitoring_interval = 30  # секунд
        self.heartbeat_timeout = timedelta(minutes=5)
        self.metrics_retention_hours = 24

        # Статистика
        self.stats = {
            "monitoring_started": datetime.now(),
            "total_heartbeats": 0,
            "total_alerts": 0,
            "system_checks": 0,
        }

        # Задачи мониторинга
        self._monitoring_tasks: list[asyncio.Task] = []
        self._running = False

        # Инициализация Redis
        if not self.redis_client:
            self._init_redis()

        # Настройка правил алертов
        self._init_alert_rules()

    def _init_redis(self):
        """Инициализация Redis клиента"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379/4")  # DB 4 для мониторинга
            logger.info("✅ Redis клиент инициализирован для мониторинга")
        except Exception as e:
            logger.warning(f"⚠️  Redis недоступен для мониторинга: {e}")
            self.redis_client = None

    def _init_alert_rules(self):
        """Инициализация правил для алертов"""
        self.alert_rules = {
            "high_memory_usage": {
                "condition": lambda metrics: metrics.memory_percent > 85,
                "severity": "warning",
                "message": "Высокое использование памяти: {memory_percent:.1f}%",
            },
            "critical_memory_usage": {
                "condition": lambda metrics: metrics.memory_percent > 95,
                "severity": "critical",
                "message": "Критическое использование памяти: {memory_percent:.1f}%",
            },
            "high_cpu_usage": {
                "condition": lambda metrics: metrics.cpu_percent > 80,
                "severity": "warning",
                "message": "Высокая загрузка CPU: {cpu_percent:.1f}%",
            },
            "disk_space_low": {
                "condition": lambda metrics: metrics.disk_usage_percent > 90,
                "severity": "critical",
                "message": "Мало места на диске: {disk_usage_percent:.1f}%",
            },
            "component_not_responding": {
                "condition": lambda component: (datetime.now() - component.last_heartbeat)
                > timedelta(minutes=5),
                "severity": "critical",
                "message": "Компонент {component_name} не отвечает более 5 минут",
            },
            "high_error_rate": {
                "condition": lambda component: component.error_count > 10,
                "severity": "warning",
                "message": "Компонент {component_name} имеет {error_count} ошибок",
            },
        }

    async def start(self):
        """Запуск мониторинга"""
        if self._running:
            logger.warning("ProcessMonitor уже запущен")
            return

        self._running = True

        # Инициализируем DBManager
        self.db_manager = await get_db()

        logger.info("🚀 Запуск ProcessMonitor")

        # Запуск задач мониторинга
        self._monitoring_tasks = [
            asyncio.create_task(self._system_metrics_loop()),
            asyncio.create_task(self._component_health_check_loop()),
            asyncio.create_task(self._alert_processor_loop()),
            asyncio.create_task(self._cleanup_loop()),
        ]

        logger.info("✅ ProcessMonitor запущен")

    async def stop(self):
        """Остановка мониторинга"""
        if not self._running:
            return

        self._running = False
        logger.info("🛑 Остановка ProcessMonitor")

        # Отмена всех задач
        for task in self._monitoring_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._monitoring_tasks.clear()
        logger.info("✅ ProcessMonitor остановлен")

    async def register_component(
        self, component_name: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """
        Регистрация компонента для мониторинга

        Args:
            component_name: Название компонента
            metadata: Дополнительные метаданные

        Returns:
            True если регистрация успешна
        """
        try:
            if component_name in self.components:
                logger.warning(f"⚠️  Компонент '{component_name}' уже зарегистрирован")
                return False

            self.components[component_name] = ComponentHealth(
                component_name=component_name,
                status="unknown",
                last_heartbeat=datetime.now(),
                metadata=metadata or {},
            )

            logger.info(f"✅ Зарегистрирован компонент для мониторинга: {component_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка регистрации компонента '{component_name}': {e}")
            return False

    async def heartbeat(
        self,
        component_name: str,
        status: str | None = None,
        active_tasks: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Отправка heartbeat от компонента

        Args:
            component_name: Название компонента
            status: Текущий статус ('healthy', 'warning', 'critical')
            active_tasks: Количество активных задач
            metadata: Дополнительные метаданные

        Returns:
            True если heartbeat принят
        """
        try:
            if component_name not in self.components:
                # Автоматическая регистрация
                await self.register_component(component_name, metadata)

            component = self.components[component_name]
            component.last_heartbeat = datetime.now()

            if status:
                component.status = status
            elif component.status == "unknown":
                component.status = "healthy"

            if active_tasks is not None:
                component.active_tasks = active_tasks

            if metadata:
                component.metadata.update(metadata)

            # Обновляем системные метрики для процесса
            await self._update_component_metrics(component)

            self.stats["total_heartbeats"] += 1

            # Сохраняем в Redis если доступен
            if self.redis_client:
                await self._save_component_to_redis(component)

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обработки heartbeat от '{component_name}': {e}")
            return False

    async def report_error(
        self, component_name: str, error_message: str, is_critical: bool = False
    ):
        """
        Сообщение об ошибке в компоненте

        Args:
            component_name: Название компонента
            error_message: Сообщение об ошибке
            is_critical: Является ли ошибка критической
        """
        try:
            if component_name not in self.components:
                await self.register_component(component_name)

            component = self.components[component_name]
            component.error_count += 1
            component.last_error = error_message

            if is_critical:
                component.status = "critical"
            elif component.status == "healthy":
                component.status = "warning"

            logger.warning(f"⚠️  Ошибка в компоненте '{component_name}': {error_message}")

            # Создаем алерт
            await self._create_alert(
                f"error_{component_name}",
                "error" if not is_critical else "critical",
                f"Ошибка в компоненте {component_name}: {error_message}",
            )

        except Exception as e:
            logger.error(f"❌ Ошибка сообщения об ошибке для '{component_name}': {e}")

    async def report_warning(self, component_name: str, warning_message: str):
        """Сообщение о предупреждении в компоненте"""
        try:
            if component_name not in self.components:
                await self.register_component(component_name)

            component = self.components[component_name]
            component.warning_count += 1

            if component.status == "healthy":
                component.status = "warning"

            logger.info(f"⚠️  Предупреждение в компоненте '{component_name}': {warning_message}")

        except Exception as e:
            logger.error(f"❌ Ошибка сообщения о предупреждении для '{component_name}': {e}")

    def get_component_health(self, component_name: str | None = None) -> dict[str, Any]:
        """
        Получение состояния здоровья компонентов

        Args:
            component_name: Название конкретного компонента (если None - все)

        Returns:
            Словарь с информацией о здоровье компонентов
        """
        if component_name:
            component = self.components.get(component_name)
            if not component:
                return {}

            return {
                "component_name": component.component_name,
                "status": component.status,
                "last_heartbeat": component.last_heartbeat.isoformat(),
                "uptime_seconds": component.uptime_seconds,
                "error_count": component.error_count,
                "warning_count": component.warning_count,
                "memory_usage_mb": component.memory_usage_mb,
                "cpu_usage_percent": component.cpu_usage_percent,
                "active_tasks": component.active_tasks,
                "last_error": component.last_error,
                "metadata": component.metadata,
            }
        else:
            # Вся информация
            health_data = {}
            for name, component in self.components.items():
                health_data[name] = {
                    "status": component.status,
                    "last_heartbeat": component.last_heartbeat.isoformat(),
                    "uptime_seconds": component.uptime_seconds,
                    "error_count": component.error_count,
                    "warning_count": component.warning_count,
                    "memory_usage_mb": component.memory_usage_mb,
                    "cpu_usage_percent": component.cpu_usage_percent,
                    "active_tasks": component.active_tasks,
                    "last_error": component.last_error,
                }

            return health_data

    def get_system_metrics(self, last_n_minutes: int = 5) -> list[dict[str, Any]]:
        """
        Получение системных метрик за период

        Args:
            last_n_minutes: За сколько минут получить метрики

        Returns:
            Список метрик
        """
        cutoff_time = datetime.now() - timedelta(minutes=last_n_minutes)

        filtered_metrics = []
        for metrics in self.system_metrics:
            if metrics.timestamp >= cutoff_time:
                filtered_metrics.append(
                    {
                        "timestamp": metrics.timestamp.isoformat(),
                        "memory_percent": metrics.memory_percent,
                        "cpu_percent": metrics.cpu_percent,
                        "disk_usage_percent": metrics.disk_usage_percent,
                        "active_connections": metrics.active_connections,
                        "redis_connections": metrics.redis_connections,
                        "postgres_connections": metrics.postgres_connections,
                    }
                )

        return filtered_metrics

    def get_alerts(self, active_only: bool = True) -> list[dict[str, Any]]:
        """
        Получение алертов

        Args:
            active_only: Только активные алерты

        Returns:
            Список алертов
        """
        if active_only:
            alerts = []
            for alert_id, alert_time in self.active_alerts.items():
                alerts.append(
                    {
                        "alert_id": alert_id,
                        "created_at": alert_time.isoformat(),
                        "age_seconds": (datetime.now() - alert_time).total_seconds(),
                    }
                )
            return alerts
        else:
            # Здесь можно добавить получение всех алертов из базы/Redis
            return []

    def get_stats(self) -> dict[str, Any]:
        """Получение статистики мониторинга"""
        now = datetime.now()
        uptime = (now - self.stats["monitoring_started"]).total_seconds()

        return {
            "monitoring_started": self.stats["monitoring_started"].isoformat(),
            "uptime_seconds": uptime,
            "total_components": len(self.components),
            "healthy_components": len(
                [c for c in self.components.values() if c.status == "healthy"]
            ),
            "warning_components": len(
                [c for c in self.components.values() if c.status == "warning"]
            ),
            "critical_components": len(
                [c for c in self.components.values() if c.status == "critical"]
            ),
            "total_heartbeats": self.stats["total_heartbeats"],
            "total_alerts": self.stats["total_alerts"],
            "system_checks": self.stats["system_checks"],
            "active_alerts": len(self.active_alerts),
            "metrics_collected": len(self.system_metrics),
        }

    async def _system_metrics_loop(self):
        """Цикл сбора системных метрик"""
        while self._running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка сбора системных метрик: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _component_health_check_loop(self):
        """Цикл проверки здоровья компонентов"""
        while self._running:
            try:
                await self._check_component_health()
                await asyncio.sleep(30)  # Каждые 30 секунд
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка проверки здоровья компонентов: {e}")
                await asyncio.sleep(30)

    async def _alert_processor_loop(self):
        """Цикл обработки алертов"""
        while self._running:
            try:
                await self._process_alerts()
                await asyncio.sleep(60)  # Каждую минуту
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка обработки алертов: {e}")
                await asyncio.sleep(60)

    async def _cleanup_loop(self):
        """Цикл очистки старых данных"""
        while self._running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Каждый час
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка очистки данных: {e}")
                await asyncio.sleep(3600)

    async def _collect_system_metrics(self):
        """Сбор системных метрик"""
        try:
            # Системные метрики
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            # Используем SSD path если доступен, иначе root
            disk_path = "/mnt/SSD" if os.path.exists("/mnt/SSD") else "/"
            disk = psutil.disk_usage(disk_path)

            # Сетевые подключения
            connections = len(psutil.net_connections(kind="inet"))

            # Redis подключения
            redis_connections = 0
            if self.redis_client:
                try:
                    info = await self.redis_client.info()
                    redis_connections = info.get("connected_clients", 0)
                except:
                    pass

            # PostgreSQL подключения
            postgres_connections = 0
            try:
                result = await self.db_manager.fetch_one(
                    "SELECT count(*) as connections FROM pg_stat_activity"
                )
                if result:
                    postgres_connections = result["connections"]
            except:
                pass

            metrics = SystemMetrics(
                timestamp=datetime.now(),
                total_memory_mb=memory.total / (1024 * 1024),
                used_memory_mb=memory.used / (1024 * 1024),
                memory_percent=memory.percent,
                cpu_percent=cpu_percent,
                disk_usage_percent=disk.percent,
                active_connections=connections,
                redis_connections=redis_connections,
                postgres_connections=postgres_connections,
            )

            self.system_metrics.append(metrics)
            self.stats["system_checks"] += 1

            # Сохраняем в Redis если доступен
            if self.redis_client:
                await self._save_metrics_to_redis(metrics)

        except Exception as e:
            logger.error(f"❌ Ошибка сбора системных метрик: {e}")

    async def _check_component_health(self):
        """Проверка здоровья компонентов"""
        now = datetime.now()

        for component_name, component in list(self.components.items()):
            try:
                # Проверяем timeout heartbeat
                if (now - component.last_heartbeat) > self.heartbeat_timeout:
                    if component.status != "critical":
                        component.status = "critical"
                        await self._create_alert(
                            f"heartbeat_timeout_{component_name}",
                            "critical",
                            f"Компонент {component_name} не отвечает более {self.heartbeat_timeout}",
                        )

                # Обновляем uptime
                component.uptime_seconds = (now - component.last_heartbeat).total_seconds()

            except Exception as e:
                logger.error(f"❌ Ошибка проверки компонента '{component_name}': {e}")

    async def _process_alerts(self):
        """Обработка алертов на основе правил"""
        try:
            # Проверяем системные алерты
            if self.system_metrics:
                latest_metrics = self.system_metrics[-1]

                for rule_name, rule in self.alert_rules.items():
                    if rule_name.startswith("component_"):
                        continue  # Пропускаем правила для компонентов

                    try:
                        if rule["condition"](latest_metrics):
                            alert_id = f"system_{rule_name}"
                            if alert_id not in self.active_alerts:
                                message = rule["message"].format(**latest_metrics.__dict__)
                                await self._create_alert(alert_id, rule["severity"], message)
                        else:
                            # Убираем алерт если условие больше не выполняется
                            alert_id = f"system_{rule_name}"
                            if alert_id in self.active_alerts:
                                del self.active_alerts[alert_id]
                    except Exception as e:
                        logger.error(f"❌ Ошибка проверки правила '{rule_name}': {e}")

            # Проверяем алерты для компонентов
            for component_name, component in self.components.items():
                for rule_name, rule in self.alert_rules.items():
                    if not rule_name.startswith("component_"):
                        continue

                    try:
                        if rule["condition"](component):
                            alert_id = f"component_{rule_name}_{component_name}"
                            if alert_id not in self.active_alerts:
                                message = rule["message"].format(**component.__dict__)
                                await self._create_alert(alert_id, rule["severity"], message)
                    except Exception as e:
                        logger.error(f"❌ Ошибка проверки правила компонента '{rule_name}': {e}")

        except Exception as e:
            logger.error(f"❌ Ошибка обработки алертов: {e}")

    async def _create_alert(self, alert_id: str, severity: str, message: str):
        """Создание алерта"""
        try:
            if alert_id in self.active_alerts:
                return  # Алерт уже существует

            self.active_alerts[alert_id] = datetime.now()
            self.stats["total_alerts"] += 1

            # Логируем алерт
            if severity == "critical":
                logger.critical(f"🚨 CRITICAL ALERT: {message}")
            elif severity == "warning":
                logger.warning(f"⚠️  WARNING ALERT: {message}")
            else:
                logger.info(f"ℹ️  INFO ALERT: {message}")

            # Сохраняем в Redis/БД если нужно
            if self.redis_client:
                alert_data = {
                    "alert_id": alert_id,
                    "severity": severity,
                    "message": message,
                    "created_at": datetime.now().isoformat(),
                }
                await self.redis_client.setex(
                    f"alert:{alert_id}",
                    3600,
                    str(alert_data),  # TTL 1 час
                )

        except Exception as e:
            logger.error(f"❌ Ошибка создания алерта: {e}")

    async def _update_component_metrics(self, component: ComponentHealth):
        """Обновление метрик компонента"""
        try:
            # Получаем метрики процесса
            current_process = psutil.Process()
            component.memory_usage_mb = current_process.memory_info().rss / (1024 * 1024)
            component.cpu_usage_percent = current_process.cpu_percent()

        except Exception as e:
            logger.debug(
                f"Не удалось получить метрики для компонента '{component.component_name}': {e}"
            )

    async def _save_component_to_redis(self, component: ComponentHealth):
        """Сохранение состояния компонента в Redis"""
        try:
            if not self.redis_client:
                return

            component_data = {
                "status": component.status,
                "last_heartbeat": component.last_heartbeat.isoformat(),
                "error_count": component.error_count,
                "warning_count": component.warning_count,
                "uptime_seconds": component.uptime_seconds,
                "memory_usage_mb": component.memory_usage_mb,
                "cpu_usage_percent": component.cpu_usage_percent,
                "active_tasks": component.active_tasks,
            }

            await self.redis_client.setex(
                f"component:{component.component_name}",
                300,
                str(component_data),  # TTL 5 минут
            )

        except Exception as e:
            logger.warning(f"⚠️  Ошибка сохранения компонента в Redis: {e}")

    async def _save_metrics_to_redis(self, metrics: SystemMetrics):
        """Сохранение системных метрик в Redis"""
        try:
            if not self.redis_client:
                return

            metrics_data = {
                "timestamp": metrics.timestamp.isoformat(),
                "memory_percent": metrics.memory_percent,
                "cpu_percent": metrics.cpu_percent,
                "disk_usage_percent": metrics.disk_usage_percent,
                "active_connections": metrics.active_connections,
            }

            # Сохраняем с временным ключом
            key = f"metrics:{int(metrics.timestamp.timestamp())}"
            await self.redis_client.setex(key, 3600, str(metrics_data))  # TTL 1 час

        except Exception as e:
            logger.warning(f"⚠️  Ошибка сохранения метрик в Redis: {e}")

    async def _cleanup_old_data(self):
        """Очистка старых данных"""
        try:
            # Очистка старых алертов
            cutoff_time = datetime.now() - timedelta(hours=24)
            expired_alerts = []

            for alert_id, alert_time in self.active_alerts.items():
                if alert_time < cutoff_time:
                    expired_alerts.append(alert_id)

            for alert_id in expired_alerts:
                del self.active_alerts[alert_id]

            if expired_alerts:
                logger.info(f"🧹 Очищено старых алертов: {len(expired_alerts)}")

            # Очистка Redis
            if self.redis_client:
                # Очистка старых метрик
                cutoff_timestamp = int(cutoff_time.timestamp())
                keys = await self.redis_client.keys("metrics:*")

                deleted_count = 0
                for key in keys:
                    try:
                        timestamp = int(key.decode().split(":")[1])
                        if timestamp < cutoff_timestamp:
                            await self.redis_client.delete(key)
                            deleted_count += 1
                    except:
                        continue

                if deleted_count > 0:
                    logger.info(f"🧹 Очищено старых метрик из Redis: {deleted_count}")

        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых данных: {e}")


# Глобальный экземпляр монитора
process_monitor = ProcessMonitor()
