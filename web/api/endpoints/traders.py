"""
Traders API Endpoints

REST API для управления трейдерами:
- Создание/удаление трейдеров
- Запуск/остановка торговли
- Мониторинг состояния
- Конфигурация параметров
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("traders_api", component="web_api")

router = APIRouter(prefix="/api/traders", tags=["traders"])

# =================== MODELS ===================


class TraderCreateRequest(BaseModel):
    """Запрос на создание трейдера"""

    trader_id: str
    exchange: str
    strategy: str
    symbol: str
    leverage: Optional[float] = None
    risk_balance: Optional[float] = None
    config_overrides: Optional[Dict[str, Any]] = None


class TraderResponse(BaseModel):
    """Ответ с информацией о трейдере"""

    trader_id: str
    exchange: str
    strategy: str
    symbol: str
    state: str
    is_trading: bool
    created_at: datetime
    last_activity: Optional[datetime] = None
    performance: Optional[Dict[str, Any]] = None
    current_position: Optional[Dict[str, Any]] = None


class TraderUpdateRequest(BaseModel):
    """Запрос на обновление трейдера"""

    leverage: Optional[float] = None
    risk_balance: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    config_updates: Optional[Dict[str, Any]] = None


class TradingActionRequest(BaseModel):
    """Запрос на торговое действие"""

    action: str  # start, stop, pause, resume
    force: bool = False


# =================== ENDPOINTS ===================


@router.get("/", response_model=List[TraderResponse])
async def get_traders(
    active_only: bool = Query(False, description="Только активные трейдеры"),
    exchange: Optional[str] = Query(None, description="Фильтр по бирже"),
    strategy: Optional[str] = Query(None, description="Фильтр по стратегии"),
):
    """Получить список всех трейдеров"""
    try:
        # Получаем trader_manager из dependency injection
        trader_manager = get_trader_manager()

        traders = trader_manager.get_all_traders()

        # Применяем фильтры
        filtered_traders = []
        for trader in traders:
            if active_only and not trader.is_active():
                continue
            if exchange and trader.exchange != exchange:
                continue
            if strategy and trader.strategy != strategy:
                continue

            # Конвертируем в response модель
            trader_response = TraderResponse(
                trader_id=trader.trader_id,
                exchange=trader.exchange,
                strategy=trader.strategy,
                symbol=trader.symbol,
                state=trader.state.value,
                is_trading=trader.is_trading(),
                created_at=trader.created_at,
                last_activity=trader.last_activity,
                performance=trader.get_performance_metrics(),
                current_position=trader.get_current_position(),
            )
            filtered_traders.append(trader_response)

        logger.info(
            f"Возвращено {len(filtered_traders)} трейдеров",
            extra={
                "total_count": len(traders),
                "filtered_count": len(filtered_traders),
                "filters": {
                    "active_only": active_only,
                    "exchange": exchange,
                    "strategy": strategy,
                },
            },
        )

        return filtered_traders

    except Exception as e:
        logger.error(f"Ошибка получения списка трейдеров: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка получения трейдеров: {str(e)}"
        )


@router.get("/{trader_id}", response_model=TraderResponse)
async def get_trader(trader_id: str):
    """Получить информацию о конкретном трейдере"""
    try:
        trader_manager = get_trader_manager()
        trader = trader_manager.get_trader(trader_id)

        if not trader:
            raise HTTPException(
                status_code=404, detail=f"Трейдер {trader_id} не найден"
            )

        trader_response = TraderResponse(
            trader_id=trader.trader_id,
            exchange=trader.exchange,
            strategy=trader.strategy,
            symbol=trader.symbol,
            state=trader.state.value,
            is_trading=trader.is_trading(),
            created_at=trader.created_at,
            last_activity=trader.last_activity,
            performance=trader.get_performance_metrics(),
            current_position=trader.get_current_position(),
        )

        logger.info(f"Получена информация о трейдере {trader_id}")
        return trader_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения трейдера {trader_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка получения трейдера: {str(e)}"
        )


@router.post("/", response_model=TraderResponse)
async def create_trader(request: TraderCreateRequest):
    """Создать новый трейдер"""
    try:
        trader_manager = get_trader_manager()

        # Проверяем что трейдер с таким ID не существует
        if trader_manager.get_trader(request.trader_id):
            raise HTTPException(
                status_code=400,
                detail=f"Трейдер с ID {request.trader_id} уже существует",
            )

        # Создаем конфигурацию трейдера
        trader_config = {
            "trader_id": request.trader_id,
            "exchange": request.exchange,
            "strategy": request.strategy,
            "symbol": request.symbol,
            "leverage": request.leverage,
            "risk_balance": request.risk_balance,
        }

        # Добавляем дополнительные настройки
        if request.config_overrides:
            trader_config.update(request.config_overrides)

        # Создаем трейдера
        trader = await trader_manager.create_trader(trader_config)

        trader_response = TraderResponse(
            trader_id=trader.trader_id,
            exchange=trader.exchange,
            strategy=trader.strategy,
            symbol=trader.symbol,
            state=trader.state.value,
            is_trading=trader.is_trading(),
            created_at=trader.created_at,
            last_activity=trader.last_activity,
            performance={},
            current_position=None,
        )

        logger.info(
            f"Создан новый трейдер {request.trader_id}",
            extra={"trader_config": trader_config},
        )

        return trader_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка создания трейдера {request.trader_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка создания трейдера: {str(e)}"
        )


@router.put("/{trader_id}", response_model=TraderResponse)
async def update_trader(trader_id: str, request: TraderUpdateRequest):
    """Обновить настройки трейдера"""
    try:
        trader_manager = get_trader_manager()
        trader = trader_manager.get_trader(trader_id)

        if not trader:
            raise HTTPException(
                status_code=404, detail=f"Трейдер {trader_id} не найден"
            )

        # Обновляем настройки
        updates = {}
        if request.leverage is not None:
            updates["leverage"] = request.leverage
        if request.risk_balance is not None:
            updates["risk_balance"] = request.risk_balance
        if request.stop_loss is not None:
            updates["stop_loss"] = request.stop_loss
        if request.take_profit is not None:
            updates["take_profit"] = request.take_profit
        if request.config_updates:
            updates.update(request.config_updates)

        # Применяем обновления
        await trader.update_config(updates)

        trader_response = TraderResponse(
            trader_id=trader.trader_id,
            exchange=trader.exchange,
            strategy=trader.strategy,
            symbol=trader.symbol,
            state=trader.state.value,
            is_trading=trader.is_trading(),
            created_at=trader.created_at,
            last_activity=trader.last_activity,
            performance=trader.get_performance_metrics(),
            current_position=trader.get_current_position(),
        )

        logger.info(
            f"Обновлены настройки трейдера {trader_id}", extra={"updates": updates}
        )

        return trader_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка обновления трейдера {trader_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка обновления трейдера: {str(e)}"
        )


@router.post("/{trader_id}/actions", response_model=Dict[str, Any])
async def trader_action(trader_id: str, request: TradingActionRequest):
    """Выполнить торговое действие с трейдером"""
    try:
        trader_manager = get_trader_manager()
        trader = trader_manager.get_trader(trader_id)

        if not trader:
            raise HTTPException(
                status_code=404, detail=f"Трейдер {trader_id} не найден"
            )

        result = {}

        if request.action == "start":
            await trader.start_trading()
            result = {
                "action": "start",
                "status": "success",
                "message": "Торговля запущена",
            }

        elif request.action == "stop":
            await trader.stop_trading(force=request.force)
            result = {
                "action": "stop",
                "status": "success",
                "message": "Торговля остановлена",
            }

        elif request.action == "pause":
            await trader.pause_trading()
            result = {
                "action": "pause",
                "status": "success",
                "message": "Торговля приостановлена",
            }

        elif request.action == "resume":
            await trader.resume_trading()
            result = {
                "action": "resume",
                "status": "success",
                "message": "Торговля возобновлена",
            }

        else:
            raise HTTPException(
                status_code=400, detail=f"Неизвестное действие: {request.action}"
            )

        logger.info(
            f"Выполнено действие {request.action} для трейдера {trader_id}",
            extra={"action": request.action, "force": request.force, "result": result},
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Ошибка выполнения действия {request.action} для трейдера {trader_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Ошибка выполнения действия: {str(e)}"
        )


@router.delete("/{trader_id}")
async def delete_trader(
    trader_id: str, force: bool = Query(False, description="Принудительное удаление")
):
    """Удалить трейдера"""
    try:
        trader_manager = get_trader_manager()
        trader = trader_manager.get_trader(trader_id)

        if not trader:
            raise HTTPException(
                status_code=404, detail=f"Трейдер {trader_id} не найден"
            )

        # Проверяем можно ли удалить трейдера
        if trader.is_trading() and not force:
            raise HTTPException(
                status_code=400,
                detail=f"Трейдер {trader_id} активно торгует. Используйте force=true для принудительного удаления",
            )

        # Останавливаем торговлю если активна
        if trader.is_trading():
            await trader.stop_trading(force=True)

        # Удаляем трейдера
        await trader_manager.remove_trader(trader_id)

        logger.info(f"Трейдер {trader_id} удален", extra={"force": force})

        return {"status": "success", "message": f"Трейдер {trader_id} удален"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления трейдера {trader_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка удаления трейдера: {str(e)}"
        )


@router.get("/{trader_id}/performance", response_model=Dict[str, Any])
async def get_trader_performance(
    trader_id: str, period: str = Query("24h", description="Период анализа")
):
    """Получить детальную статистику производительности трейдера"""
    try:
        trader_manager = get_trader_manager()
        trader = trader_manager.get_trader(trader_id)

        if not trader:
            raise HTTPException(
                status_code=404, detail=f"Трейдер {trader_id} не найден"
            )

        performance = trader.get_detailed_performance(period)

        logger.info(
            f"Получена статистика производительности трейдера {trader_id} за {period}"
        )

        return performance

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения статистики трейдера {trader_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка получения статистики: {str(e)}"
        )


@router.get("/{trader_id}/logs", response_model=List[Dict[str, Any]])
async def get_trader_logs(
    trader_id: str,
    limit: int = Query(100, description="Количество записей"),
    level: Optional[str] = Query(None, description="Уровень логирования"),
):
    """Получить логи трейдера"""
    try:
        trader_manager = get_trader_manager()
        trader = trader_manager.get_trader(trader_id)

        if not trader:
            raise HTTPException(
                status_code=404, detail=f"Трейдер {trader_id} не найден"
            )

        logs = trader.get_logs(limit=limit, level=level)

        return logs

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения логов трейдера {trader_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения логов: {str(e)}")


# =================== DEPENDENCY INJECTION ===================


def get_trader_manager():
    """Получить trader_manager из глобального контекста"""
    # Будет реализовано через dependency injection в main.py
    from web.integration.dependencies import get_trader_manager_dependency

    return get_trader_manager_dependency()
