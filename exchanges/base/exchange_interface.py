"""
Базовый интерфейс для всех криптовалютных бирж в BOT_Trading v3.0

Определяет унифицированный API для работы с различными биржами:
- Спотовая и фьючерсная торговля
- Управление ордерами и позициями  
- Получение рыночных данных
- WebSocket подключения
- Управление рисками
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .models import (
    Position, Order, Balance, Instrument, Ticker, OrderBook, 
    Kline, AccountInfo, ExchangeInfo
)
from .order_types import OrderRequest, OrderResponse, OrderType, OrderSide


class ExchangeType(Enum):
    """Типы бирж"""
    SPOT = "spot"
    FUTURES = "futures" 
    BOTH = "both"


class ExchangeStatus(Enum):
    """Статусы биржи"""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    RESTRICTED = "restricted"


@dataclass
class ExchangeCapabilities:
    """Возможности биржи"""
    # Типы торговли
    spot_trading: bool = False
    futures_trading: bool = False
    margin_trading: bool = False
    
    # Типы ордеров
    market_orders: bool = True
    limit_orders: bool = True
    stop_orders: bool = False
    stop_limit_orders: bool = False
    
    # WebSocket
    websocket_public: bool = False
    websocket_private: bool = False
    
    # Дополнительные возможности
    position_management: bool = False
    leverage_trading: bool = False
    auto_borrow: bool = False
    
    # Лимиты
    max_leverage: float = 1.0
    min_order_size: float = 0.0001
    max_order_size: float = 1000000.0
    
    # Rate limits (requests per minute)
    rate_limit_public: int = 1200
    rate_limit_private: int = 600


class BaseExchangeInterface(ABC):
    """
    Базовый интерфейс для всех бирж
    
    Определяет стандартный набор методов, которые должны быть
    реализованы каждой биржей для интеграции с системой торговли.
    """
    
    def __init__(self, 
                 api_key: str,
                 api_secret: str, 
                 sandbox: bool = False,
                 timeout: int = 30):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.timeout = timeout
        self._connected = False
        self._last_request_time: Optional[datetime] = None
        
    # =================== ОСНОВНЫЕ СВОЙСТВА ===================
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Название биржи"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> ExchangeCapabilities:
        """Возможности биржи"""
        pass
    
    @property
    def is_connected(self) -> bool:
        """Статус подключения к бирже"""
        return self._connected
    
    # =================== ПОДКЛЮЧЕНИЕ И АУТЕНТИФИКАЦИЯ ===================
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Установка соединения с биржей
        
        Returns:
            True если соединение успешно установлено
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Отключение от биржи"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Тестирование соединения с биржей
        
        Returns:
            True если соединение работает
        """
        pass
    
    @abstractmethod
    async def get_server_time(self) -> datetime:
        """Получение времени сервера биржи"""
        pass
    
    # =================== ИНФОРМАЦИЯ О БИРЖЕ ===================
    
    @abstractmethod
    async def get_exchange_info(self) -> ExchangeInfo:
        """Получение общей информации о бирже"""
        pass
    
    @abstractmethod
    async def get_instruments(self, 
                            category: Optional[str] = None) -> List[Instrument]:
        """
        Получение списка торговых инструментов
        
        Args:
            category: Категория инструментов (spot, linear, inverse, etc.)
        """
        pass
    
    @abstractmethod
    async def get_instrument_info(self, symbol: str) -> Instrument:
        """Получение информации о конкретном инструменте"""
        pass
    
    # =================== АККАУНТ И БАЛАНСЫ ===================
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Получение информации об аккаунте"""
        pass
    
    @abstractmethod
    async def get_balances(self, 
                         account_type: Optional[str] = None) -> List[Balance]:
        """
        Получение балансов аккаунта
        
        Args:
            account_type: Тип аккаунта (spot, contract, etc.)
        """
        pass
    
    @abstractmethod 
    async def get_balance(self, 
                        currency: str,
                        account_type: Optional[str] = None) -> Balance:
        """Получение баланса конкретной валюты"""
        pass
    
    # =================== РЫНОЧНЫЕ ДАННЫЕ ===================
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Получение тикера инструмента"""
        pass
    
    @abstractmethod
    async def get_tickers(self, 
                        category: Optional[str] = None) -> List[Ticker]:
        """Получение тикеров всех инструментов"""
        pass
    
    @abstractmethod
    async def get_orderbook(self, 
                          symbol: str, 
                          limit: int = 25) -> OrderBook:
        """Получение стакана ордеров"""
        pass
    
    @abstractmethod
    async def get_klines(self,
                       symbol: str,
                       interval: str,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       limit: int = 500) -> List[Kline]:
        """
        Получение свечных данных
        
        Args:
            symbol: Торговая пара
            interval: Интервал (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            start_time: Начальное время
            end_time: Конечное время  
            limit: Количество свечей
        """
        pass
    
    # =================== УПРАВЛЕНИЕ ОРДЕРАМИ ===================
    
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Размещение ордера"""
        pass
    
    @abstractmethod
    async def cancel_order(self, 
                         symbol: str, 
                         order_id: str) -> OrderResponse:
        """Отмена ордера"""
        pass
    
    @abstractmethod
    async def cancel_all_orders(self, 
                              symbol: Optional[str] = None) -> List[OrderResponse]:
        """Отмена всех ордеров"""
        pass
    
    @abstractmethod
    async def modify_order(self,
                         symbol: str,
                         order_id: str,
                         quantity: Optional[float] = None,
                         price: Optional[float] = None) -> OrderResponse:
        """Модификация ордера"""
        pass
    
    @abstractmethod
    async def get_order(self, 
                      symbol: str, 
                      order_id: str) -> Order:
        """Получение информации об ордере"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, 
                            symbol: Optional[str] = None) -> List[Order]:
        """Получение активных ордеров"""
        pass
    
    @abstractmethod
    async def get_order_history(self,
                              symbol: Optional[str] = None,
                              start_time: Optional[datetime] = None,
                              end_time: Optional[datetime] = None,
                              limit: int = 100) -> List[Order]:
        """Получение истории ордеров"""
        pass
    
    # =================== УПРАВЛЕНИЕ ПОЗИЦИЯМИ ===================
    
    @abstractmethod
    async def get_positions(self, 
                          symbol: Optional[str] = None) -> List[Position]:
        """Получение открытых позиций"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Получение позиции по символу"""
        pass
    
    @abstractmethod
    async def close_position(self, 
                           symbol: str,
                           quantity: Optional[float] = None) -> OrderResponse:
        """Закрытие позиции"""
        pass
    
    @abstractmethod
    async def set_leverage(self, 
                         symbol: str, 
                         leverage: float) -> bool:
        """Установка плеча для символа"""
        pass
    
    @abstractmethod
    async def set_position_mode(self, 
                              symbol: str, 
                              hedge_mode: bool) -> bool:
        """Установка режима позиции (hedge/one-way)"""
        pass
    
    # =================== STOP LOSS / TAKE PROFIT ===================
    
    @abstractmethod
    async def set_stop_loss(self,
                          symbol: str,
                          stop_price: float,
                          quantity: Optional[float] = None) -> OrderResponse:
        """Установка Stop Loss"""
        pass
    
    @abstractmethod
    async def set_take_profit(self,
                            symbol: str, 
                            take_price: float,
                            quantity: Optional[float] = None) -> OrderResponse:
        """Установка Take Profit"""
        pass
    
    @abstractmethod
    async def modify_stop_loss(self,
                             symbol: str,
                             new_stop_price: float) -> OrderResponse:
        """Модификация Stop Loss"""
        pass
    
    @abstractmethod
    async def modify_take_profit(self,
                               symbol: str,
                               new_take_price: float) -> OrderResponse:
        """Модификация Take Profit"""
        pass
    
    # =================== ИСТОРИЯ СДЕЛОК ===================
    
    @abstractmethod
    async def get_trade_history(self,
                              symbol: Optional[str] = None,
                              start_time: Optional[datetime] = None, 
                              end_time: Optional[datetime] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Получение истории сделок"""
        pass
    
    # =================== WEBSOCKET ===================
    
    @abstractmethod
    async def start_websocket(self, 
                            channels: List[str],
                            callback: callable) -> bool:
        """Запуск WebSocket подключения"""
        pass
    
    @abstractmethod
    async def stop_websocket(self) -> None:
        """Остановка WebSocket подключения"""
        pass
    
    @abstractmethod
    async def subscribe_ticker(self, 
                             symbol: str, 
                             callback: callable) -> bool:
        """Подписка на тикер через WebSocket"""
        pass
    
    @abstractmethod
    async def subscribe_orderbook(self, 
                                symbol: str, 
                                callback: callable) -> bool:
        """Подписка на стакан через WebSocket"""
        pass
    
    @abstractmethod
    async def subscribe_trades(self, 
                             symbol: str, 
                             callback: callable) -> bool:
        """Подписка на сделки через WebSocket"""
        pass
    
    @abstractmethod
    async def subscribe_orders(self, callback: callable) -> bool:
        """Подписка на обновления ордеров через WebSocket"""
        pass
    
    @abstractmethod
    async def subscribe_positions(self, callback: callable) -> bool:
        """Подписка на обновления позиций через WebSocket"""
        pass
    
    # =================== УТИЛИТЫ ===================
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """
        Получение торговых комиссий
        
        Returns:
            Dict с maker и taker комиссиями
        """
        return {
            "maker": 0.001,  # 0.1% по умолчанию
            "taker": 0.001   # 0.1% по умолчанию  
        }
    
    def normalize_symbol(self, symbol: str) -> str:
        """Нормализация символа под формат биржи"""
        return symbol.upper().replace("/", "")
    
    def validate_order_size(self, 
                          symbol: str, 
                          quantity: float) -> bool:
        """Валидация размера ордера"""
        return (quantity >= self.capabilities.min_order_size and 
                quantity <= self.capabilities.max_order_size)
    
    async def wait_for_rate_limit(self) -> None:
        """Ожидание для соблюдения rate limit"""
        if self._last_request_time:
            time_diff = datetime.now() - self._last_request_time
            min_interval = timedelta(seconds=60 / self.capabilities.rate_limit_private)
            
            if time_diff < min_interval:
                sleep_time = (min_interval - time_diff).total_seconds()
                await asyncio.sleep(sleep_time)
        
        self._last_request_time = datetime.now()
    
    # =================== CONTEXT MANAGERS ===================
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    def __str__(self) -> str:
        return f"{self.name}Exchange(connected={self.is_connected}, sandbox={self.sandbox})"
    
    def __repr__(self) -> str:
        return self.__str__()


# Вспомогательные функции для работы с интерфейсом

def get_exchange_capabilities(exchange_name: str) -> ExchangeCapabilities:
    """Получение возможностей биржи по имени"""
    # Будет реализовано в registry.py
    pass


async def test_exchange_connection(exchange: BaseExchangeInterface) -> Dict[str, Any]:
    """
    Тестирование подключения к бирже
    
    Returns:
        Dict с результатами тестирования
    """
    result = {
        "exchange": exchange.name,
        "connected": False,
        "server_time": None,
        "latency_ms": 0,
        "error": None
    }
    
    try:
        start_time = datetime.now()
        
        # Тест подключения
        connected = await exchange.test_connection()
        result["connected"] = connected
        
        if connected:
            # Тест получения времени сервера
            server_time = await exchange.get_server_time()
            result["server_time"] = server_time.isoformat()
            
            # Расчет латентности
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds() * 1000
            result["latency_ms"] = round(latency, 2)
            
    except Exception as e:
        result["error"] = str(e)
    
    return result