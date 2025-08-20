#!/usr/bin/env python3
"""
API endpoints для ML сигналов
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import setup_logger
from database.connections.postgres import AsyncSessionLocal
from database.models.signal import Signal

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/ml", tags=["ML Signals"])


async def get_db():
    """Dependency для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class MLSignalResponse(BaseModel):
    """Модель ответа для ML сигнала"""

    id: int | None = None
    symbol: str
    exchange: str
    signal_type: str
    confidence: float
    strength: float
    timestamp: str
    strategy_name: str = "PatchTST_ML"
    suggested_price: float | None = None
    suggested_stop_loss: float | None = None
    suggested_take_profit: float | None = None
    extra_data: dict[str, Any] | None = None


class MLMetricsResponse(BaseModel):
    """Метрики ML системы"""

    total_processed: int
    success_rate: float
    save_rate: float
    error_rate: float
    active_symbols: list[str]
    last_signal_time: str | None = None


class MLCacheMetricsResponse(BaseModel):
    """Метрики кэша ML системы"""

    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    cache_size: int
    unique_symbols_processed: int
    symbols_list: list[str]
    cache_ttl_seconds: int
    last_cleanup: str


class MLDirectionStatsResponse(BaseModel):
    """Статистика распределения направлений ML"""

    total_predictions: int
    long_count: int
    short_count: int
    flat_count: int
    long_percentage: float
    short_percentage: float
    flat_percentage: float
    last_hour_distribution: dict[str, int]
    confidence_by_direction: dict[str, float]


@router.get("/signals/recent", response_model=list[MLSignalResponse])
async def get_recent_ml_signals(
    limit: int = Query(10, description="Количество сигналов"),
    symbol: str = Query(None, description="Фильтр по символу"),
    db: AsyncSession = Depends(get_db)
) -> list[MLSignalResponse]:
    """
    Получить последние ML сигналы (alias для latest для совместимости с фронтендом)
    """
    return await get_latest_ml_signals(limit=limit, symbol=symbol, db=db)


