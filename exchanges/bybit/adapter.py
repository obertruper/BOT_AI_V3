"""
Bybit Adapter для BOT_Trading v3.0

Обеспечивает совместимость нового унифицированного клиента Bybit
с существующими API и обратную совместимость с v1.0/v2.0 системами.

Этот адаптер позволяет использовать новый BybitClient через
привычные интерфейсы, сохраняя при этом все преимущества v3.0 архитектуры.
"""

from datetime import datetime
from typing import Any

from core.logger import setup_logger

from ..base.models import Position
from ..base.order_types import (
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderType,
    TimeInForce,
)
from .client import BybitClient, clean_symbol


class BybitLegacyAdapter:
    """
    Адаптер для обратной совместимости с legacy API Bybit

    Предоставляет методы в формате v1.0/v2.0 системы,
    но использует новый унифицированный клиент под капотом.
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        # Создаем унифицированный клиент
        self.client = BybitClient(api_key=api_key, api_secret=api_secret, sandbox=testnet)

        # Логирование
        self.logger = setup_logger("bybit_adapter")

        # Состояние соединения
        self._connected = False

    # =================== LEGACY CONNECTION METHODS ===================

    async def connect(self) -> bool:
        """Подключение к API"""
        try:
            self._connected = await self.client.connect()
            return self._connected
        except Exception as e:
            self.logger.error(f"Failed to connect via adapter: {e}")
            return False

    async def disconnect(self) -> None:
        """Отключение от API"""
        await self.client.disconnect()
        self._connected = False

    def check_connectivity(self) -> bool:
        """Проверка соединения (синхронная версия для legacy кода)"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.client.test_connection())
        except Exception:
            return False

    # =================== LEGACY TRADING METHODS ===================

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float | str,
        order_type: str = "Market",
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Legacy place_order метод для совместимости"""
        import asyncio

        try:
            # Преобразуем legacy параметры в новый формат
            order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

            order_type_mapping = {
                "Market": OrderType.MARKET,
                "Limit": OrderType.LIMIT,
                "StopMarket": OrderType.STOP_MARKET,
                "StopLimit": OrderType.STOP_LIMIT,
            }
            mapped_order_type = order_type_mapping.get(order_type, OrderType.MARKET)

            tif_mapping = {
                "GTC": TimeInForce.GTC,
                "IOC": TimeInForce.IOC,
                "FOK": TimeInForce.FOK,
            }
            mapped_tif = tif_mapping.get(time_in_force, TimeInForce.GTC)

            # Создаем запрос
            order_request = OrderRequest(
                symbol=symbol,
                side=order_side,
                order_type=mapped_order_type,
                quantity=float(qty),
                price=price,
                time_in_force=mapped_tif,
                reduce_only=reduce_only,
                stop_loss=stop_loss,
                take_profit=take_profit,
                exchange_params=kwargs,
            )

            # Выполняем асинхронно
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(self.client.place_order(order_request))

            # Преобразуем в legacy формат
            return self._convert_order_response_to_legacy(response)

        except Exception as e:
            self.logger.error(f"Legacy place_order failed: {e}")
            return {"retCode": 99999, "retMsg": str(e), "result": None}

    def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Legacy cancel_order метод"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(self.client.cancel_order(symbol, order_id))
            return self._convert_order_response_to_legacy(response)
        except Exception as e:
            return {"retCode": 99999, "retMsg": str(e), "result": None}

    def get_positions(self, symbol: str | None = None, **kwargs) -> dict[str, Any]:
        """Legacy get_positions метод"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            positions = loop.run_until_complete(self.client.get_positions(symbol))

            # Преобразуем в legacy формат
            legacy_positions = []
            for pos in positions:
                legacy_pos = self._convert_position_to_legacy(pos)
                legacy_positions.append(legacy_pos)

            return {"retCode": 0, "retMsg": "OK", "result": {"list": legacy_positions}}

        except Exception as e:
            return {"retCode": 99999, "retMsg": str(e), "result": None}

    def get_wallet_balance(self, account_type: str = "UNIFIED") -> dict[str, Any]:
        """Legacy get_wallet_balance метод"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            balances = loop.run_until_complete(self.client.get_balances(account_type))

            # Преобразуем в legacy формат
            legacy_coins = []
            for balance in balances:
                legacy_coin = {
                    "coin": balance.currency,
                    "walletBalance": str(balance.total),
                    "transferBalance": str(balance.available),
                    "locked": str(balance.frozen),
                }
                legacy_coins.append(legacy_coin)

            return {
                "retCode": 0,
                "retMsg": "OK",
                "result": {"list": [{"accountType": account_type, "coin": legacy_coins}]},
            }

        except Exception as e:
            return {"retCode": 99999, "retMsg": str(e), "result": None}

    def get_current_price(self, symbol: str) -> float:
        """Legacy get_current_price метод"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            ticker = loop.run_until_complete(self.client.get_ticker(symbol))
            return ticker.last_price
        except Exception as e:
            self.logger.error(f"Failed to get price for {symbol}: {e}")
            return 0.0

    def set_trading_stop(
        self,
        symbol: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Legacy set_trading_stop метод"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()

            if stop_loss:
                response = loop.run_until_complete(self.client.set_stop_loss(symbol, stop_loss))
                if not response.success:
                    return {
                        "retCode": 99999,
                        "retMsg": response.message,
                        "result": None,
                    }

            if take_profit:
                response = loop.run_until_complete(self.client.set_take_profit(symbol, take_profit))
                if not response.success:
                    return {
                        "retCode": 99999,
                        "retMsg": response.message,
                        "result": None,
                    }

            return {"retCode": 0, "retMsg": "OK", "result": {}}

        except Exception as e:
            return {"retCode": 99999, "retMsg": str(e), "result": None}

    def get_server_time(self) -> dict[str, Any]:
        """Legacy get_server_time метод"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            server_time = loop.run_until_complete(self.client.get_server_time())

            timestamp_ms = int(server_time.timestamp() * 1000)
            return {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "timeSecond": timestamp_ms // 1000,
                    "timeNano": timestamp_ms * 1000000,
                },
            }
        except Exception:
            # Fallback to local time
            timestamp_ms = int(datetime.now().timestamp() * 1000)
            return {
                "retCode": 0,
                "retMsg": "OK (local time)",
                "result": {
                    "timeSecond": timestamp_ms // 1000,
                    "timeNano": timestamp_ms * 1000000,
                },
            }

    # =================== CONVERSION HELPERS ===================

    def _convert_order_response_to_legacy(self, response: OrderResponse) -> dict[str, Any]:
        """Преобразование OrderResponse в legacy формат"""
        if response.success:
            return {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "orderId": response.order_id,
                    "orderLinkId": response.client_order_id,
                },
            }
        else:
            return {"retCode": 99999, "retMsg": response.message, "result": None}

    def _convert_position_to_legacy(self, position: Position) -> dict[str, Any]:
        """Преобразование Position в legacy формат"""
        return {
            "symbol": position.symbol,
            "side": position.side or "None",
            "size": str(position.size),
            "avgPrice": str(position.entry_price),
            "markPrice": str(position.mark_price),
            "unrealisedPnl": str(position.unrealised_pnl),
            "leverage": str(position.leverage),
            "positionIM": str(position.position_margin or 0),
            "liqPrice": str(position.liquidation_price or 0),
            "stopLoss": str(position.stop_loss or 0),
            "takeProfit": str(position.take_profit or 0),
            "positionMode": getattr(position, "position_mode", "MergedSingle"),
            "autoAddMargin": 1 if getattr(position, "auto_add_margin", False) else 0,
            "createdTime": (
                str(int(position.created_time.timestamp() * 1000)) if position.created_time else "0"
            ),
            "updatedTime": (
                str(int(position.updated_time.timestamp() * 1000)) if position.updated_time else "0"
            ),
        }


class BybitAPIClient(BybitLegacyAdapter):
    """
    Полностью совместимый с legacy системой API клиент

    Наследует от BybitLegacyAdapter и добавляет дополнительные
    методы для полной совместимости с существующим кодом.
    """

    def __init__(self, api_key="", api_secret="", testnet=False, config_path=None, db_path=None):
        super().__init__(api_key, api_secret, testnet)

        # Legacy атрибуты для совместимости
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"

        # Метрики для совместимости
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_errors = []

    def _make_request(
        self, method: str, endpoint: str, params: dict = None, auth: bool = False
    ) -> dict[str, Any]:
        """Legacy _make_request метод"""
        import asyncio

        try:
            self.request_count += 1

            # Используем новый клиент под капотом
            loop = asyncio.get_event_loop()
            response = loop.run_until_complete(
                self.client._make_request(method, endpoint, params, auth)
            )

            self.success_count += 1
            return response

        except Exception as e:
            self.error_count += 1
            self.last_errors.append(str(e))
            # Ограничиваем список ошибок
            if len(self.last_errors) > 10:
                self.last_errors.pop(0)

            return {"retCode": 99999, "retMsg": str(e), "result": None}


# Фабричная функция для совместимости
def get_bybit_client(
    api_key="", api_secret="", testnet=False, config_path=None, db_path=None
) -> BybitAPIClient:
    """
    Фабричная функция для создания Bybit клиента

    Полностью совместима с legacy версией, но использует
    новую архитектуру под капотом.
    """
    return BybitAPIClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
        config_path=config_path,
        db_path=db_path,
    )


# Экспорт для совместимости
__all__ = [
    "BybitAPIClient",  # Полностью совместимый клиент
    "BybitClient",  # Новый унифицированный клиент
    "BybitLegacyAdapter",  # Адаптер для legacy кода
    "clean_symbol",  # Утилита
    "get_bybit_client",  # Фабричная функция
]
