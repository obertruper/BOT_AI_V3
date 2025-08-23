#!/usr/bin/env python3
"""
Системные эндпоинты для BOT Trading v3
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from core.system.orchestrator import SystemOrchestrator
from web.integration.dependencies import get_config_manager_dependency, get_orchestrator_dependency

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
    orchestrator: SystemOrchestrator = Depends(get_orchestrator_dependency),
    config_manager: ConfigManager = Depends(get_config_manager_dependency),
) -> SystemStatus:
    """
    Получить текущий статус системы.

    Returns:
        SystemStatus: Полный статус системы
    """
    try:
        # Используем get_system_status() для унифицированного формата
        system_status = await orchestrator.get_system_status()
        system_config = config_manager.get_system_config()

        # Получаем версию и окружение из system_config (теперь это SystemSettings объект)
        version = system_status["system"]["version"]
        environment = "production"  # По умолчанию
        
        if hasattr(system_config, 'environment'):
            environment = system_config.environment

        return SystemStatus(
            status="running" if system_status["system"]["is_running"] else "stopped",
            uptime_seconds=system_status["system"]["uptime_seconds"] or 0,
            start_time=datetime.fromisoformat(system_status["system"]["startup_time"]) if system_status["system"]["startup_time"] else datetime.now(),
            version=version,
            environment=environment,
            components={name: True for name in system_status["components"]["active"]} | {name: False for name in system_status["components"]["failed"]},
            traders_count=system_status["traders"]["active"],
            active_positions=system_status["traders"]["active_positions"],
        )

    except Exception as e:
        logger.error(f"Ошибка получения статуса системы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения статуса: {e!s}",
        )


@router.get("/health", response_model=HealthCheck)
async def health_check(
    orchestrator: SystemOrchestrator = Depends(get_orchestrator_dependency),
    config_manager: ConfigManager = Depends(get_config_manager_dependency),
) -> HealthCheck:
    """
    Проверка здоровья системы.

    Returns:
        HealthCheck: Статус здоровья всех компонентов
    """
    try:
        # Используем get_system_status() для унифицированного формата
        system_status = await orchestrator.get_system_status()

        # Извлекаем информацию о здоровье системы
        health_info = system_status["health"]
        components = {
            "system": {
                "status": "healthy" if health_info["is_healthy"] else "unhealthy",
                "issues": health_info["issues"],
                "warnings": health_info["warnings"]
            }
        }

        # Добавляем информацию о ресурсах
        if "resources" in system_status:
            components["resources"] = {
                "status": "healthy" if health_info["is_healthy"] else "warning",
                "cpu_percent": system_status["resources"].get("cpu_percent", 0),
                "memory_percent": system_status["resources"].get("memory_percent", 0),
                "disk_percent": system_status["resources"].get("disk_percent", 0),
            }

        return HealthCheck(
            healthy=health_info["is_healthy"],
            components=components,
            timestamp=datetime.fromisoformat(health_info["last_check"]),
            version=system_status["system"]["version"],
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
    config_manager: ConfigManager = Depends(get_config_manager_dependency),
) -> SystemConfig:
    """
    Получить системную конфигурацию.

    Returns:
        SystemConfig: Основные настройки системы
    """
    try:
        # Получаем полную конфигурацию как словарь для удобства работы
        full_config = config_manager.get_config()
        
        # Преобразуем Pydantic модель в словарь если нужно
        if hasattr(full_config, 'model_dump'):
            config_dict = full_config.model_dump()
        elif hasattr(full_config, 'dict'):
            config_dict = full_config.dict()
        else:
            config_dict = full_config

        # Фильтруем чувствительные данные
        safe_config = {
            "database": {
                "type": config_dict.get("database", {}).get("type"),
                "host": config_dict.get("database", {}).get("host"),
                "port": config_dict.get("database", {}).get("port"),
                "name": config_dict.get("database", {}).get("name"),
            },
            "monitoring": config_dict.get("monitoring", {}),
            "logging": config_dict.get("logging", {}),
            "api": config_dict.get("api", {}),
            "risk_management": config_dict.get("risk_management", {}),
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
    config_manager: ConfigManager = Depends(get_config_manager_dependency),
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
    config_manager: ConfigManager = Depends(get_config_manager_dependency),
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
    orchestrator: SystemOrchestrator = Depends(get_orchestrator_dependency),
) -> dict[str, str]:
    """
    Перезапустить систему.

    Returns:
        Dict: Статус перезапуска
    """
    try:
        logger.warning("Запрос на перезапуск системы")

        # Останавливаем систему
        await orchestrator.shutdown()

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
    orchestrator: SystemOrchestrator = Depends(get_orchestrator_dependency),
) -> dict[str, str]:
    """
    Остановить систему.

    Returns:
        Dict: Статус остановки
    """
    try:
        logger.warning("Запрос на остановку системы")

        await orchestrator.shutdown()

        return {"status": "success", "message": "Система остановлена"}

    except Exception as e:
        logger.error(f"Ошибка остановки системы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка остановки: {e!s}",
        )


@router.get("/metrics")
async def get_system_metrics(
    orchestrator: SystemOrchestrator = Depends(get_orchestrator_dependency),
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
async def get_system_logs(lines: int = 100, level: Optional[str] = None) -> dict[str, Any]:
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
