"""
FastAPI Web Application для BOT_Trading v3.0

Интегрированный веб-сервер для управления торговыми ботами:
- RESTful API для всех операций
- WebSocket для real-time данных
- Прямая интеграция с core системой
- Безопасная аутентификация и авторизация
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

try:
    # Попытка импорта для установленного пакета
    from core.config.config_manager import ConfigManager
    from core.logging.logger_factory import get_global_logger_factory
    from core.shared_context import shared_context
    from web.integration.web_orchestrator_bridge import (
        WebOrchestratorBridge,
        get_web_orchestrator_bridge,
        initialize_web_bridge,
    )
except ImportError:
    # Fallback для разработки - добавляем путь к проекту
    import os
    import sys

    # Добавляем корневую директорию проекта в Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Повторная попытка импорта
    from core.config.config_manager import ConfigManager
    from core.logging.logger_factory import get_global_logger_factory
    from core.shared_context import shared_context
    from web.integration.web_orchestrator_bridge import (
        WebOrchestratorBridge,
        initialize_web_bridge,
    )


# Глобальные переменные для интеграции
_orchestrator: Optional[Any] = None
_trader_manager: Optional[Any] = None
_exchange_factory: Optional[Any] = None
_config_manager: Optional[ConfigManager] = None
_web_bridge: Optional[WebOrchestratorBridge] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом FastAPI приложения"""
    global _web_bridge, _orchestrator

    # Startup
    logger = logging.getLogger("web_api")
    logger.info("Starting BOT_Trading v3.0 Web API...")

    # Попытка получить orchestrator из shared context
    _orchestrator = shared_context.get_orchestrator()
    if _orchestrator:
        logger.info("✅ Получен orchestrator из shared context")
    else:
        logger.warning(
            "⚠️ Orchestrator не найден в shared context, работаем в mock режиме"
        )

    try:
        # Инициализация веб-моста с orchestrator из shared context
        _web_bridge = await initialize_web_bridge(_orchestrator)
        logger.info("Web bridge initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize web bridge: {e}")
        # Продолжаем в mock режиме
        _web_bridge = await initialize_web_bridge(None)

    yield

    # Shutdown
    logger.info("Shutting down BOT_Trading v3.0 Web API...")
    if _web_bridge:
        await _web_bridge.shutdown()


# Создание FastAPI приложения
app = FastAPI(
    title="BOT_Trading v3.0 Web API",
    description="Comprehensive trading bot management and monitoring API",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Security
security = HTTPBearer()

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development
        "http://localhost:5173",  # Vite development
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Middleware для доверенных хостов
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*"],  # В продакшене ограничить
)


# =================== ПОДКЛЮЧЕНИЕ РОУТЕРОВ ===================

# Импортируем роутеры
from web.api.endpoints import (
    auth_router,
    exchanges_router,
    monitoring_router,
    strategies_router,
    traders_router,
)
from web.api.ml_api import router as ml_router

# Подключаем роутеры к приложению
app.include_router(monitoring_router)
app.include_router(traders_router)
app.include_router(exchanges_router)
app.include_router(strategies_router)
app.include_router(auth_router)
app.include_router(ml_router)


# =================== DEPENDENCY INJECTION ===================


async def get_orchestrator():
    """Получение экземпляра оркестратора"""
    global _orchestrator
    if _orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System orchestrator not available",
        )
    return _orchestrator


async def get_trader_manager():
    """Получение менеджера трейдеров"""
    global _trader_manager
    if _trader_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trader manager not available",
        )
    return _trader_manager


async def get_exchange_factory():
    """Получение фабрики бирж"""
    global _exchange_factory
    if _exchange_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Exchange factory not available",
        )
    return _exchange_factory


async def get_config_manager():
    """Получение менеджера конфигурации"""
    global _config_manager
    if _config_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration manager not available",
        )
    return _config_manager


async def get_web_bridge():
    """Получение веб-моста"""
    global _web_bridge
    if _web_bridge is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web bridge not available",
        )
    return _web_bridge


# =================== ИНИЦИАЛИЗАЦИЯ ===================


