"""
API эндпоинты для отслеживания позиций

Предоставляет данные из Enhanced Position Tracker
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.logger import setup_logger
from trading.position_tracker import get_position_tracker

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/positions", tags=["position-tracking"])


class PositionResponse(BaseModel):
    """Модель ответа позиции"""

    position_id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str
    health: str
    unrealized_pnl: float
    roi_percent: float
    hold_time_minutes: int
    exchange: str
    created_at: datetime
    updated_at: datetime


class PositionMetricsResponse(BaseModel):
    """Модель метрик позиции"""

    position_id: str
    unrealized_pnl: float
    realized_pnl: float
    roi_percent: float
    hold_time_minutes: int
    max_profit: float
    max_drawdown: float
    health_score: float
    last_updated: datetime


class TrackerStatsResponse(BaseModel):
    """Модель статистики трекера"""

    total_tracked: int
    active_positions: int
    updates_count: int
    sync_errors: int
    last_update: Optional[datetime]
    health_distribution: Dict[str, int]
    total_unrealized_pnl: float
    avg_hold_time: float
    is_running: bool


@router.get("/active", response_model=List[PositionResponse])
async def get_active_positions():
    """Получить все активные позиции"""

    try:
        tracker = await get_position_tracker()
        positions = await tracker.get_active_positions()

        result = []
        for pos in positions:
            metrics = pos.metrics or {}
            result.append(
                PositionResponse(
                    position_id=pos.position_id,
                    symbol=pos.symbol,
                    side=pos.side,
                    size=float(pos.size),
                    entry_price=float(pos.entry_price),
                    current_price=float(pos.current_price),
                    stop_loss=float(pos.stop_loss) if pos.stop_loss else None,
                    take_profit=float(pos.take_profit) if pos.take_profit else None,
                    status=pos.status.value,
                    health=pos.health.value,
                    unrealized_pnl=float(getattr(metrics, "unrealized_pnl", 0)),
                    roi_percent=float(getattr(metrics, "roi_percent", 0)),
                    hold_time_minutes=getattr(metrics, "hold_time_minutes", 0),
                    exchange=pos.exchange,
                    created_at=pos.created_at,
                    updated_at=pos.updated_at,
                )
            )

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка получения активных позиций: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-symbol/{symbol}", response_model=List[PositionResponse])
async def get_positions_by_symbol(symbol: str):
    """Получить позиции по символу"""

    try:
        tracker = await get_position_tracker()
        positions = await tracker.get_positions_by_symbol(symbol.upper())

        result = []
        for pos in positions:
            metrics = pos.metrics or {}
            result.append(
                PositionResponse(
                    position_id=pos.position_id,
                    symbol=pos.symbol,
                    side=pos.side,
                    size=float(pos.size),
                    entry_price=float(pos.entry_price),
                    current_price=float(pos.current_price),
                    stop_loss=float(pos.stop_loss) if pos.stop_loss else None,
                    take_profit=float(pos.take_profit) if pos.take_profit else None,
                    status=pos.status.value,
                    health=pos.health.value,
                    unrealized_pnl=float(getattr(metrics, "unrealized_pnl", 0)),
                    roi_percent=float(getattr(metrics, "roi_percent", 0)),
                    hold_time_minutes=getattr(metrics, "hold_time_minutes", 0),
                    exchange=pos.exchange,
                    created_at=pos.created_at,
                    updated_at=pos.updated_at,
                )
            )

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка получения позиций для {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(position_id: str):
    """Получить конкретную позицию"""

    try:
        tracker = await get_position_tracker()
        position = await tracker.get_position(position_id)

        if not position:
            raise HTTPException(status_code=404, detail="Позиция не найдена")

        metrics = position.metrics or {}

        return PositionResponse(
            position_id=position.position_id,
            symbol=position.symbol,
            side=position.side,
            size=float(position.size),
            entry_price=float(position.entry_price),
            current_price=float(position.current_price),
            stop_loss=float(position.stop_loss) if position.stop_loss else None,
            take_profit=float(position.take_profit) if position.take_profit else None,
            status=position.status.value,
            health=position.health.value,
            unrealized_pnl=float(getattr(metrics, "unrealized_pnl", 0)),
            roi_percent=float(getattr(metrics, "roi_percent", 0)),
            hold_time_minutes=getattr(metrics, "hold_time_minutes", 0),
            exchange=position.exchange,
            created_at=position.created_at,
            updated_at=position.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения позиции {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{position_id}/metrics", response_model=PositionMetricsResponse)
async def get_position_metrics(position_id: str):
    """Получить метрики конкретной позиции"""

    try:
        tracker = await get_position_tracker()
        position = await tracker.get_position(position_id)

        if not position or not position.metrics:
            raise HTTPException(status_code=404, detail="Позиция или её метрики не найдены")

        metrics = position.metrics

        return PositionMetricsResponse(
            position_id=position_id,
            unrealized_pnl=float(metrics.unrealized_pnl),
            realized_pnl=float(metrics.realized_pnl),
            roi_percent=float(metrics.roi_percent),
            hold_time_minutes=metrics.hold_time_minutes,
            max_profit=float(metrics.max_profit),
            max_drawdown=float(metrics.max_drawdown),
            health_score=metrics.health_score,
            last_updated=metrics.last_updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения метрик позиции {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{position_id}/update")
async def update_position_metrics(position_id: str):
    """Принудительно обновить метрики позиции"""

    try:
        tracker = await get_position_tracker()
        success = await tracker.update_position_metrics(position_id)

        if not success:
            raise HTTPException(status_code=404, detail="Позиция не найдена или ошибка обновления")

        return {"status": "success", "message": f"Метрики позиции {position_id} обновлены"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка обновления метрик позиции {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{position_id}/sync")
async def sync_position_with_exchange(position_id: str):
    """Синхронизировать позицию с биржей"""

    try:
        tracker = await get_position_tracker()
        success = await tracker.sync_with_exchange(position_id)

        if not success:
            raise HTTPException(
                status_code=404, detail="Позиция не найдена или ошибка синхронизации"
            )

        return {"status": "success", "message": f"Позиция {position_id} синхронизирована с биржей"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации позиции {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/tracker", response_model=TrackerStatsResponse)
async def get_tracker_stats():
    """Получить общую статистику трекера позиций"""

    try:
        tracker = await get_position_tracker()
        stats = await tracker.get_tracker_stats()

        return TrackerStatsResponse(**stats)

    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики трекера: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/pnl")
async def get_pnl_stats(
    symbol: Optional[str] = Query(None, description="Фильтр по символу"),
    hours: int = Query(24, description="Период в часах"),
):
    """Получить статистику PnL"""

    try:
        tracker = await get_position_tracker()

        # Получаем активные позиции
        if symbol:
            positions = await tracker.get_positions_by_symbol(symbol.upper())
        else:
            positions = await tracker.get_active_positions()

        # Фильтруем по времени
        cutoff_time = datetime.now() - timedelta(hours=hours)
        filtered_positions = [pos for pos in positions if pos.created_at >= cutoff_time]

        # Считаем статистику
        total_unrealized_pnl = sum(
            float(pos.metrics.unrealized_pnl) for pos in filtered_positions if pos.metrics
        )

        total_positions = len(filtered_positions)

        winning_positions = sum(
            1 for pos in filtered_positions if pos.metrics and float(pos.metrics.unrealized_pnl) > 0
        )

        losing_positions = sum(
            1 for pos in filtered_positions if pos.metrics and float(pos.metrics.unrealized_pnl) < 0
        )

        avg_roi = sum(
            float(pos.metrics.roi_percent) for pos in filtered_positions if pos.metrics
        ) / max(total_positions, 1)

        return {
            "period_hours": hours,
            "symbol_filter": symbol,
            "total_positions": total_positions,
            "total_unrealized_pnl": total_unrealized_pnl,
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "win_rate": winning_positions / max(total_positions, 1) * 100,
            "avg_roi_percent": avg_roi,
            "best_position": max(
                (float(pos.metrics.unrealized_pnl) for pos in filtered_positions if pos.metrics),
                default=0,
            ),
            "worst_position": min(
                (float(pos.metrics.unrealized_pnl) for pos in filtered_positions if pos.metrics),
                default=0,
            ),
        }

    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики PnL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
