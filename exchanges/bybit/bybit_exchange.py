#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bybit Exchange для BOT Trading v3

Это основной модуль для работы с биржей Bybit.
Предоставляет унифицированный интерфейс для торговли.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

from core.logger import setup_logger
from exchanges.base.exchange_interface import BaseExchangeInterface
from exchanges.base.models import (
    Balance,
    Instrument,
    Kline,
    Order,
    OrderBook,
    Position,
    Ticker,
)
from exchanges.base.order_types import OrderRequest, OrderResponse

from .adapter import BybitAPIClient, BybitLegacyAdapter
from .client import BybitClient

logger = setup_logger("bybit_exchange")


class BybitExchange(BaseExchangeInterface):
    """
    Основной класс для работы с биржей Bybit.

    Использует BybitClient для современного API и предоставляет
    унифицированный интерфейс для торговой системы.
    """

    def __init__(
        self, api_key: str, api_secret: str, sandbox: bool = False, timeout: int = 30
    ):
        """
        Инициализация Bybit Exchange.

        Args:
            api_key: API ключ
            api_secret: API секрет
            sandbox: Использовать тестовую сеть
            timeout: Таймаут соединения
        """
        # Создаем клиент
        self.client = BybitClient(
            api_key=api_key, api_secret=api_secret, sandbox=sandbox, timeout=timeout
        )

        # Для обратной совместимости создаем legacy адаптер
        self.legacy_adapter = BybitLegacyAdapter(
            api_key=api_key, api_secret=api_secret, testnet=sandbox
        )

        self._connected = False
        logger.info(f"BybitExchange initialized (sandbox={sandbox})")

    @property
    def name(self) -> str:
        """Название биржи"""
        return self.client.name

    @property
    def capabilities(self):
        """Возможности биржи"""
        return self.client.capabilities

    @property
    def is_connected(self) -> bool:
        """Статус подключения"""
        return self._connected

    # =================== ПОДКЛЮЧЕНИЕ ===================

    async def connect(self) -> bool:
        """Подключение к бирже"""
        try:
            result = await self.client.connect()
            if result:
                self._connected = True
                # Также подключаем legacy адаптер для совместимости
                await self.legacy_adapter.connect()
            return result
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def disconnect(self) -> None:
        """Отключение от биржи"""
        await self.client.disconnect()
        await self.legacy_adapter.disconnect()
        self._connected = False

    async def test_connection(self) -> bool:
        """Тест соединения"""
        return await self.client.test_connection()

    # =================== ИНФОРМАЦИЯ О БИРЖЕ ===================

    async def get_exchange_info(self):
        """Получение информации о бирже"""
        return await self.client.get_exchange_info()

    async def get_instruments(self, category: Optional[str] = None) -> List[Instrument]:
        """Получение списка инструментов"""
        return await self.client.get_instruments(category)

    async def get_instrument_info(self, symbol: str) -> Instrument:
        """Получение информации об инструменте"""
        return await self.client.get_instrument_info(symbol)

    # =================== АККАУНТ ===================

    async def get_account_info(self):
        """Получение информации об аккаунте"""
        return await self.client.get_account_info()

    async def get_balances(self, account_type: Optional[str] = None) -> List[Balance]:
        """Получение балансов"""
        return await self.client.get_balances(account_type)

    async def get_balance(
        self, currency: str, account_type: Optional[str] = None
    ) -> Balance:
        """Получение баланса конкретной валюты"""
        return await self.client.get_balance(currency, account_type)

    # =================== РЫНОЧНЫЕ ДАННЫЕ ===================

    async def get_ticker(self, symbol: str) -> Ticker:
        """Получение тикера"""
        return await self.client.get_ticker(symbol)

    async def get_tickers(self, category: Optional[str] = None) -> List[Ticker]:
        """Получение всех тикеров"""
        return await self.client.get_tickers(category)

    async def get_orderbook(self, symbol: str, limit: int = 25) -> OrderBook:
        """Получение стакана"""
        return await self.client.get_orderbook(symbol, limit)

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Kline]:
        """Получение свечей"""
        return await self.client.get_klines(
            symbol, interval, start_time, end_time, limit
        )

    # =================== ТОРГОВЛЯ ===================

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Размещение ордера"""
        return await self.client.place_order(order_request)

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResponse:
        """Отмена ордера"""
        return await self.client.cancel_order(symbol, order_id)

    async def cancel_all_orders(
        self, symbol: Optional[str] = None
    ) -> List[OrderResponse]:
        """Отмена всех ордеров"""
        return await self.client.cancel_all_orders(symbol)

    async def modify_order(
        self,
        symbol: str,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
    ) -> OrderResponse:
        """Модификация ордера"""
        return await self.client.modify_order(symbol, order_id, quantity, price)

    async def get_order(self, symbol: str, order_id: str) -> Order:
        """Получение информации об ордере"""
        return await self.client.get_order(symbol, order_id)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Получение открытых ордеров"""
        return await self.client.get_open_orders(symbol)

    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Order]:
        """Получение истории ордеров"""
        return await self.client.get_order_history(symbol, start_time, end_time, limit)

    # =================== ПОЗИЦИИ ===================

    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Получение позиций"""
        return await self.client.get_positions(symbol)

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Получение конкретной позиции"""
        return await self.client.get_position(symbol)

    async def close_position(
        self, symbol: str, quantity: Optional[float] = None
    ) -> OrderResponse:
        """Закрытие позиции"""
        return await self.client.close_position(symbol, quantity)

    async def set_leverage(self, symbol: str, leverage: float) -> bool:
        """Установка плеча"""
        return await self.client.set_leverage(symbol, leverage)

    async def set_position_mode(self, symbol: str, hedge_mode: bool) -> bool:
        """Установка режима позиции"""
        return await self.client.set_position_mode(symbol, hedge_mode)

    async def set_stop_loss(
        self, symbol: str, stop_price: float, quantity: Optional[float] = None
    ) -> OrderResponse:
        """Установка Stop Loss"""
        return await self.client.set_stop_loss(symbol, stop_price, quantity)

    async def set_take_profit(
        self, symbol: str, take_price: float, quantity: Optional[float] = None
    ) -> OrderResponse:
        """Установка Take Profit"""
        return await self.client.set_take_profit(symbol, take_price, quantity)

    # =================== СОВМЕСТИМОСТЬ С LEGACY API ===================

    def get_legacy_client(self) -> BybitAPIClient:
        """
        Получение legacy клиента для обратной совместимости.

        Returns:
            BybitAPIClient для работы со старым API
        """
        return BybitAPIClient(
            api_key=self.client.api_key,
            api_secret=self.client.api_secret,
            testnet=self.client.sandbox,
        )

    # Методы для обратной совместимости
    def place_order_sync(
        self,
        symbol: str,
        side: str,
        qty: Union[float, str],
        order_type: str = "Market",
        **kwargs,
    ) -> Dict[str, any]:
        """
        Синхронная версия place_order для обратной совместимости.

        Использует legacy адаптер для выполнения.
        """
        return self.legacy_adapter.place_order(symbol, side, qty, order_type, **kwargs)

    def get_positions_sync(self, symbol: Optional[str] = None) -> Dict[str, any]:
        """
        Синхронная версия get_positions для обратной совместимости.
        """
        return self.legacy_adapter.get_positions(symbol)

    def get_wallet_balance_sync(self, account_type: str = "UNIFIED") -> Dict[str, any]:
        """
        Синхронная версия get_wallet_balance для обратной совместимости.
        """
        return self.legacy_adapter.get_wallet_balance(account_type)


# Фабричная функция для создания экземпляра биржи
def create_bybit_exchange(
    api_key: str, api_secret: str, sandbox: bool = False, timeout: int = 30
) -> BybitExchange:
    """
    Создает экземпляр BybitExchange.

    Args:
        api_key: API ключ
        api_secret: API секрет
        sandbox: Использовать тестовую сеть
        timeout: Таймаут соединения

    Returns:
        BybitExchange instance
    """
    return BybitExchange(api_key, api_secret, sandbox, timeout)


# Экспорт для удобства
__all__ = [
    "BybitExchange",
    "BybitClient",
    "BybitLegacyAdapter",
    "BybitAPIClient",
    "create_bybit_exchange",
]