def initialize_web_api(orchestrator, trader_manager, exchange_factory, config_manager):
    """
    Инициализация веб API с компонентами системы

    Args:
        orchestrator: Системный оркестратор
        trader_manager: Менеджер трейдеров
        exchange_factory: Фабрика бирж
        config_manager: Менеджер конфигурации
    """
    global _orchestrator, _trader_manager, _exchange_factory, _config_manager

    _orchestrator = orchestrator
    _trader_manager = trader_manager
    _exchange_factory = exchange_factory
    _config_manager = config_manager

    # Логирование
    logger = logging.getLogger("web_api")
    logger.info("Web API initialized with system components")


# =================== БАЗОВЫЕ ЭНДПОИНТЫ ===================


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "BOT_Trading v3.0 Web API",
        "version": "3.0.0",
        "status": "running",
        "docs": "/api/docs",
    }


@app.get("/api/health")
async def health_check():
    """
    Комплексная проверка здоровья системы

    Проверяет все критические компоненты:
    - База данных PostgreSQL
    - Redis кеш
    - Подключения к биржам
    - Системные ресурсы
    - Внутренние компоненты

    Returns:
        Детальный статус всех компонентов системы
    """
    global _trader_manager, _exchange_factory, _config_manager

    try:
        # Быстрая проверка основных компонентов
        basic_status = {
            "orchestrator": _orchestrator is not None,
            "trader_manager": _trader_manager is not None,
            "exchange_factory": _exchange_factory is not None,
            "config_manager": _config_manager is not None,
            "web_bridge": _web_bridge is not None,
        }

        # Обновляем глобальные переменные из orchestrator если они не заданы
        if _orchestrator:
            _trader_manager = _trader_manager or getattr(
                _orchestrator, "trader_manager", None
            )
            _exchange_factory = _exchange_factory or getattr(
                _orchestrator, "exchange_factory", None
            )
            _config_manager = _config_manager or getattr(
                _orchestrator, "config_manager", None
            )

            # Обновляем статус компонентов
            basic_status.update(
                {
                    "trader_manager": _trader_manager is not None,
                    "exchange_factory": _exchange_factory is not None,
                    "config_manager": _config_manager is not None,
                }
            )

        # Если есть HealthChecker, используем его для детальной проверки
        if (
            _orchestrator
            and hasattr(_orchestrator, "health_checker")
            and _orchestrator.health_checker
        ):
            health_checker = _orchestrator.health_checker

            # Устанавливаем компоненты для проверки
            health_checker.set_components(
                exchange_registry=_exchange_factory,
                trader_manager=_trader_manager,
                strategy_manager=getattr(_orchestrator, "strategy_manager", None),
            )

            # Получаем детальный отчет
            detailed_report = await health_checker.get_detailed_report()

            return {
                "status": detailed_report["overall_status"],
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (
                    int((datetime.now() - _orchestrator.startup_time).total_seconds())
                    if _orchestrator and _orchestrator.startup_time
                    else 0
                ),
                "components": detailed_report["components"],
                "basic_components": basic_status,
                "details": detailed_report.get("details", {}),
            }
        else:
            # Fallback на базовую проверку
            overall_status = "healthy" if all(basic_status.values()) else "degraded"

            return {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "components": basic_status,
                "message": "Detailed health check not available",
            }

    except Exception as e:
        logger = logging.getLogger("web_api")
        logger.error(f"Error during health check: {e}")

        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "components": {
                "orchestrator": _orchestrator is not None,
                "trader_manager": _trader_manager is not None,
                "exchange_factory": _exchange_factory is not None,
                "config_manager": _config_manager is not None,
            },
        }


@app.get("/api/system/status")
async def get_system_status(bridge: WebOrchestratorBridge = Depends(get_web_bridge)):
    """Получение статуса системы"""
    try:
        status_data = await bridge.get_system_status()
        return {
            "success": True,
            "data": status_data,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}",
        )


# =================== TRADERS API ===================


@app.get("/api/traders")
async def get_traders(bridge: WebOrchestratorBridge = Depends(get_web_bridge)):
    """Получение списка всех трейдеров"""
    try:
        traders = await bridge.get_traders()
        return {
            "success": True,
            "data": traders,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get traders: {str(e)}",
        )


@app.get("/api/traders/{trader_id}")
async def get_trader(
    trader_id: str, bridge: WebOrchestratorBridge = Depends(get_web_bridge)
):
    """Получение данных конкретного трейдера"""
    try:
        trader = await bridge.get_trader(trader_id)
        if trader is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trader {trader_id} not found",
            )
        return {
            "success": True,
            "data": trader,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trader: {str(e)}",
        )


