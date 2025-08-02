#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Системные эндпоинты для BOT Trading v3
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from core.system.orchestrator import SystemOrchestrator
from web.api.dependencies import get_config_manager, get_system_orchestrator

logger = setup_logger("api.system")

router = APIRouter(prefix="/system", tags=["system"])


class SystemStatus(BaseModel):
    """Модель статуса системы"""

    status: str  # running, stopped, error
    uptime_seconds: float
    start_time: datetime
    version: str
    environment: str
    components: Dict[str, bool]
    traders_count: int
    active_positions: int


class HealthCheck(BaseModel):
    """Модель проверки здоровья"""

    healthy: bool
    components: Dict[str, Dict[str, Any]]
    timestamp: datetime
    version: str


class SystemConfig(BaseModel):
    """Модель системной конфигурации"""

    database: Dict[str, Any]
    monitoring: Dict[str, Any]
    logging: Dict[str, Any]
    api: Dict[str, Any]
    risk_management: Dict[str, Any]


@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
    config_manager: ConfigManager = Depends(get_config_manager),
) -> SystemStatus:
    """
    Получить текущий статус системы.

    Returns:
        SystemStatus: Полный статус системы
    """
    try:
        status = await orchestrator.get_status()
        system_config = config_manager.get_system_config()

        return SystemStatus(
            status="running" if status.get("running") else "stopped",
            uptime_seconds=status.get("uptime", 0),
            start_time=status.get("start_time", datetime.now()),
            version=system_config.get("system", {}).get("version", "3.0.0"),
            environment=system_config.get("system", {}).get("environment", "unknown"),
            components=status.get("components", {}),
            traders_count=status.get("traders_count", 0),
            active_positions=status.get("active_positions", 0),
        )

    except Exception as e:
        logger.error(f"Ошибка получения статуса системы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения статуса: {str(e)}",
        )


@router.get("/health", response_model=HealthCheck)
async def health_check(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
    config_manager: ConfigManager = Depends(get_config_manager),
) -> HealthCheck:
    """
    Проверка здоровья системы.

    Returns:
        HealthCheck: Статус здоровья всех компонентов
    """
    try:
        health_status = await orchestrator.health_check()
        system_config = config_manager.get_system_config()

        return HealthCheck(
            healthy=health_status.get("healthy", False),
            components=health_status.get("components", {}),
            timestamp=datetime.now(),
            version=system_config.get("system", {}).get("version", "3.0.0"),
        )

    except Exception as e:
        logger.error(f"Ошибка проверки здоровья: {e}")
        return HealthCheck(
            healthy=False,
            components={"error": {"status": "error", "message": str(e)}},
            timestamp=datetime.now(),
            version="unknown",
        )


@router.get("/config", response_model=SystemConfig)
async def get_system_config(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> SystemConfig:
    """
    Получить системную конфигурацию.

    Returns:
        SystemConfig: Основные настройки системы
    """
    try:
        config = config_manager.get_system_config()

        # Фильтруем чувствительные данные
        safe_config = {
            "database": {
                "type": config.get("database", {}).get("type"),
                "host": config.get("database", {}).get("host"),
                "port": config.get("database", {}).get("port"),
                "name": config.get("database", {}).get("name"),
            },
            "monitoring": config.get("monitoring", {}),
            "logging": config.get("logging", {}),
            "api": config.get("api", {}),
            "risk_management": config.get("risk_management", {}),
        }

        return SystemConfig(**safe_config)

    except Exception as e:
        logger.error(f"Ошибка получения конфигурации: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения конфигурации: {str(e)}",
        )


@router.post("/restart")
async def restart_system(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
) -> Dict[str, str]:
    """
    Перезапустить систему.

    Returns:
        Dict: Статус перезапуска
    """
    try:
        logger.warning("Запрос на перезапуск системы")

        # Останавливаем систему
        await orchestrator.stop()

        # Запускаем заново
        await orchestrator.initialize()
        await orchestrator.start()

        return {"status": "success", "message": "Система успешно перезапущена"}

    except Exception as e:
        logger.error(f"Ошибка перезапуска системы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка перезапуска: {str(e)}",
        )


@router.post("/shutdown")
async def shutdown_system(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
) -> Dict[str, str]:
    """
    Остановить систему.

    Returns:
        Dict: Статус остановки
    """
    try:
        logger.warning("Запрос на остановку системы")

        await orchestrator.stop()

        return {"status": "success", "message": "Система остановлена"}

    except Exception as e:
        logger.error(f"Ошибка остановки системы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка остановки: {str(e)}",
        )


@router.get("/metrics")
async def get_system_metrics(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
) -> Dict[str, Any]:
    """
    Получить системные метрики.

    Returns:
        Dict: Метрики производительности
    """
    try:
        metrics = await orchestrator.get_metrics()

        return {
            "cpu_usage": metrics.get("cpu_usage", 0),
            "memory_usage": metrics.get("memory_usage", 0),
            "disk_usage": metrics.get("disk_usage", 0),
            "network_io": metrics.get("network_io", {}),
            "database_connections": metrics.get("database_connections", 0),
            "active_threads": metrics.get("active_threads", 0),
            "timestamp": datetime.now(),
        }

    except Exception as e:
        logger.error(f"Ошибка получения метрик: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения метрик: {str(e)}",
        )


@router.get("/logs")
async def get_system_logs(
    lines: int = 100, level: Optional[str] = None
) -> Dict[str, Any]:
    """
    Получить последние логи системы.

    Args:
        lines: Количество строк (max 1000)
        level: Уровень логов (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Dict: Последние записи логов
    """
    try:
        # Ограничиваем количество строк
        lines = min(lines, 1000)

        # TODO: Реализовать чтение логов из файлов

        return {
            "logs": [],
            "lines": lines,
            "level": level,
            "message": "Функция чтения логов будет реализована",
        }

    except Exception as e:
        logger.error(f"Ошибка получения логов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения логов: {str(e)}",
        )
