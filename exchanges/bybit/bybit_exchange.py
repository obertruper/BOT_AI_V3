#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bybit Exchange для BOT Trading v3

Это основной модуль для работы с биржей Bybit.
Предоставляет унифицированный интерфейс для торговли.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from core.logger import setup_logger
from exchanges.base.exchange_interface import BaseExchangeInterface
from exchanges.base.models import (
    Balance,
    Candle,
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

        # Кэш для свечей
        self.candles_cache: Dict[str, Dict] = {}
        self.cache_ttl = 60  # 1 минута

        # Маппинг интервалов
        self.interval_map = {
            1: "1",
            5: "5",
            15: "15",
            30: "30",
            60: "60",
            240: "240",
            1440: "D",
        }

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

    async def initialize(self) -> bool:
        """Инициализация биржи (алиас для connect)"""
        return await self.connect()

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

    # =================== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ===================

    async def fetch_balance(self) -> Dict[str, Dict[str, float]]:
        """
        Получение баланса аккаунта

        Returns:
            Dict с балансами по валютам: {currency: {free, used, total}}
        """
        try:
            balance = await self.client.get_balance(currency=None)
            result = {}

            # Преобразуем Balance объекты в словари
            for currency, bal_obj in balance.items():
                if isinstance(bal_obj, Balance):
                    result[currency] = {
                        "free": bal_obj.free,
                        "used": bal_obj.used,
                        "total": bal_obj.total,
                    }
                else:
                    # Если уже словарь
                    result[currency] = bal_obj

            return result
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return {}

    async def load_markets(self) -> Dict[str, Dict[str, any]]:
        """
        Загрузка информации о торговых парах

        Returns:
            Dict с информацией о рынках
        """
        try:
            instruments = await self.client.get_instruments()
            markets = {}

            for instrument in instruments:
                markets[instrument.symbol] = {
                    "symbol": instrument.symbol,
                    "base": instrument.base_currency,
                    "quote": instrument.quote_currency,
                    "active": instrument.active,
                    "type": instrument.instrument_type,
                    "limits": {
                        "amount": {
                            "min": instrument.min_quantity,
                            "max": instrument.max_quantity,
                        },
                        "price": {
                            "min": instrument.min_price,
                            "max": instrument.max_price,
                        },
                    },
                    "precision": {
                        "amount": instrument.quantity_step,
                        "price": instrument.price_step,
                    },
                }

            return markets
        except Exception as e:
            logger.error(f"Ошибка загрузки рынков: {e}")
            return {}

    async def create_order(self, **kwargs) -> Dict[str, any]:
        """
        Создание ордера (упрощенный интерфейс)

        Args:
            symbol: Торговая пара
            type: Тип ордера (limit/market)
            side: Сторона (buy/sell)
            amount: Количество
            price: Цена (для лимитных)

        Returns:
            Dict с информацией об ордере
        """
        try:
            # Преобразуем параметры
            symbol = kwargs.get("symbol")
            order_type = kwargs.get("type", "market").upper()
            side = kwargs.get("side", "buy").upper()
            amount = float(kwargs.get("amount", 0))
            price = float(kwargs.get("price", 0)) if kwargs.get("price") else None

            # Создаем OrderRequest
            order_request = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=amount,
                price=price,
            )

            # Размещаем ордер
            response = await self.client.place_order(order_request)

            # Преобразуем ответ в словарь
            return {
                "id": response.order_id,
                "symbol": response.symbol,
                "type": response.order_type,
                "side": response.side,
                "amount": response.quantity,
                "price": response.price,
                "status": response.status,
                "timestamp": response.timestamp,
            }

        except Exception as e:
            logger.error(f"Ошибка создания ордера: {e}")
            raise

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

    # =================== НЕДОСТАЮЩИЕ АБСТРАКТНЫЕ МЕТОДЫ ===================

    async def get_server_time(self) -> datetime:
        """Получение времени сервера"""
        return await self.client.get_server_time()

    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        """Получение истории сделок"""
        return await self.client.get_trade_history(symbol, limit, start_time, end_time)

    async def modify_stop_loss(
        self, symbol: str, order_id: str, stop_loss: float
    ) -> OrderResponse:
        """Модификация стоп-лосса"""
        return await self.client.modify_stop_loss(symbol, order_id, stop_loss)

    async def modify_take_profit(
        self, symbol: str, order_id: str, take_profit: float
    ) -> OrderResponse:
        """Модификация тейк-профита"""
        return await self.client.modify_take_profit(symbol, order_id, take_profit)

    # =================== WEBSOCKET МЕТОДЫ ===================

    async def start_websocket(self, channels: List[str], callback: callable) -> bool:
        """Запуск WebSocket соединения"""
        try:
            return await self.client.start_websocket(channels, callback)
        except Exception as e:
            logger.error(f"Failed to start websocket: {e}")
            return False

    async def stop_websocket(self) -> None:
        """Остановка WebSocket соединения"""
        try:
            await self.client.stop_websocket()
        except Exception as e:
            logger.error(f"Failed to stop websocket: {e}")

    async def subscribe_ticker(self, symbol: str, callback: callable) -> bool:
        """Подписка на тикер через WebSocket"""
        try:
            return await self.client.subscribe_ticker(symbol, callback)
        except Exception as e:
            logger.error(f"Failed to subscribe to ticker {symbol}: {e}")
            return False

    async def subscribe_orderbook(self, symbol: str, callback: callable) -> bool:
        """Подписка на стакан через WebSocket"""
        try:
            return await self.client.subscribe_orderbook(symbol, callback)
        except Exception as e:
            logger.error(f"Failed to subscribe to orderbook {symbol}: {e}")
            return False

    async def subscribe_trades(self, symbol: str, callback: callable) -> bool:
        """Подписка на сделки через WebSocket"""
        try:
            return await self.client.subscribe_trades(symbol, callback)
        except Exception as e:
            logger.error(f"Failed to subscribe to trades {symbol}: {e}")
            return False

    async def subscribe_orders(self, callback: callable) -> bool:
        """Подписка на обновления ордеров через WebSocket"""
        try:
            return await self.client.subscribe_orders(callback)
        except Exception as e:
            logger.error(f"Failed to subscribe to orders: {e}")
            return False

    async def subscribe_positions(self, callback: callable) -> bool:
        """Подписка на обновления позиций через WebSocket"""
        try:
            return await self.client.subscribe_positions(callback)
        except Exception as e:
            logger.error(f"Failed to subscribe to positions: {e}")
            return False

    # =================== АЛИАС ДЛЯ СОВМЕСТИМОСТИ ===================

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Dict = None,
    ) -> List[List]:
        """
        Метод для совместимости с ccxt интерфейсом.
        Проксирует вызов к клиенту.

        Args:
            symbol: Торговый символ
            timeframe: Временной интервал
            since: Начальная временная метка в миллисекундах
            limit: Количество свечей
            params: Дополнительные параметры

        Returns:
            Список свечей в формате [timestamp, open, high, low, close, volume]
        """
        return await self.client.fetch_ohlcv(
            symbol=symbol, timeframe=timeframe, since=since, limit=limit, params=params
        )

    async def get_candles(
        self,
        symbol: str,
        interval_minutes: Union[int, str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Candle]:
        """
        Получение свечей с биржи Bybit

        Args:
            symbol: Торговый символ (например, 'BTCUSDT')
            interval_minutes: Интервал в минутах (1, 5, 15, 30, 60, 240, 1440)
            start_time: Начальное время
            end_time: Конечное время
            limit: Максимальное количество свечей

        Returns:
            Список свечей
        """
        try:
            # Конвертация строкового интервала в минуты если нужно
            interval_minutes_orig = interval_minutes
            if isinstance(interval_minutes, str):
                # Маппинг строковых интервалов в минуты
                str_to_minutes = {
                    "1m": 1,
                    "5m": 5,
                    "15m": 15,
                    "30m": 30,
                    "1h": 60,
                    "60m": 60,
                    "4h": 240,
                    "240m": 240,
                    "1d": 1440,
                    "D": 1440,
                    "1D": 1440,
                }
                interval_minutes = str_to_minutes.get(interval_minutes)
                if not interval_minutes:
                    raise ValueError(
                        f"Unknown interval format: {interval_minutes_orig}"
                    )

            # Проверка кэша
            cache_key = f"{symbol}_{interval_minutes}_{start_time}_{end_time}_{limit}"
            cached_data = self.candles_cache.get(cache_key)

            if cached_data and self._is_cache_valid(cached_data):
                logger.debug(
                    f"Returning cached candles for {symbol}: {len(cached_data['candles'])} items"
                )
                return cached_data["candles"]

            # Конвертация interval_minutes в формат Bybit
            bybit_interval = self.interval_map.get(interval_minutes)
            if not bybit_interval:
                supported = list(self.interval_map.keys())
                raise ValueError(
                    f"Unsupported interval: {interval_minutes}. Supported: {supported}"
                )

            # Подготовка параметров запроса
            params = {
                "category": "linear",  # Для фьючерсов
                "symbol": symbol,
                "interval": bybit_interval,
                "limit": min(limit, 1000),  # Bybit лимит 1000
            }

            # Установка временных границ
            if start_time:
                if isinstance(start_time, datetime):
                    params["start"] = int(start_time.timestamp() * 1000)
                else:
                    # Если уже int - используем как есть
                    params["start"] = int(start_time)

            if end_time:
                if isinstance(end_time, datetime):
                    params["end"] = int(end_time.timestamp() * 1000)
                else:
                    # Если уже int - используем как есть
                    params["end"] = int(end_time)

            logger.debug(
                f"Requesting candles from Bybit: {symbol} {bybit_interval} "
                f"({start_time} - {end_time}) limit={limit}"
            )

            # Запрос к API Bybit
            response = await self.client._make_request(
                method="GET", endpoint="/v5/market/kline", params=params
            )

            if not response or "result" not in response:
                logger.warning(f"Empty response from Bybit for {symbol}")
                return []

            # Парсинг данных
            candles_data = response["result"].get("list", [])

            if not candles_data:
                logger.debug(f"No candles data from Bybit for {symbol}")
                return []

            # Конвертация в объекты Candle
            candles = []

            for candle_data in candles_data:
                try:
                    # Формат Bybit: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
                    # Сохраняем оригинальное значение interval_minutes для Candle

                    # Обработка timestamp - может быть int или уже datetime
                    timestamp_value = candle_data[0]
                    if isinstance(timestamp_value, datetime):
                        timestamp = timestamp_value
                    else:
                        # Если это число, конвертируем из миллисекунд
                        timestamp = datetime.fromtimestamp(int(timestamp_value) / 1000)

                    candle = Candle(
                        symbol=symbol,
                        exchange=self.name,
                        interval_minutes=int(
                            interval_minutes
                        ),  # Убеждаемся что это int
                        timestamp=timestamp,
                        open_price=float(candle_data[1]),
                        high_price=float(candle_data[2]),
                        low_price=float(candle_data[3]),
                        close_price=float(candle_data[4]),
                        volume=float(candle_data[5]),
                        turnover=float(candle_data[6]) if len(candle_data) > 6 else 0.0,
                    )
                    candles.append(candle)

                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse candle for {symbol}: {e}")
                    continue

            # Сортировка по времени (от старых к новым)
            candles.sort(key=lambda x: x.timestamp)

            # Кэширование результата
            if candles:
                self.candles_cache[cache_key] = {
                    "candles": candles,
                    "timestamp": datetime.now(),
                }

            logger.info(
                f"Successfully loaded {len(candles)} candles for {symbol} "
                f"({candles[0].timestamp} - {candles[-1].timestamp})"
                if candles
                else f"No candles for {symbol}"
            )

            return candles

        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            raise

    def _is_cache_valid(self, cached_data: Dict) -> bool:
        """Проверка валидности кэша"""
        cache_age = (datetime.now() - cached_data["timestamp"]).total_seconds()
        return cache_age < self.cache_ttl

    async def get_recent_candles(
        self, symbol: str, interval_minutes: int, count: int = 100
    ) -> List[Candle]:
        """Получение последних свечей"""

        end_time = datetime.now()
        start_time = end_time - timedelta(
            minutes=interval_minutes * count * 2
        )  # С запасом

        candles = await self.get_candles(
            symbol=symbol,
            interval_minutes=interval_minutes,
            start_time=start_time,
            end_time=end_time,
            limit=count,
        )

        # Возвращаем последние count свечей
        return candles[-count:] if len(candles) > count else candles


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