@app.post("/api/traders/{trader_id}/start")
async def start_trader(
    trader_id: str, bridge: WebOrchestratorBridge = Depends(get_web_bridge)
):
    """Запуск трейдера"""
    try:
        result = await bridge.start_trader(trader_id)
        return {
            "success": result,
            "message": f"Trader {trader_id} {'started' if result else 'failed to start'}",
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start trader: {str(e)}",
        )


@app.post("/api/traders/{trader_id}/stop")
async def stop_trader(
    trader_id: str, bridge: WebOrchestratorBridge = Depends(get_web_bridge)
):
    """Остановка трейдера"""
    try:
        result = await bridge.stop_trader(trader_id)
        return {
            "success": result,
            "message": f"Trader {trader_id} {'stopped' if result else 'failed to stop'}",
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop trader: {str(e)}",
        )


# =================== POSITIONS API ===================


@app.get("/api/positions")
async def get_positions(
    trader_id: Optional[str] = None,
    bridge: WebOrchestratorBridge = Depends(get_web_bridge),
):
    """Получение списка позиций"""
    try:
        positions = await bridge.get_positions(trader_id)
        return {
            "success": True,
            "data": positions,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}",
        )


@app.get("/api/system/config/raw")
async def get_system_config_raw():
    """Безопасная выдача полной конфигурации (секреты редактируются)."""
    try:
        cfg_manager: Optional[ConfigManager] = _config_manager
        if not cfg_manager:
            cfg_manager = ConfigManager()
            await cfg_manager.initialize()
        raw_cfg = cfg_manager.get_config()

        def _sanitize(d: Any):
            if isinstance(d, dict):
                red = {}
                for k, v in d.items():
                    lk = k.lower()
                    if any(s in lk for s in ["secret", "api_key", "password", "token"]):
                        red[k] = "***"
                    else:
                        red[k] = _sanitize(v)
                return red
            elif isinstance(d, list):
                return [_sanitize(x) for x in d]
            return d

        safe_cfg = _sanitize(raw_cfg if isinstance(raw_cfg, dict) else {})
        return {
            "success": True,
            "data": safe_cfg,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger = logging.getLogger("web_api")
        logger.error(f"Failed to get system config: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }


@app.post("/api/system/config/update")
async def update_system_config(body: dict):
    """Обновление раздела system в конфигурации. Ожидает {"updates": {...}}"""
    try:
        updates = body.get("updates", {})
        if not isinstance(updates, dict):
            raise ValueError("updates must be a dict")

        cfg_manager: Optional[ConfigManager] = _config_manager
        if not cfg_manager:
            cfg_manager = ConfigManager()
            await cfg_manager.initialize()

        # Обновляем и сохраняем конфигурацию
        new_cfg = cfg_manager.update_system_config(updates)
        return {
            "success": True,
            "data": new_cfg,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as e:
        logger = logging.getLogger("web_api")
        logger.error(f"Failed to update system config: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }


# =================== ОБРАБОТКА ОШИБОК ===================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Обработчик HTTP исключений"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Обработчик общих исключений"""
    logger = logging.getLogger("web_api")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": True, "message": "Internal server error", "status_code": 500},
    )


# =================== ЗАПУСК СЕРВЕРА ===================


async def start_web_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    orchestrator=None,
    trader_manager=None,
    exchange_factory=None,
    config_manager=None,
):
    """
    Запуск веб-сервера с интеграцией компонентов

    Args:
        host: Хост для привязки
        port: Порт для прослушивания
        orchestrator: Системный оркестратор
        trader_manager: Менеджер трейдеров
        exchange_factory: Фабрика бирж
        config_manager: Менеджер конфигурации
    """

    # Инициализация компонентов если переданы
    if orchestrator and trader_manager and exchange_factory and config_manager:
        initialize_web_api(
            orchestrator, trader_manager, exchange_factory, config_manager
        )

    # Настройка логирования
    logger_factory = get_global_logger_factory()
    logger = logger_factory.get_logger("web_server")

    logger.info(f"Starting web server on {host}:{port}")

    # Конфигурация uvicorn
    config = uvicorn.Config(
        app=app, host=host, port=port, log_level="info", access_log=True, loop="asyncio"
    )

    # Запуск сервера
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    # Запуск в режиме разработки
    asyncio.run(start_web_server(port=8080))