@router.get("/signals/latest", response_model=list[MLSignalResponse])
async def get_latest_ml_signals(
    limit: int = Query(default=10, ge=1, le=100),
    symbol: str | None = Query(default=None),
    exchange: str | None = Query(default="bybit"),
    db: AsyncSession = Depends(get_db),
) -> list[MLSignalResponse]:
    """
    Получение последних ML сигналов

    Args:
        limit: Количество сигналов
        symbol: Фильтр по символу
        exchange: Фильтр по бирже

    Returns:
        Список последних ML сигналов
    """
    try:
        # Формируем запрос
        query = select(Signal).where(Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"]))

        if symbol:
            query = query.where(Signal.symbol == symbol)
        if exchange:
            query = query.where(Signal.exchange == exchange)

        # Добавляем сортировку и лимит
        query = query.order_by(desc(Signal.created_at)).limit(limit)

        # Выполняем запрос
        result = await db.execute(query)
        signals = result.scalars().all()

        # Конвертируем в ответ
        response = []
        for signal in signals:
            response.append(
                MLSignalResponse(
                    id=signal.id,
                    symbol=signal.symbol,
                    exchange=signal.exchange,
                    signal_type=signal.signal_type.value,
                    confidence=signal.confidence,
                    strength=signal.strength,
                    timestamp=signal.created_at.isoformat() if signal.created_at else "",
                    strategy_name=signal.strategy_name,
                    suggested_price=signal.suggested_price,
                    suggested_stop_loss=signal.suggested_stop_loss,
                    suggested_take_profit=signal.suggested_take_profit,
                    extra_data=signal.extra_data,
                )
            )

        return response

    except Exception as e:
        logger.error(f"Ошибка получения ML сигналов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/active", response_model=list[MLSignalResponse])
async def get_active_ml_signals(
    symbol: str | None = Query(default=None),
    exchange: str | None = Query(default="bybit"),
    db: AsyncSession = Depends(get_db),
) -> list[MLSignalResponse]:
    """
    Получение активных ML сигналов (не старше 10 минут)
    """
    try:
        # Время истечения - 10 минут назад
        expiry_time = datetime.utcnow() - timedelta(minutes=10)

        # Формируем запрос
        query = select(Signal).where(
            and_(
                Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"]),
                Signal.created_at >= expiry_time,
            )
        )

        if symbol:
            query = query.where(Signal.symbol == symbol)
        if exchange:
            query = query.where(Signal.exchange == exchange)

        # Выполняем запрос
        result = await db.execute(query)
        signals = result.scalars().all()

        # Конвертируем в ответ
        response = []
        for signal in signals:
            response.append(
                MLSignalResponse(
                    id=signal.id,
                    symbol=signal.symbol,
                    exchange=signal.exchange,
                    signal_type=signal.signal_type.value,
                    confidence=signal.confidence,
                    strength=signal.strength,
                    timestamp=signal.created_at.isoformat() if signal.created_at else "",
                    strategy_name=signal.strategy_name,
                    suggested_price=signal.suggested_price,
                    suggested_stop_loss=signal.suggested_stop_loss,
                    suggested_take_profit=signal.suggested_take_profit,
                    extra_data=signal.extra_data,
                )
            )

        return response

    except Exception as e:
        logger.error(f"Ошибка получения активных ML сигналов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MLMetricsResponse)
async def get_ml_metrics(db: AsyncSession = Depends(get_db)) -> MLMetricsResponse:
    """
    Получение метрик ML системы
    """
    try:
        # Получаем статистику из БД
        # Всего сигналов
        total_query = select(Signal).where(
            Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"])
        )
        total_result = await db.execute(total_query)
        total_signals = len(total_result.scalars().all())

        # Сигналы за последний час
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_query = select(Signal).where(
            and_(
                Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"]),
                Signal.created_at >= hour_ago,
            )
        )
        recent_result = await db.execute(recent_query)
        recent_signals = recent_result.scalars().all()

        # Уникальные символы
        symbols_query = (
            select(Signal.symbol)
            .where(Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"]))
            .distinct()
        )
        symbols_result = await db.execute(symbols_query)
        active_symbols = [s for s in symbols_result.scalars().all()]

        # Последний сигнал
        last_signal = None
        if recent_signals:
            last_signal = max(recent_signals, key=lambda s: s.created_at)

        # Считаем метрики
        success_rate = 0.0
        if recent_signals:
            successful = len([s for s in recent_signals if s.confidence > 0.65])
            success_rate = successful / len(recent_signals)

        return MLMetricsResponse(
            total_processed=total_signals,
            success_rate=success_rate,
            save_rate=1.0,  # Все сигналы сохраняются
            error_rate=0.0,  # Пока не отслеживаем
            active_symbols=active_symbols,
            last_signal_time=last_signal.created_at.isoformat() if last_signal else None,
        )

    except Exception as e:
        logger.error(f"Ошибка получения метрик ML: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def get_scheduler_status():
    """
    Получение статуса ML Signal Scheduler
    """
    try:
        # Получаем оркестратор
        from core.config.config_manager import get_global_config_manager
        from core.system.orchestrator import SystemOrchestrator

        orchestrator = SystemOrchestrator(get_global_config_manager())

        if not orchestrator.signal_scheduler:
            return {
                "status": "not_initialized",
                "message": "ML Signal Scheduler не инициализирован",
            }

        # Получаем статус
        status = await orchestrator.signal_scheduler.get_status()

        return {
            "status": "running" if status.get("running") else "stopped",
            "enabled": status.get("enabled"),
            "interval_seconds": status.get("interval_seconds"),
            "symbols": status.get("symbols", {}),
            "processor_stats": status.get("processor_stats", {}),
        }

    except Exception as e:
        logger.error(f"Ошибка получения статуса scheduler: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/scheduler/start")
async def start_scheduler():
    """Запуск ML Signal Scheduler"""
    try:
        from core.config.config_manager import get_global_config_manager
        from core.system.orchestrator import SystemOrchestrator

        orchestrator = SystemOrchestrator(get_global_config_manager())

        if not orchestrator.signal_scheduler:
            raise HTTPException(status_code=400, detail="ML Signal Scheduler не инициализирован")

        await orchestrator.signal_scheduler.start()

        return {"status": "started", "message": "ML Signal Scheduler запущен"}

    except Exception as e:
        logger.error(f"Ошибка запуска scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Остановка ML Signal Scheduler"""
    try:
        from core.config.config_manager import get_global_config_manager
        from core.system.orchestrator import SystemOrchestrator

        orchestrator = SystemOrchestrator(get_global_config_manager())

        if not orchestrator.signal_scheduler:
            raise HTTPException(status_code=400, detail="ML Signal Scheduler не инициализирован")

        await orchestrator.signal_scheduler.stop()

        return {"status": "stopped", "message": "ML Signal Scheduler остановлен"}

    except Exception as e:
        logger.error(f"Ошибка остановки scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache-stats", response_model=MLCacheMetricsResponse)
async def get_ml_cache_stats() -> MLCacheMetricsResponse:
    """
    Получение статистики кэша ML системы
    """
    try:
        # Получаем ML Signal Processor для доступа к кэшу
        from ml.ml_signal_processor import MLSignalProcessor
        
        processor = MLSignalProcessor()
        
        # Получаем метрики кэша
        cache_stats = processor.get_cache_stats()
        
        # Вычисляем hit rate
        total_requests = cache_stats.get('cache_hits', 0) + cache_stats.get('cache_misses', 0)
        hit_rate = cache_stats.get('cache_hits', 0) / total_requests if total_requests > 0 else 0.0
        
        # Получаем уникальные символы
        symbols = list(cache_stats.get('symbols', set()))
        
        return MLCacheMetricsResponse(
            cache_hits=cache_stats.get('cache_hits', 0),
            cache_misses=cache_stats.get('cache_misses', 0),
            cache_hit_rate=hit_rate,
            cache_size=cache_stats.get('cache_size', 0),
            unique_symbols_processed=len(symbols),
            symbols_list=symbols,
            cache_ttl_seconds=cache_stats.get('ttl_seconds', 300),
            last_cleanup=cache_stats.get('last_cleanup', datetime.utcnow().isoformat())
        )

    except Exception as e:
        logger.error(f"Ошибка получения статистики кэша: {e}")
        # Возвращаем пустые данные вместо ошибки
        return MLCacheMetricsResponse(
            cache_hits=0,
            cache_misses=0,
            cache_hit_rate=0.0,
            cache_size=0,
            unique_symbols_processed=0,
            symbols_list=[],
            cache_ttl_seconds=300,
            last_cleanup=datetime.utcnow().isoformat()
        )


@router.get("/direction-stats", response_model=MLDirectionStatsResponse)
async def get_ml_direction_stats(
    hours: int = Query(default=24, ge=1, le=168),  # От 1 до 168 часов (неделя)
    db: AsyncSession = Depends(get_db)
) -> MLDirectionStatsResponse:
    """
    Получение статистики распределения направлений ML предсказаний
    """
    try:
        # Временной диапазон
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        hour_threshold = datetime.utcnow() - timedelta(hours=1)
        
        # Запрос всех ML сигналов за период
        query = select(Signal).where(
            and_(
                Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"]),
                Signal.created_at >= time_threshold,
            )
        )
        
        result = await db.execute(query)
        all_signals = result.scalars().all()
        
        # Запрос сигналов за последний час
        hour_query = select(Signal).where(
            and_(
                Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"]),
                Signal.created_at >= hour_threshold,
            )
        )
        
        hour_result = await db.execute(hour_query)
        hour_signals = hour_result.scalars().all()
        
        # Подсчет общих статистик
        total_predictions = len(all_signals)
        
        if total_predictions == 0:
            return MLDirectionStatsResponse(
                total_predictions=0,
                long_count=0,
                short_count=0,
                flat_count=0,
                long_percentage=0.0,
                short_percentage=0.0,
                flat_percentage=0.0,
                last_hour_distribution={"LONG": 0, "SHORT": 0, "FLAT": 0},
                confidence_by_direction={"LONG": 0.0, "SHORT": 0.0, "FLAT": 0.0}
            )
        
        # Подсчет по типам сигналов
        long_signals = [s for s in all_signals if s.signal_type.value in ['LONG', 'buy']]
        short_signals = [s for s in all_signals if s.signal_type.value in ['SHORT', 'sell']]
        flat_signals = [s for s in all_signals if s.signal_type.value in ['FLAT', 'NEUTRAL', 'hold']]
        
        long_count = len(long_signals)
        short_count = len(short_signals)
        flat_count = len(flat_signals)
        
        # Проценты
        long_percentage = (long_count / total_predictions) * 100
        short_percentage = (short_count / total_predictions) * 100
        flat_percentage = (flat_count / total_predictions) * 100
        
        # Распределение за последний час
        hour_long = len([s for s in hour_signals if s.signal_type.value in ['LONG', 'buy']])
        hour_short = len([s for s in hour_signals if s.signal_type.value in ['SHORT', 'sell']])
        hour_flat = len([s for s in hour_signals if s.signal_type.value in ['FLAT', 'NEUTRAL', 'hold']])
        
        # Средняя уверенность по направлениям
        long_confidence = sum(s.confidence for s in long_signals) / len(long_signals) if long_signals else 0.0
        short_confidence = sum(s.confidence for s in short_signals) / len(short_signals) if short_signals else 0.0
        flat_confidence = sum(s.confidence for s in flat_signals) / len(flat_signals) if flat_signals else 0.0
        
        return MLDirectionStatsResponse(
            total_predictions=total_predictions,
            long_count=long_count,
            short_count=short_count,
            flat_count=flat_count,
            long_percentage=long_percentage,
            short_percentage=short_percentage,
            flat_percentage=flat_percentage,
            last_hour_distribution={
                "LONG": hour_long,
                "SHORT": hour_short,
                "FLAT": hour_flat
            },
            confidence_by_direction={
                "LONG": long_confidence,
                "SHORT": short_confidence,
                "FLAT": flat_confidence
            }
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики направлений: {e}")
        # Возвращаем пустые данные вместо ошибки
        return MLDirectionStatsResponse(
            total_predictions=0,
            long_count=0,
            short_count=0,
            flat_count=0,
            long_percentage=0.0,
            short_percentage=0.0,
            flat_percentage=0.0,
            last_hour_distribution={"LONG": 0, "SHORT": 0, "FLAT": 0},
            confidence_by_direction={"LONG": 0.0, "SHORT": 0.0, "FLAT": 0.0}
        )
