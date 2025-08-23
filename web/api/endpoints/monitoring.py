"""
Monitoring API Endpoints

REST API для мониторинга системы:
- Здоровье компонентов
- Метрики производительности
- Статистика торговли
- Системные алерты
"""

from datetime import datetime, timedelta
from typing import Any

import psutil
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("monitoring_api")

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# =================== MODELS ===================


class SystemHealth(BaseModel):
    """Состояние здоровья системы"""

    status: str  # healthy, warning, critical
    components: dict[str, str]
    last_check: datetime
    uptime_seconds: int


class SystemMetrics(BaseModel):
    """Системные метрики"""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_connections: int
    active_traders: int
    total_trades_today: int
    last_updated: datetime


class TradingStats(BaseModel):
    """Статистика торговли"""

    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    success_rate: float
    average_trade_duration: float
    period: str


class Alert(BaseModel):
    """Системный алерт"""

    id: str
    level: str  # info, warning, error, critical
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False


class ExchangeStatus(BaseModel):
    """Статус биржи"""

    exchange: str
    status: str  # connected, disconnected, error
    latency_ms: float | None = None
    last_heartbeat: datetime | None = None
    api_calls_count: int = 0
    error_rate: float = 0.0


# =================== ENDPOINTS ===================


@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """Получить общее состояние здоровья системы"""
    try:
        health_checker = get_health_checker()
        health_status = await health_checker.check_all_components()

        # Определяем общий статус
        overall_status = "healthy"
        for component_status in health_status.values():
            if component_status == "critical":
                overall_status = "critical"
                break
            elif component_status == "warning" and overall_status == "healthy":
                overall_status = "warning"

        # Получаем uptime
        orchestrator = get_orchestrator()
        uptime = orchestrator.get_uptime_seconds()

        health = SystemHealth(
            status=overall_status,
            components=health_status,
            last_check=datetime.now(),
            uptime_seconds=uptime,
        )

        logger.info(f"Проверка здоровья системы: {overall_status}")
        return health

    except Exception as e:
        logger.error(f"Ошибка проверки здоровья системы: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка проверки здоровья: {e!s}")


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """Получить системные метрики"""
    try:
        # Системные метрики
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network_connections = len(psutil.net_connections())

        # Торговые метрики
        trader_manager = get_trader_manager()
        active_traders = len(trader_manager.get_active_traders())

        # Статистика сделок за сегодня
        trading_stats = await get_trading_stats_today()

        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            network_connections=network_connections,
            active_traders=active_traders,
            total_trades_today=trading_stats.get("total_trades", 0),
            last_updated=datetime.now(),
        )

        logger.debug(
            "Получены системные метрики",
            extra={
                "cpu": cpu_percent,
                "memory": memory.percent,
                "active_traders": active_traders,
            },
        )

        return metrics

    except Exception as e:
        logger.error(f"Ошибка получения системных метрик: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения метрик: {e!s}")


@router.get("/trading-stats", response_model=TradingStats)
async def get_trading_statistics(
    period: str = Query("24h", description="Период статистики (1h, 24h, 7d, 30d)"),
):
    """Получить статистику торговли за период"""
    try:
        # Определяем временной диапазон
        now = datetime.now()
        if period == "1h":
            start_time = now - timedelta(hours=1)
        elif period == "24h":
            start_time = now - timedelta(hours=24)
        elif period == "7d":
            start_time = now - timedelta(days=7)
        elif period == "30d":
            start_time = now - timedelta(days=30)
        else:
            raise HTTPException(status_code=400, detail=f"Неподдерживаемый период: {period}")

        # Получаем статистику из базы данных
        stats_service = get_stats_service()
        trading_data = await stats_service.get_trading_stats(start_time, now)

        stats = TradingStats(
            total_trades=trading_data["total_trades"],
            successful_trades=trading_data["successful_trades"],
            failed_trades=trading_data["failed_trades"],
            total_pnl=trading_data["total_pnl"],
            success_rate=trading_data["success_rate"],
            average_trade_duration=trading_data["avg_duration"],
            period=period,
        )

        logger.info(
            f"Получена статистика торговли за {period}",
            extra={
                "total_trades": stats.total_trades,
                "success_rate": stats.success_rate,
                "total_pnl": stats.total_pnl,
            },
        )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статистики торговли: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {e!s}")


