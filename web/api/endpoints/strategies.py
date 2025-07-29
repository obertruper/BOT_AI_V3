"""
Strategies API Endpoints

REST API для управления стратегиями:
- Список доступных стратегий
- Создание/настройка стратегий
- Запуск бэктестов
- Мониторинг производительности
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("strategies_api", component="web_api")

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

# =================== MODELS ===================

class StrategyInfo(BaseModel):
    """Информация о стратегии"""
    name: str
    display_name: str
    description: str
    category: str  # ml, indicator, arbitrage, scalping, grid
    status: str  # active, inactive, testing
    version: str
    parameters: Dict[str, Any]
    performance_metrics: Optional[Dict[str, float]] = None
    supported_exchanges: List[str]
    risk_level: str  # low, medium, high

class StrategyConfig(BaseModel):
    """Конфигурация стратегии"""
    strategy_name: str
    trader_id: str
    exchange: str
    symbol: str
    parameters: Dict[str, Any]
    risk_settings: Optional[Dict[str, Any]] = None
    enabled: bool = True

class BacktestRequest(BaseModel):
    """Запрос на бэктест"""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    parameters: Optional[Dict[str, Any]] = None
    exchanges: Optional[List[str]] = None

class BacktestResult(BaseModel):
    """Результат бэктеста"""
    backtest_id: str
    strategy_name: str
    symbol: str
    period: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_trade_duration: float
    profit_factor: float
    status: str  # running, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None

class StrategyPerformance(BaseModel):
    """Производительность стратегии"""
    strategy_name: str
    period: str
    total_pnl: float
    trades_count: int
    win_rate: float
    avg_win: float
    avg_loss: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    var_95: float
    last_updated: datetime

# =================== ENDPOINTS ===================

@router.get("/", response_model=List[StrategyInfo])
async def get_strategies(
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    active_only: bool = Query(False, description="Только активные стратегии")
):
    """Получить список всех доступных стратегий"""
    try:
        strategy_registry = get_strategy_registry()
        strategies = []
        
        for strategy_name in strategy_registry.get_available_strategies():
            strategy_class = strategy_registry.get_strategy_class(strategy_name)
            
            if not strategy_class:
                continue
            
            # Применяем фильтры
            if category and getattr(strategy_class, 'category', '') != category:
                continue
            
            if active_only and getattr(strategy_class, 'status', '') != 'active':
                continue
            
            # Получаем информацию о стратегии
            strategy_info = StrategyInfo(
                name=strategy_name,
                display_name=getattr(strategy_class, 'display_name', strategy_name.title()),
                description=getattr(strategy_class, 'description', ''),
                category=getattr(strategy_class, 'category', 'unknown'),
                status=getattr(strategy_class, 'status', 'inactive'),
                version=getattr(strategy_class, 'version', '1.0.0'),
                parameters=getattr(strategy_class, 'default_parameters', {}),
                performance_metrics=await get_strategy_performance_summary(strategy_name),
                supported_exchanges=getattr(strategy_class, 'supported_exchanges', []),
                risk_level=getattr(strategy_class, 'risk_level', 'medium')
            )
            
            strategies.append(strategy_info)
        
        logger.info(f"Получен список из {len(strategies)} стратегий", extra={
            'category': category,
            'active_only': active_only
        })
        
        return strategies
        
    except Exception as e:
        logger.error(f"Ошибка получения списка стратегий: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения стратегий: {str(e)}")

@router.get("/{strategy_name}", response_model=StrategyInfo)
async def get_strategy_info(strategy_name: str):
    """Получить детальную информацию о конкретной стратегии"""
    try:
        strategy_registry = get_strategy_registry()
        strategy_class = strategy_registry.get_strategy_class(strategy_name)
        
        if not strategy_class:
            raise HTTPException(status_code=404, detail=f"Стратегия {strategy_name} не найдена")
        
        # Получаем детальную производительность
        performance_metrics = await get_strategy_detailed_performance(strategy_name)
        
        strategy_info = StrategyInfo(
            name=strategy_name,
            display_name=getattr(strategy_class, 'display_name', strategy_name.title()),
            description=getattr(strategy_class, 'description', ''),
            category=getattr(strategy_class, 'category', 'unknown'),
            status=getattr(strategy_class, 'status', 'inactive'),
            version=getattr(strategy_class, 'version', '1.0.0'),
            parameters=getattr(strategy_class, 'default_parameters', {}),
            performance_metrics=performance_metrics,
            supported_exchanges=getattr(strategy_class, 'supported_exchanges', []),
            risk_level=getattr(strategy_class, 'risk_level', 'medium')
        )
        
        logger.info(f"Получена информация о стратегии {strategy_name}")
        return strategy_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения информации о стратегии {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации: {str(e)}")

@router.post("/config", response_model=Dict[str, Any])
async def configure_strategy(config: StrategyConfig):
    """Настроить стратегию для трейдера"""
    try:
        strategy_manager = get_strategy_manager()
        trader_manager = get_trader_manager()
        
        # Проверяем что трейдер существует
        trader = trader_manager.get_trader(config.trader_id)
        if not trader:
            raise HTTPException(status_code=404, detail=f"Трейдер {config.trader_id} не найден")
        
        # Проверяем что стратегия существует
        strategy_registry = get_strategy_registry()
        if not strategy_registry.get_strategy_class(config.strategy_name):
            raise HTTPException(status_code=404, detail=f"Стратегия {config.strategy_name} не найдена")
        
        # Настраиваем стратегию
        strategy_config = {
            'strategy_name': config.strategy_name,
            'exchange': config.exchange,
            'symbol': config.symbol,
            'parameters': config.parameters,
            'risk_settings': config.risk_settings or {},
            'enabled': config.enabled
        }
        
        success = await strategy_manager.configure_strategy(config.trader_id, strategy_config)
        
        if not success:
            raise HTTPException(status_code=500, detail="Не удалось настроить стратегию")
        
        logger.info(f"Настроена стратегия {config.strategy_name} для трейдера {config.trader_id}", extra={
            'strategy_config': strategy_config
        })
        
        return {
            "status": "success",
            "trader_id": config.trader_id,
            "strategy_name": config.strategy_name,
            "message": f"Стратегия {config.strategy_name} настроена для трейдера {config.trader_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка настройки стратегии {config.strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка настройки стратегии: {str(e)}")

@router.post("/backtest", response_model=BacktestResult)
async def start_backtest(request: BacktestRequest):
    """Запустить бэктест стратегии"""
    try:
        backtest_engine = get_backtest_engine()
        
        # Валидация параметров
        if request.start_date >= request.end_date:
            raise HTTPException(status_code=400, detail="Дата начала должна быть меньше даты окончания")
        
        if request.initial_balance <= 0:
            raise HTTPException(status_code=400, detail="Начальный баланс должен быть положительным")
        
        # Проверяем что стратегия существует
        strategy_registry = get_strategy_registry()
        if not strategy_registry.get_strategy_class(request.strategy_name):
            raise HTTPException(status_code=404, detail=f"Стратегия {request.strategy_name} не найдена")
        
        # Запускаем бэктест
        backtest_config = {
            'strategy_name': request.strategy_name,
            'symbol': request.symbol,
            'start_date': request.start_date,
            'end_date': request.end_date,
            'initial_balance': request.initial_balance,
            'parameters': request.parameters or {},
            'exchanges': request.exchanges or ['bybit']
        }
        
        backtest_id = await backtest_engine.start_backtest(backtest_config)
        
        # Возвращаем информацию о запущенном бэктесте
        result = BacktestResult(
            backtest_id=backtest_id,
            strategy_name=request.strategy_name,
            symbol=request.symbol,
            period=f"{request.start_date.strftime('%Y-%m-%d')} - {request.end_date.strftime('%Y-%m-%d')}",
            total_return=0.0,  # Будет обновлено по завершении
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            total_trades=0,
            avg_trade_duration=0.0,
            profit_factor=0.0,
            status="running",
            created_at=datetime.now()
        )
        
        logger.info(f"Запущен бэктест {backtest_id} для стратегии {request.strategy_name}", extra={
            'backtest_config': backtest_config
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка запуска бэктеста для стратегии {request.strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка запуска бэктеста: {str(e)}")

@router.get("/backtest/{backtest_id}", response_model=BacktestResult)
async def get_backtest_result(backtest_id: str):
    """Получить результат бэктеста"""
    try:
        backtest_engine = get_backtest_engine()
        result = await backtest_engine.get_backtest_result(backtest_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Бэктест {backtest_id} не найден")
        
        logger.info(f"Получен результат бэктеста {backtest_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения результата бэктеста {backtest_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения результата: {str(e)}")

@router.get("/{strategy_name}/performance", response_model=StrategyPerformance)
async def get_strategy_performance(
    strategy_name: str,
    period: str = Query("30d", description="Период анализа (1d, 7d, 30d, 90d, 1y)")
):
    """Получить детальную производительность стратегии"""
    try:
        # Проверяем что стратегия существует
        strategy_registry = get_strategy_registry()
        if not strategy_registry.get_strategy_class(strategy_name):
            raise HTTPException(status_code=404, detail=f"Стратегия {strategy_name} не найдена")
        
        # Получаем производительность
        performance_service = get_performance_service()
        performance_data = await performance_service.get_strategy_performance(strategy_name, period)
        
        performance = StrategyPerformance(
            strategy_name=strategy_name,
            period=period,
            total_pnl=performance_data.get('total_pnl', 0.0),
            trades_count=performance_data.get('trades_count', 0),
            win_rate=performance_data.get('win_rate', 0.0),
            avg_win=performance_data.get('avg_win', 0.0),
            avg_loss=performance_data.get('avg_loss', 0.0),
            max_drawdown=performance_data.get('max_drawdown', 0.0),
            sharpe_ratio=performance_data.get('sharpe_ratio', 0.0),
            sortino_ratio=performance_data.get('sortino_ratio', 0.0),
            calmar_ratio=performance_data.get('calmar_ratio', 0.0),
            var_95=performance_data.get('var_95', 0.0),
            last_updated=datetime.now()
        )
        
        logger.info(f"Получена производительность стратегии {strategy_name} за {period}")
        
        return performance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения производительности стратегии {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения производительности: {str(e)}")

@router.get("/categories/list", response_model=List[Dict[str, str]])
async def get_strategy_categories():
    """Получить список категорий стратегий"""
    try:
        categories = [
            {"name": "ml", "display_name": "Machine Learning", "description": "Стратегии на основе машинного обучения"},
            {"name": "indicator", "display_name": "Technical Indicators", "description": "Стратегии на технических индикаторах"},
            {"name": "arbitrage", "display_name": "Arbitrage", "description": "Арбитражные стратегии"},
            {"name": "scalping", "display_name": "Scalping", "description": "Скальпинговые стратегии"},
            {"name": "grid", "display_name": "Grid Trading", "description": "Сеточные стратегии"},
            {"name": "trend", "display_name": "Trend Following", "description": "Трендовые стратегии"},
            {"name": "mean_reversion", "display_name": "Mean Reversion", "description": "Стратегии возврата к среднему"}
        ]
        
        logger.info("Получен список категорий стратегий")
        
        return categories
        
    except Exception as e:
        logger.error(f"Ошибка получения категорий стратегий: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения категорий: {str(e)}")

# =================== HELPER FUNCTIONS ===================

async def get_strategy_performance_summary(strategy_name: str) -> Optional[Dict[str, float]]:
    """Получить краткую сводку производительности стратегии"""
    try:
        performance_service = get_performance_service()
        summary = await performance_service.get_strategy_summary(strategy_name)
        return summary
    except Exception as e:
        logger.error(f"Ошибка получения сводки производительности {strategy_name}: {e}")
        return None

async def get_strategy_detailed_performance(strategy_name: str) -> Optional[Dict[str, float]]:
    """Получить детальную производительность стратегии"""
    try:
        performance_service = get_performance_service()
        detailed = await performance_service.get_strategy_detailed_metrics(strategy_name)
        return detailed
    except Exception as e:
        logger.error(f"Ошибка получения детальной производительности {strategy_name}: {e}")
        return None

# =================== DEPENDENCY INJECTION ===================

def get_strategy_registry():
    """Получить strategy_registry из глобального контекста"""
    from web.integration.dependencies import get_strategy_registry_dependency
    return get_strategy_registry_dependency()

def get_strategy_manager():
    """Получить strategy_manager из глобального контекста"""
    from web.integration.dependencies import get_strategy_manager_dependency
    return get_strategy_manager_dependency()

def get_trader_manager():
    """Получить trader_manager из глобального контекста"""
    from web.integration.dependencies import get_trader_manager_dependency
    return get_trader_manager_dependency()

def get_backtest_engine():
    """Получить backtest_engine из глобального контекста"""
    from web.integration.dependencies import get_backtest_engine_dependency
    return get_backtest_engine_dependency()

def get_performance_service():
    """Получить performance_service из глобального контекста"""
    from web.integration.dependencies import get_performance_service_dependency
    return get_performance_service_dependency()