#!/usr/bin/env python3
"""
Системные эндпоинты для BOT Trading v3
"""

from datetime import datetime
from typing import Any,Union

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
    components: dict[str, bool]
    traders_count: int
    active_positions: int


class HealthCheck(BaseModel):
    """Модель проверки здоровья"""

    healthy: bool
    components: dict[str, dict[str, Any]]
    timestamp: datetime
    version: str


class SystemConfig(BaseModel):
    """Модель системной конфигурации"""

    database: dict[str, Any]
    monitoring: dict[str, Any]
    logging: dict[str, Any]
    api: dict[str, Any]
    risk_management: dict[str, Any]


class SystemConfigUpdate(BaseModel):
    """Запрос на обновление системной конфигурации (плоский верхний уровень system)"""

    updates: dict[str, Any]


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
            detail=f"Ошибка получения статуса: {e!s}",
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
            detail=f"Ошибка получения конфигурации: {e!s}",
        )


@router.post("/config/update")
async def update_system_config(
    request: SystemConfigUpdate,
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any]:
    """
    Обновить часть системной конфигурации (раздел system) и сохранить изменения.

    Body:
        {
          "updates": {"web_interface": {"host": "0.0.0.0"}, "system": {"environment": "development"}}
        }

    Примечание: обновление плоское (только верхний уровень system). Для вложенных
    структур передавайте их целиком.
    """
    try:
        new_config = config_manager.update_system_config(request.updates)
        return {
            "success": True,
            "data": new_config,
            "timestamp": int(datetime.now().timestamp()),
        }
    except Exception as e:
        logger.error(f"Ошибка обновления системной конфигурации: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": int(datetime.now().timestamp()),
        }


@router.get("/config/raw")
async def get_full_config(
    config_manager: ConfigManager = Depends(get_config_manager),
) -> dict[str, Any]:
    """Получить всю конфигурацию (без фильтрации), для админских нужд UI."""
    try:
        cfg = config_manager.get_config()

        # Убираем секреты если встречаются типичные ключи
        def _sanitize(d: dict[str, Any]) -> dict[str, Any]:
            redacted = {}
            for k, v in d.items():
                lk = k.lower()
                if any(s in lk for s in ["secret", "api_key", "password", "token"]):
                    redacted[k] = "***"
                elif isinstance(v, dict):
                    redacted[k] = _sanitize(v)
                else:
                    redacted[k] = v
            return redacted

        safe_cfg = _sanitize(cfg if isinstance(cfg, dict) else {})
        return {
            "success": True,
            "data": safe_cfg,
            "timestamp": int(datetime.now().timestamp()),
        }
    except Exception as e:
        logger.error(f"Ошибка получения полной конфигурации: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": int(datetime.now().timestamp()),
        }


@router.post("/restart")
async def restart_system(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
) -> dict[str, str]:
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
            detail=f"Ошибка перезапуска: {e!s}",
        )


@router.post("/shutdown")
async def shutdown_system(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
) -> dict[str, str]:
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
            detail=f"Ошибка остановки: {e!s}",
        )


@router.get("/metrics")
async def get_system_metrics(
    orchestrator: SystemOrchestrator = Depends(get_system_orchestrator),
) -> dict[str, Any]:
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
            detail=f"Ошибка получения метрик: {e!s}",
        )


@router.get("/logs")
async def get_system_logs(lines: int = 100, level: Union[str, None] = None) -> dict[str, Any]:
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
            detail=f"Ошибка получения логов: {e!s}",
        )