@router.get("/alerts", response_model=list[Alert])
async def get_alerts(
    level: str | None = Query(None, description="Фильтр по уровню"),
    unresolved_only: bool = Query(True, description="Только нерешенные алерты"),
    limit: int = Query(50, description="Количество алертов"),
):
    """Получить список системных алертов"""
    try:
        alerts_service = get_alerts_service()

        filters = {}
        if level:
            filters["level"] = level
        if unresolved_only:
            filters["resolved"] = False

        alerts_data = await alerts_service.get_alerts(filters, limit)

        alerts = []
        for alert_data in alerts_data:
            alert = Alert(
                id=alert_data["id"],
                level=alert_data["level"],
                component=alert_data["component"],
                message=alert_data["message"],
                timestamp=alert_data["timestamp"],
                resolved=alert_data["resolved"],
            )
            alerts.append(alert)

        logger.info(
            f"Получено {len(alerts)} алертов",
            extra={"filters": filters, "count": len(alerts)},
        )

        return alerts

    except Exception as e:
        logger.error(f"Ошибка получения алертов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения алертов: {e!s}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Отметить алерт как решенный"""
    try:
        alerts_service = get_alerts_service()
        success = await alerts_service.resolve_alert(alert_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Алерт {alert_id} не найден")

        logger.info(f"Алерт {alert_id} отмечен как решенный")

        return {"status": "success", "message": f"Алерт {alert_id} решен"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка решения алерта {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка решения алерта: {e!s}")


@router.get("/exchanges", response_model=list[ExchangeStatus])
async def get_exchanges_status():
    """Получить статус всех подключенных бирж"""
    try:
        exchange_manager = get_exchange_manager()
        exchanges_data = await exchange_manager.get_all_exchanges_status()

        statuses = []
        for exchange_name, data in exchanges_data.items():
            status = ExchangeStatus(
                exchange=exchange_name,
                status=data["status"],
                latency_ms=data.get("latency_ms"),
                last_heartbeat=data.get("last_heartbeat"),
                api_calls_count=data.get("api_calls_count", 0),
                error_rate=data.get("error_rate", 0.0),
            )
            statuses.append(status)

        logger.info(f"Получен статус {len(statuses)} бирж")

        return statuses

    except Exception as e:
        logger.error(f"Ошибка получения статуса бирж: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса бирж: {e!s}")


@router.get("/performance", response_model=dict[str, Any])
async def get_performance_overview(
    period: str = Query("24h", description="Период анализа"),
):
    """Получить общий обзор производительности системы"""
    try:
        # Агрегированная статистика по всем трейдерам
        trader_manager = get_trader_manager()
        performance_data = await trader_manager.get_aggregated_performance(period)

        # Добавляем системные метрики
        system_metrics = await get_system_metrics()

        overview = {
            "period": period,
            "timestamp": datetime.now(),
            "trading": {
                "total_pnl": performance_data.get("total_pnl", 0.0),
                "success_rate": performance_data.get("success_rate", 0.0),
                "active_traders": performance_data.get("active_traders", 0),
                "total_trades": performance_data.get("total_trades", 0),
                "best_performer": performance_data.get("best_trader"),
                "worst_performer": performance_data.get("worst_trader"),
            },
            "system": {
                "cpu_usage": system_metrics.cpu_percent,
                "memory_usage": system_metrics.memory_percent,
                "uptime_hours": (
                    system_metrics.uptime_seconds / 3600
                    if hasattr(system_metrics, "uptime_seconds")
                    else 0
                ),
            },
            "exchanges": await get_exchange_performance_summary(),
        }

        logger.info(f"Получен обзор производительности за {period}")

        return overview

    except Exception as e:
        logger.error(f"Ошибка получения обзора производительности: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения обзора: {e!s}")


@router.get("/logs", response_model=list[dict[str, Any]])
async def get_system_logs(
    component: str | None = Query(None, description="Фильтр по компоненту"),
    level: str | None = Query(None, description="Уровень логирования"),
    limit: int = Query(100, description="Количество записей"),
    search: str | None = Query(None, description="Поиск по тексту"),
):
    """Получить системные логи"""
    try:
        logs_service = get_logs_service()

        filters = {}
        if component:
            filters["component"] = component
        if level:
            filters["level"] = level
        if search:
            filters["search"] = search

        logs = await logs_service.get_logs(filters, limit)

        logger.info(
            f"Получено {len(logs)} записей логов",
            extra={"filters": filters, "count": len(logs)},
        )

        return logs

    except Exception as e:
        logger.error(f"Ошибка получения логов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения логов: {e!s}")


# =================== HELPER FUNCTIONS ===================


async def get_trading_stats_today():
    """Получить статистику торговли за сегодня"""
    try:
        stats_service = get_stats_service()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now()

        stats = await stats_service.get_trading_stats(today_start, today_end)
        return stats
    except Exception as e:
        logger.error(f"Ошибка получения статистики за сегодня: {e}")
        return {"total_trades": 0}


async def get_exchange_performance_summary():
    """Получить краткую сводку по производительности бирж"""
    try:
        exchange_manager = get_exchange_manager()
        summary = await exchange_manager.get_performance_summary()
        return summary
    except Exception as e:
        logger.error(f"Ошибка получения сводки по биржам: {e}")
        return {}


# =================== DEPENDENCY INJECTION ===================


def get_health_checker():
    """Получить health_checker из глобального контекста"""
    from web.integration.dependencies import get_health_checker_dependency

    return get_health_checker_dependency()


def get_trader_manager():
    """Получить trader_manager из глобального контекста"""
    from web.integration.dependencies import get_trader_manager_dependency

    return get_trader_manager_dependency()


def get_orchestrator():
    """Получить orchestrator из глобального контекста"""
    from web.integration.dependencies import get_orchestrator_dependency

    return get_orchestrator_dependency()


def get_stats_service():
    """Получить stats_service из глобального контекста"""
    from web.integration.dependencies import get_stats_service_dependency

    return get_stats_service_dependency()


def get_alerts_service():
    """Получить alerts_service из глобального контекста"""
    from web.integration.dependencies import get_alerts_service_dependency

    return get_alerts_service_dependency()


def get_exchange_manager():
    """Получить exchange_manager из глобального контекста"""
    from web.integration.dependencies import get_exchange_manager_dependency

    return get_exchange_manager_dependency()


def get_logs_service():
    """Получить logs_service из глобального контекста"""
    from web.integration.dependencies import get_logs_service_dependency

    return get_logs_service_dependency()
