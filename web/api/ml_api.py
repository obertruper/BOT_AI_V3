#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API endpoints для ML сигналов
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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

    id: Optional[int] = None
    symbol: str
    exchange: str
    signal_type: str
    confidence: float
    strength: float
    timestamp: str
    strategy_name: str = "PatchTST_ML"
    suggested_price: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    extra_data: Optional[Dict[str, Any]] = None


class MLMetricsResponse(BaseModel):
    """Метрики ML системы"""

    total_processed: int
    success_rate: float
    save_rate: float
    error_rate: float
    active_symbols: List[str]
    last_signal_time: Optional[str] = None


@router.get("/signals/latest", response_model=List[MLSignalResponse])
async def get_latest_ml_signals(
    limit: int = Query(default=10, ge=1, le=100),
    symbol: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default="bybit"),
    db: AsyncSession = Depends(get_db),
) -> List[MLSignalResponse]:
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
        query = select(Signal).where(
            Signal.strategy_name.in_(["PatchTST_ML", "PatchTST_RealTime"])
        )

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
                    timestamp=signal.created_at.isoformat()
                    if signal.created_at
                    else "",
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


@router.get("/signals/active", response_model=List[MLSignalResponse])
async def get_active_ml_signals(
    symbol: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default="bybit"),
    db: AsyncSession = Depends(get_db),
) -> List[MLSignalResponse]:
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
                    timestamp=signal.created_at.isoformat()
                    if signal.created_at
                    else "",
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
            last_signal_time=last_signal.created_at.isoformat()
            if last_signal
            else None,
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
            raise HTTPException(
                status_code=400, detail="ML Signal Scheduler не инициализирован"
            )

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
            raise HTTPException(
                status_code=400, detail="ML Signal Scheduler не инициализирован"
            )

        await orchestrator.signal_scheduler.stop()

        return {"status": "stopped", "message": "ML Signal Scheduler остановлен"}

    except Exception as e:
        logger.error(f"Ошибка остановки scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))
