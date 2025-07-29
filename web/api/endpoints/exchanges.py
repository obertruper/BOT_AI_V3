"""
Exchanges API Endpoints

REST API для управления биржами:
- Информация о подключенных биржах
- Тестирование соединений
- Управление API ключами
- Мониторинг статуса
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("exchanges_api", component="web_api")

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])

# =================== MODELS ===================


class ExchangeInfo(BaseModel):
    """Информация о бирже"""

    name: str
    display_name: str
    status: str  # connected, disconnected, error
    capabilities: Dict[str, bool]
    supported_symbols: List[str]
    api_limits: Dict[str, Any]
    last_heartbeat: Optional[datetime] = None


class ExchangeConfig(BaseModel):
    """Конфигурация биржи"""

    exchange: str
    api_key: str
    api_secret: str
    sandbox: bool = False
    additional_params: Optional[Dict[str, Any]] = None


class ConnectionTest(BaseModel):
    """Результат тестирования подключения"""

    exchange: str
    success: bool
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: datetime


# =================== ENDPOINTS ===================


@router.get("/", response_model=List[ExchangeInfo])
async def get_exchanges():
    """Получить список всех доступных бирж"""
    try:
        exchange_registry = get_exchange_registry()
        exchanges = []

        for exchange_name in exchange_registry.get_available_exchanges():
            exchange_client = exchange_registry.get_exchange(exchange_name)

            if exchange_client:
                info = ExchangeInfo(
                    name=exchange_name,
                    display_name=exchange_client.name.title(),
                    status="connected"
                    if exchange_client.is_connected()
                    else "disconnected",
                    capabilities=exchange_client.capabilities.__dict__,
                    supported_symbols=await exchange_client.get_supported_symbols(),
                    api_limits=exchange_client.get_api_limits(),
                    last_heartbeat=exchange_client.last_heartbeat,
                )
            else:
                info = ExchangeInfo(
                    name=exchange_name,
                    display_name=exchange_name.title(),
                    status="available",
                    capabilities={},
                    supported_symbols=[],
                    api_limits={},
                    last_heartbeat=None,
                )

            exchanges.append(info)

        logger.info(f"Получен список из {len(exchanges)} бирж")
        return exchanges

    except Exception as e:
        logger.error(f"Ошибка получения списка бирж: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения бирж: {str(e)}")


@router.get("/{exchange_name}", response_model=ExchangeInfo)
async def get_exchange_info(exchange_name: str):
    """Получить детальную информацию о конкретной бирже"""
    try:
        exchange_registry = get_exchange_registry()
        exchange_client = exchange_registry.get_exchange(exchange_name)

        if not exchange_client:
            raise HTTPException(
                status_code=404,
                detail=f"Биржа {exchange_name} не найдена или не подключена",
            )

        # Получаем детальную информацию
        supported_symbols = await exchange_client.get_supported_symbols()

        info = ExchangeInfo(
            name=exchange_name,
            display_name=exchange_client.name.title(),
            status="connected" if exchange_client.is_connected() else "disconnected",
            capabilities=exchange_client.capabilities.__dict__,
            supported_symbols=supported_symbols,
            api_limits=exchange_client.get_api_limits(),
            last_heartbeat=exchange_client.last_heartbeat,
        )

        logger.info(f"Получена информация о бирже {exchange_name}")
        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения информации о бирже {exchange_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Ошибка получения информации: {str(e)}"
        )


@router.post("/connect", response_model=Dict[str, Any])
async def connect_exchange(config: ExchangeConfig):
    """Подключить новую биржу"""
    try:
        exchange_factory = get_exchange_factory()
        exchange_registry = get_exchange_registry()

        # Проверяем что биржа поддерживается
        if not exchange_factory.is_supported(config.exchange):
            raise HTTPException(
                status_code=400, detail=f"Биржа {config.exchange} не поддерживается"
            )

        # Создаем подключение
        exchange_config = {
            "api_key": config.api_key,
            "api_secret": config.api_secret,
            "sandbox": config.sandbox,
        }

        if config.additional_params:
            exchange_config.update(config.additional_params)

        exchange_client = await exchange_factory.create_exchange(
            config.exchange, exchange_config
        )

        # Тестируем подключение
        await exchange_client.test_connection()

        # Регистрируем в реестре
        exchange_registry.register_exchange(config.exchange, exchange_client)

        logger.info(
            f"Биржа {config.exchange} успешно подключена",
            extra={"sandbox": config.sandbox},
        )

        return {
            "status": "success",
            "exchange": config.exchange,
            "message": f"Биржа {config.exchange} подключена",
            "sandbox": config.sandbox,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка подключения биржи {config.exchange}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {str(e)}")


@router.post("/{exchange_name}/test", response_model=ConnectionTest)
async def test_exchange_connection(exchange_name: str):
    """Тестировать подключение к бирже"""
    try:
        exchange_registry = get_exchange_registry()
        exchange_client = exchange_registry.get_exchange(exchange_name)

        if not exchange_client:
            raise HTTPException(
                status_code=404, detail=f"Биржа {exchange_name} не подключена"
            )

        start_time = datetime.now()

        try:
            await exchange_client.test_connection()
            success = True
            error_message = None
        except Exception as test_error:
            success = False
            error_message = str(test_error)

        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        test_result = ConnectionTest(
            exchange=exchange_name,
            success=success,
            latency_ms=latency_ms if success else None,
            error_message=error_message,
            timestamp=end_time,
        )

        logger.info(
            f"Тест подключения к {exchange_name}: {'успешно' if success else 'неудачно'}"
        )

        return test_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка тестирования подключения к {exchange_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка тестирования: {str(e)}")


# =================== DEPENDENCY INJECTION ===================


def get_exchange_factory():
    """Получить exchange_factory из глобального контекста"""
    from web.integration.dependencies import get_exchange_factory_dependency

    return get_exchange_factory_dependency()


def get_exchange_registry():
    """Получить exchange_registry из глобального контекста"""
    from web.integration.dependencies import get_exchange_registry_dependency

    return get_exchange_registry_dependency()
