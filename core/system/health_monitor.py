#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Монитор здоровья компонентов системы
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
import psutil

from core.logger import setup_logger

logger = setup_logger(__name__)


class ComponentHealth:
    """Информация о здоровье компонента"""

    def __init__(self, name: str):
        self.name = name
        self.healthy = False
        self.last_check = None
        self.error = None
        self.response_time_ms = None
        self.consecutive_failures = 0
        self.uptime_seconds = 0
        self.memory_mb = 0
        self.cpu_percent = 0


class HealthMonitor:
    """
    Мониторинг здоровья компонентов системы

    Функциональность:
    - HTTP health checks
    - Process monitoring
    - Resource usage tracking
    - Alert generation
    """

    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}
        self.components_config: Dict[str, Dict[str, Any]] = {}
        self.is_running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self, components_config: Dict[str, Dict[str, Any]]):
        """
        Инициализация мониторинга

        Args:
            components_config: Конфигурация компонентов для мониторинга
        """
        self.components_config = components_config

        # Создаем объекты здоровья для каждого компонента
        for comp_name, comp_config in components_config.items():
            if comp_config.get("enabled", False):
                self.components[comp_name] = ComponentHealth(comp_name)

        # Создаем HTTP сессию
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))

        self.is_running = True
        logger.info(
            f"✅ HealthMonitor инициализирован для {len(self.components)} компонентов"
        )

    async def check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Проверка здоровья всех компонентов

        Returns:
            Словарь со статусом каждого компонента
        """
        results = {}

        for comp_name, health in self.components.items():
            comp_config = self.components_config.get(comp_name, {})

            # Пропускаем отключенные компоненты
            if not comp_config.get("enabled", False):
                continue

            # Пропускаем интегрированные компоненты
            if comp_config.get("integrated_with"):
                continue

            # Выполняем проверку
            health_status = await self._check_component(comp_name, comp_config)
            results[comp_name] = health_status

        return results

    async def _check_component(
        self, comp_name: str, comp_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Проверка здоровья отдельного компонента"""
        health = self.components[comp_name]
        health.last_check = datetime.now()

        try:
            # HTTP health check если есть endpoint
            if comp_config.get("health_check_endpoint"):
                await self._http_health_check(
                    health, comp_config["health_check_endpoint"]
                )
            else:
                # Process-based health check
                await self._process_health_check(health, comp_name)

            # Сбор метрик ресурсов
            await self._collect_resource_metrics(health, comp_name)

            # Обновляем статус
            if health.healthy:
                health.consecutive_failures = 0
            else:
                health.consecutive_failures += 1

        except Exception as e:
            logger.error(f"Ошибка проверки здоровья {comp_name}: {e}")
            health.healthy = False
            health.error = str(e)
            health.consecutive_failures += 1

        return self._health_to_dict(health)

    async def _http_health_check(self, health: ComponentHealth, endpoint: str):
        """HTTP health check"""
        if not self.session:
            health.healthy = False
            health.error = "HTTP session not initialized"
            return

        try:
            start_time = asyncio.get_event_loop().time()

            async with self.session.get(endpoint) as response:
                health.response_time_ms = (
                    asyncio.get_event_loop().time() - start_time
                ) * 1000

                if response.status == 200:
                    health.healthy = True
                    health.error = None

                    # Парсим дополнительную информацию если есть
                    try:
                        data = await response.json()
                        if "status" in data:
                            health.healthy = data["status"] in [
                                "healthy",
                                "ok",
                                "degraded",
                            ]
                        if "error" in data and data["error"]:
                            health.error = data["error"]
                    except:
                        pass  # Игнорируем ошибки парсинга JSON
                else:
                    health.healthy = False
                    health.error = f"HTTP {response.status}"

        except asyncio.TimeoutError:
            health.healthy = False
            health.error = "Timeout"
            health.response_time_ms = 5000
        except Exception as e:
            health.healthy = False
            health.error = str(e)

    async def _process_health_check(self, health: ComponentHealth, comp_name: str):
        """Process-based health check"""
        # Проверяем PID файл
        pid_file = Path(f"logs/pids/{comp_name}.pid")

        if not pid_file.exists():
            health.healthy = False
            health.error = "PID file not found"
            return

        try:
            pid = int(pid_file.read_text())
            process = psutil.Process(pid)

            # Проверяем статус процесса
            status = process.status()
            if status in [psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING]:
                health.healthy = True
                health.error = None
                health.uptime_seconds = (
                    datetime.now() - datetime.fromtimestamp(process.create_time())
                ).total_seconds()
            else:
                health.healthy = False
                health.error = f"Process status: {status}"

        except psutil.NoSuchProcess:
            health.healthy = False
            health.error = "Process not found"
            # Удаляем устаревший PID файл
            pid_file.unlink()
        except Exception as e:
            health.healthy = False
            health.error = str(e)

    async def _collect_resource_metrics(self, health: ComponentHealth, comp_name: str):
        """Сбор метрик использования ресурсов"""
        pid_file = Path(f"logs/pids/{comp_name}.pid")

        if not pid_file.exists():
            return

        try:
            pid = int(pid_file.read_text())
            process = psutil.Process(pid)

            # CPU и память
            health.cpu_percent = process.cpu_percent(interval=0.1)
            health.memory_mb = process.memory_info().rss / 1024 / 1024

        except:
            pass  # Игнорируем ошибки сбора метрик

    def _health_to_dict(self, health: ComponentHealth) -> Dict[str, Any]:
        """Преобразование объекта здоровья в словарь"""
        return {
            "name": health.name,
            "healthy": health.healthy,
            "last_check": health.last_check.isoformat() if health.last_check else None,
            "error": health.error,
            "response_time_ms": health.response_time_ms,
            "consecutive_failures": health.consecutive_failures,
            "uptime_seconds": health.uptime_seconds,
            "memory_mb": round(health.memory_mb, 2),
            "cpu_percent": round(health.cpu_percent, 2),
        }

    async def get_summary(self) -> Dict[str, Any]:
        """Получение сводки по здоровью системы"""
        total = len(self.components)
        healthy = sum(1 for h in self.components.values() if h.healthy)
        unhealthy = total - healthy

        # Определяем общий статус
        if unhealthy == 0:
            overall_status = "healthy"
        elif unhealthy < total / 2:
            overall_status = "degraded"
        else:
            overall_status = "critical"

        return {
            "overall_status": overall_status,
            "total_components": total,
            "healthy_components": healthy,
            "unhealthy_components": unhealthy,
            "components": {
                name: self._health_to_dict(health)
                for name, health in self.components.items()
            },
        }

    async def stop(self):
        """Остановка мониторинга"""
        self.is_running = False

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()

        if self.session:
            await self.session.close()

        logger.info("✅ HealthMonitor остановлен")
