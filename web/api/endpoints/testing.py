"""
API эндпоинты для тестирования системы
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.logger import setup_logger
from database.models.base_models import SignalType
from database.models.signal import Signal
from database.repositories.signal_repository_fixed import SignalRepositoryFixed

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/testing", tags=["testing"])


class TestSignalRequest(BaseModel):
    """Запрос на создание тестового сигнала"""

    symbol: str = "BTCUSDT"
    signal_type: str = "LONG"
    exchange: str = "bybit"
    confidence: float = 0.85


class TestPositionRequest(BaseModel):
    """Запрос на создание тестовой позиции"""

    symbol: str = "BTCUSDT"
    side: str = "long"
    size: float = 0.001
    entry_price: float = 50000.0
    stop_loss: Optional[float] = 49000.0
    take_profit: Optional[float] = 52000.0


@router.post("/generate-test-signal")
async def generate_test_signal(request: TestSignalRequest = TestSignalRequest()):
    """Создать тестовый сигнал для проверки системы"""

    try:
        # Создаем тестовый сигнал
        signal = Signal(
            symbol=request.symbol,
            signal_type=SignalType[request.signal_type.upper()],
            price=Decimal("50000.0"),  # Тестовая цена
            confidence=request.confidence,
            exchange=request.exchange,
            metadata={
                "test": True,
                "source": "testing_endpoint",
                "features_count": 240,
                "model_version": "test_v1.0",
            },
        )

        # Сохраняем в БД
        from database.connections.postgres import get_async_db
        async with get_async_db() as db:
            signal_repo = SignalRepositoryFixed(db)
            saved_signal = await signal_repo.save_signal(signal)

        if saved_signal:
            logger.info(f"✅ Создан тестовый сигнал: {signal.symbol} {signal.signal_type.value}")

            return {
                "success": True,
                "message": "Тестовый сигнал создан успешно",
                "signal": {
                    "id": saved_signal.id,
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type.value,
                    "price": float(signal.price),
                    "confidence": signal.confidence,
                    "exchange": signal.exchange,
                    "created_at": signal.created_at.isoformat(),
                },
            }
        else:
            raise Exception("Ошибка сохранения сигнала")

    except Exception as e:
        logger.error(f"❌ Ошибка создания тестового сигнала: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-test-position")
async def create_test_position(request: TestPositionRequest = TestPositionRequest()):
    """Создать тестовую позицию в Position Tracker"""

    try:
        from trading.position_tracker import get_position_tracker

        tracker = await get_position_tracker()

        # Создаем уникальный ID для тестовой позиции
        position_id = f"test_{request.symbol}_{request.side}_{int(datetime.now().timestamp())}"

        # Добавляем позицию в отслеживание
        position = await tracker.track_position(
            position_id=position_id,
            symbol=request.symbol,
            side=request.side,
            size=Decimal(str(request.size)),
            entry_price=Decimal(str(request.entry_price)),
            stop_loss=Decimal(str(request.stop_loss)) if request.stop_loss else None,
            take_profit=Decimal(str(request.take_profit)) if request.take_profit else None,
            exchange="bybit",
        )

        logger.info(f"✅ Создана тестовая позиция: {position_id}")

        return {
            "success": True,
            "message": "Тестовая позиция создана успешно",
            "position": {
                "position_id": position.position_id,
                "symbol": position.symbol,
                "side": position.side,
                "size": float(position.size),
                "entry_price": float(position.entry_price),
                "stop_loss": float(position.stop_loss) if position.stop_loss else None,
                "take_profit": float(position.take_profit) if position.take_profit else None,
                "status": position.status.value,
                "health": position.health.value,
                "created_at": position.created_at.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"❌ Ошибка создания тестовой позиции: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position-tracker-status")
async def get_position_tracker_status():
    """Получить статус Position Tracker"""

    try:
        from trading.position_tracker import get_position_tracker

        tracker = await get_position_tracker()
        stats = await tracker.get_tracker_stats()

        return {
            "success": True,
            "tracker_stats": stats,
            "message": (
                "Position Tracker работает"
                if stats.get("is_running")
                else "Position Tracker не запущен"
            ),
        }

    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса Position Tracker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup-test-positions")
async def cleanup_test_positions():
    """Очистить все тестовые позиции"""

    try:
        from trading.position_tracker import get_position_tracker

        tracker = await get_position_tracker()

        # Получаем все позиции
        positions = await tracker.get_active_positions()

        # Удаляем тестовые позиции (начинаются с "test_")
        deleted_count = 0
        for position in positions:
            if position.position_id.startswith("test_"):
                await tracker.remove_position(position.position_id, "cleanup")
                deleted_count += 1

        return {
            "success": True,
            "message": f"Удалено {deleted_count} тестовых позиций",
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка очистки тестовых позиций: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-health")
async def get_system_health():
    """Проверить состояние основных компонентов системы"""

    try:
        health_status = {"timestamp": datetime.now().isoformat(), "components": {}}

        # Проверяем Position Tracker
        try:
            from trading.position_tracker import get_position_tracker

            tracker = await get_position_tracker()
            stats = await tracker.get_tracker_stats()
            health_status["components"]["position_tracker"] = {
                "status": "healthy" if stats.get("is_running") else "warning",
                "active_positions": stats.get("active_positions", 0),
                "updates_count": stats.get("updates_count", 0),
            }
        except Exception as e:
            health_status["components"]["position_tracker"] = {"status": "error", "error": str(e)}

        # Проверяем базу данных
        try:
            from database.connections.postgres import get_async_db
            async with get_async_db() as db:
                signal_repo = SignalRepositoryFixed(db)
                # Простой запрос для проверки БД - получаем активные сигналы
                active_signals = await signal_repo.get_active_signals()
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "active_signals_count": len(active_signals),
                }
        except Exception as e:
            health_status["components"]["database"] = {"status": "error", "error": str(e)}

        # Общий статус
        all_healthy = all(
            comp.get("status") == "healthy" for comp in health_status["components"].values()
        )

        health_status["overall_status"] = "healthy" if all_healthy else "degraded"

        return health_status

    except Exception as e:
        logger.error(f"❌ Ошибка проверки состояния системы: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml-pipeline-test")
async def test_ml_pipeline():
    """Протестировать ML pipeline генерации сигналов"""

    try:
        # Проверяем, доступен ли ML Manager
        ml_status = {"timestamp": datetime.now().isoformat(), "ml_components": {}}

        try:
            from ml.ml_manager import MLManager
            from core.config.config_manager import ConfigManager

            config_manager = ConfigManager()
            ml_manager = MLManager(config_manager)

            ml_status["ml_components"]["ml_manager"] = {
                "status": "available",
                "message": "MLManager доступен",
            }

        except Exception as e:
            ml_status["ml_components"]["ml_manager"] = {"status": "error", "error": str(e)}

        return ml_status

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования ML pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))
