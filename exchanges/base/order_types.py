"""
Стандартизированные типы ордеров для мульти-биржевой системы BOT_Trading v3.0

Содержит унифицированные типы ордеров, статусы и запросы для всех поддерживаемых бирж.
Обеспечивает единый интерфейс для работы с различными типами ордеров на разных биржах.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class OrderType(Enum):
    """Типы ордеров"""
    MARKET = "Market"                   # Рыночный ордер
    LIMIT = "Limit"                     # Лимитный ордер
    STOP_MARKET = "StopMarket"          # Стоп рыночный
    STOP_LIMIT = "StopLimit"            # Стоп лимитный
    TAKE_PROFIT_MARKET = "TakeProfitMarket"  # Тейк профит рыночный
    TAKE_PROFIT_LIMIT = "TakeProfitLimit"    # Тейк профит лимитный
    TRAILING_STOP = "TrailingStop"      # Трейлинг стоп
    POST_ONLY = "PostOnly"              # Только постановка (maker)
    REDUCE_ONLY = "ReduceOnly"          # Только уменьшение позиции
    
    # Условные ордеры
    CONDITIONAL = "Conditional"         # Условный ордер
    OCO = "OCO"                        # One-Cancels-Other
    BRACKET = "Bracket"                # Bracket ордер (SL + TP)


class OrderSide(Enum):
    """Сторона ордера"""
    BUY = "Buy"                        # Покупка
    SELL = "Sell"                      # Продажа


class OrderStatus(Enum):
    """Статусы ордера"""
    NEW = "New"                        # Новый ордер
    PARTIALLY_FILLED = "PartiallyFilled"  # Частично исполнен
    FILLED = "Filled"                  # Полностью исполнен
    CANCELLED = "Cancelled"            # Отменен
    REJECTED = "Rejected"              # Отклонен
    EXPIRED = "Expired"                # Истек
    PENDING = "Pending"                # Ожидает
    TRIGGERED = "Triggered"            # Сработал триггер
    DEACTIVATED = "Deactivated"        # Деактивирован
    
    # Специальные статусы
    PENDING_CANCEL = "PendingCancel"   # Ожидает отмены
    PENDING_NEW = "PendingNew"         # Ожидает создания


class TimeInForce(Enum):
    """Время действия ордера"""
    GTC = "GTC"                        # Good Till Cancelled
    IOC = "IOC"                        # Immediate Or Cancel
    FOK = "FOK"                        # Fill Or Kill
    GTX = "GTX"                        # Good Till Crossing (Post Only)
    GTD = "GTD"                        # Good Till Date


class PositionSide(Enum):
    """Сторона позиции"""
    LONG = "Long"                      # Длинная позиция
    SHORT = "Short"                    # Короткая позиция
    BOTH = "Both"                      # Обе стороны (hedge mode)


class TriggerDirection(Enum):
    """Направление триггера"""
    RISING = "Rising"                  # При росте цены
    FALLING = "Falling"                # При падении цены


class ExecutionType(Enum):
    """Тип исполнения"""
    NEW = "NEW"                        # Новый ордер
    CANCELED = "CANCELED"              # Отменен
    REPLACED = "REPLACED"              # Заменен
    REJECTED = "REJECTED"              # Отклонен
    TRADE = "TRADE"                    # Сделка
    EXPIRED = "EXPIRED"                # Истек


@dataclass
class OrderRequest:
    """
    Запрос на создание ордера
    
    Унифицированная структура для размещения ордеров на всех биржах
    """
    symbol: str                        # Символ инструмента
    side: OrderSide                    # Сторона ордера
    order_type: OrderType             # Тип ордера
    quantity: float                    # Количество
    
    # Цены
    price: Optional[float] = None      # Цена (для лимитных ордеров)
    stop_price: Optional[float] = None # Стоп цена
    trigger_price: Optional[float] = None # Цена триггера
    
    # Время действия
    time_in_force: TimeInForce = TimeInForce.GTC
    expire_time: Optional[datetime] = None  # Время истечения для GTD
    
    # Клиентские идентификаторы
    client_order_id: Optional[str] = None   # Клиентский ID
    order_link_id: Optional[str] = None     # ID связанного ордера
    
    # Специальные параметры
    reduce_only: bool = False          # Только уменьшение позиции
    close_on_trigger: bool = False     # Закрытие по триггеру
    position_idx: int = 0              # Индекс позиции (для hedge mode)
    
    # SL/TP параметры
    stop_loss: Optional[float] = None   # Stop Loss цена
    take_profit: Optional[float] = None # Take Profit цена
    sl_trigger_by: Optional[str] = None # Триггер SL (LastPrice/IndexPrice/MarkPrice)
    tp_trigger_by: Optional[str] = None # Триггер TP
    
    # Трейлинг стоп
    trailing_stop: Optional[float] = None      # Трейлинг стоп
    trailing_stop_pct: Optional[float] = None  # Трейлинг стоп в процентах
    active_price: Optional[float] = None       # Цена активации
    
    # Дополнительные параметры
    margin_mode: Optional[str] = None   # Режим маржи (ISOLATED/CROSS)
    leverage: Optional[float] = None    # Плечо
    
    # Метаданные
    exchange_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        data = {
            "symbol": self.symbol,
            "side": self.side.value,
            "orderType": self.order_type.value,
            "qty": str(self.quantity),
            "timeInForce": self.time_in_force.value
        }
        
        if self.price is not None:
            data["price"] = str(self.price)
        if self.stop_price is not None:
            data["stopPrice"] = str(self.stop_price)
        if self.trigger_price is not None:
            data["triggerPrice"] = str(self.trigger_price)
        if self.client_order_id:
            data["orderLinkId"] = self.client_order_id
        if self.reduce_only:
            data["reduceOnly"] = True
        if self.close_on_trigger:
            data["closeOnTrigger"] = True
        if self.position_idx != 0:
            data["positionIdx"] = self.position_idx
        
        # Добавляем параметры SL/TP
        if self.stop_loss is not None:
            data["stopLoss"] = str(self.stop_loss)
        if self.take_profit is not None:
            data["takeProfit"] = str(self.take_profit)
        
        # Добавляем exchange-специфичные параметры
        data.update(self.exchange_params)
        
        return data
    
    def validate(self) -> List[str]:
        """Валидация запроса ордера"""
        errors = []
        
        if not self.symbol:
            errors.append("Symbol is required")
        
        if self.quantity <= 0:
            errors.append("Quantity must be positive")
        
        if self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
            if self.price is None or self.price <= 0:
                errors.append(f"{self.order_type.value} order requires valid price")
        
        if self.order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT]:
            if self.stop_price is None or self.stop_price <= 0:
                errors.append(f"{self.order_type.value} order requires valid stop price")
        
        if self.time_in_force == TimeInForce.GTD and self.expire_time is None:
            errors.append("GTD order requires expire time")
        
        return errors
    
    def is_valid(self) -> bool:
        """Проверка валидности запроса"""
        return len(self.validate()) == 0


@dataclass
class OrderResponse:
    """
    Ответ на запрос ордера
    
    Унифицированная структура ответа от биржи
    """
    success: bool                      # Успешность операции
    order_id: Optional[str] = None     # ID ордера
    client_order_id: Optional[str] = None  # Клиентский ID
    
    # Статус ордера
    status: Optional[OrderStatus] = None
    message: Optional[str] = None      # Сообщение об ошибке
    
    # Параметры ордера
    symbol: Optional[str] = None
    side: Optional[OrderSide] = None
    order_type: Optional[OrderType] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    filled_quantity: Optional[float] = None
    avg_price: Optional[float] = None
    
    # Время
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    
    # Комиссии
    commission: Optional[float] = None
    commission_asset: Optional[str] = None
    
    # Дополнительная информация
    exchange_data: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    @classmethod
    def success_response(cls,
                        order_id: str,
                        symbol: str,
                        side: OrderSide,
                        order_type: OrderType,
                        quantity: float,
                        **kwargs) -> 'OrderResponse':
        """Создание успешного ответа"""
        return cls(
            success=True,
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            status=OrderStatus.NEW,
            **kwargs
        )
    
    @classmethod
    def error_response(cls,
                      error_message: str,
                      error_code: Optional[str] = None,
                      **kwargs) -> 'OrderResponse':
        """Создание ответа с ошибкой"""
        return cls(
            success=False,
            message=error_message,
            error_code=error_code,
            error_message=error_message,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            "success": self.success,
            "orderId": self.order_id,
            "clientOrderId": self.client_order_id,
            "status": self.status.value if self.status else None,
            "message": self.message,
            "symbol": self.symbol,
            "side": self.side.value if self.side else None,
            "orderType": self.order_type.value if self.order_type else None,
            "quantity": self.quantity,
            "price": self.price,
            "filledQty": self.filled_quantity,
            "avgPrice": self.avg_price,
            "commission": self.commission,
            "commissionAsset": self.commission_asset,
            "createdTime": self.created_time.isoformat() if self.created_time else None,
            "updatedTime": self.updated_time.isoformat() if self.updated_time else None,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "exchangeData": self.exchange_data
        }


@dataclass
class ConditionalOrderParams:
    """Параметры условного ордера"""
    trigger_condition: str             # Условие триггера
    trigger_price: float               # Цена триггера
    trigger_direction: TriggerDirection # Направление триггера
    trigger_by: str = "LastPrice"      # Тип цены для триггера
    
    # OCO параметры
    oco_stop_price: Optional[float] = None    # Стоп цена для OCO
    oco_limit_price: Optional[float] = None   # Лимит цена для OCO
    oco_time_in_force: TimeInForce = TimeInForce.GTC


@dataclass
class BracketOrderParams:
    """Параметры bracket ордера (SL + TP)"""
    stop_loss_price: float             # Цена Stop Loss
    take_profit_price: float           # Цена Take Profit
    
    # Типы ордеров SL/TP
    sl_order_type: OrderType = OrderType.STOP_MARKET
    tp_order_type: OrderType = OrderType.TAKE_PROFIT_MARKET
    
    # Триггеры
    sl_trigger_by: str = "LastPrice"
    tp_trigger_by: str = "LastPrice"
    
    # Время действия
    sl_time_in_force: TimeInForce = TimeInForce.GTC
    tp_time_in_force: TimeInForce = TimeInForce.GTC


class OrderBuilder:
    """
    Построитель ордеров для упрощения создания запросов
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.reset()
    
    def reset(self) -> 'OrderBuilder':
        """Сброс параметров"""
        self._side = None
        self._order_type = None
        self._quantity = None
        self._price = None
        self._stop_price = None
        self._time_in_force = TimeInForce.GTC
        self._client_order_id = None
        self._reduce_only = False
        self._close_on_trigger = False
        self._position_idx = 0
        self._stop_loss = None
        self._take_profit = None
        self._exchange_params = {}
        return self
    
    def buy(self, quantity: float) -> 'OrderBuilder':
        """Покупка"""
        self._side = OrderSide.BUY
        self._quantity = quantity
        return self
    
    def sell(self, quantity: float) -> 'OrderBuilder':
        """Продажа"""
        self._side = OrderSide.SELL
        self._quantity = quantity
        return self
    
    def market(self) -> 'OrderBuilder':
        """Рыночный ордер"""
        self._order_type = OrderType.MARKET
        return self
    
    def limit(self, price: float) -> 'OrderBuilder':
        """Лимитный ордер"""
        self._order_type = OrderType.LIMIT
        self._price = price
        return self
    
    def stop_market(self, stop_price: float) -> 'OrderBuilder':
        """Стоп рыночный ордер"""
        self._order_type = OrderType.STOP_MARKET
        self._stop_price = stop_price
        return self
    
    def stop_limit(self, stop_price: float, price: float) -> 'OrderBuilder':
        """Стоп лимитный ордер"""
        self._order_type = OrderType.STOP_LIMIT
        self._stop_price = stop_price
        self._price = price
        return self
    
    def ioc(self) -> 'OrderBuilder':
        """Immediate Or Cancel"""
        self._time_in_force = TimeInForce.IOC
        return self
    
    def fok(self) -> 'OrderBuilder':
        """Fill Or Kill"""
        self._time_in_force = TimeInForce.FOK
        return self
    
    def post_only(self) -> 'OrderBuilder':
        """Post Only (GTX)"""
        self._time_in_force = TimeInForce.GTX
        return self
    
    def client_id(self, client_id: str) -> 'OrderBuilder':
        """Клиентский ID"""
        self._client_order_id = client_id
        return self
    
    def reduce_only(self, enable: bool = True) -> 'OrderBuilder':
        """Только уменьшение позиции"""
        self._reduce_only = enable
        return self
    
    def close_on_trigger(self, enable: bool = True) -> 'OrderBuilder':
        """Закрытие по триггеру"""
        self._close_on_trigger = enable
        return self
    
    def stop_loss(self, sl_price: float) -> 'OrderBuilder':
        """Stop Loss"""
        self._stop_loss = sl_price
        return self
    
    def take_profit(self, tp_price: float) -> 'OrderBuilder':
        """Take Profit"""
        self._take_profit = tp_price
        return self
    
    def with_sl_tp(self, sl_price: float, tp_price: float) -> 'OrderBuilder':
        """SL и TP одновременно"""
        self._stop_loss = sl_price
        self._take_profit = tp_price
        return self
    
    def exchange_param(self, key: str, value: Any) -> 'OrderBuilder':
        """Добавление exchange-специфичного параметра"""
        self._exchange_params[key] = value
        return self
    
    def build(self) -> OrderRequest:
        """Построение запроса ордера"""
        if not all([self._side, self._order_type, self._quantity]):
            raise ValueError("Side, order_type and quantity are required")
        
        return OrderRequest(
            symbol=self.symbol,
            side=self._side,
            order_type=self._order_type,
            quantity=self._quantity,
            price=self._price,
            stop_price=self._stop_price,
            time_in_force=self._time_in_force,
            client_order_id=self._client_order_id,
            reduce_only=self._reduce_only,
            close_on_trigger=self._close_on_trigger,
            position_idx=self._position_idx,
            stop_loss=self._stop_loss,
            take_profit=self._take_profit,
            exchange_params=self._exchange_params.copy()
        )


# =================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===================

def create_market_buy_order(symbol: str, quantity: float, **kwargs) -> OrderRequest:
    """Создание рыночного ордера на покупку"""
    return OrderBuilder(symbol).buy(quantity).market().build()


def create_market_sell_order(symbol: str, quantity: float, **kwargs) -> OrderRequest:
    """Создание рыночного ордера на продажу"""
    return OrderBuilder(symbol).sell(quantity).market().build()


def create_limit_buy_order(symbol: str, quantity: float, price: float, **kwargs) -> OrderRequest:
    """Создание лимитного ордера на покупку"""
    return OrderBuilder(symbol).buy(quantity).limit(price).build()


def create_limit_sell_order(symbol: str, quantity: float, price: float, **kwargs) -> OrderRequest:
    """Создание лимитного ордера на продажу"""
    return OrderBuilder(symbol).sell(quantity).limit(price).build()


def create_stop_loss_order(symbol: str, quantity: float, stop_price: float, **kwargs) -> OrderRequest:
    """Создание Stop Loss ордера"""
    side = OrderSide.SELL if quantity > 0 else OrderSide.BUY
    return OrderBuilder(symbol).side(side).stop_market(stop_price).reduce_only().build()


def create_take_profit_order(symbol: str, quantity: float, price: float, **kwargs) -> OrderRequest:
    """Создание Take Profit ордера"""
    side = OrderSide.SELL if quantity > 0 else OrderSide.BUY
    return OrderBuilder(symbol).side(side).limit(price).reduce_only().build()


def validate_order_params(symbol: str, side: OrderSide, order_type: OrderType, 
                         quantity: float, price: Optional[float] = None,
                         stop_price: Optional[float] = None) -> List[str]:
    """Валидация параметров ордера"""
    errors = []
    
    if not symbol:
        errors.append("Symbol is required")
    
    if quantity <= 0:
        errors.append("Quantity must be positive")
    
    if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
        if price is None or price <= 0:
            errors.append(f"{order_type.value} requires valid price")
    
    if order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT]:
        if stop_price is None or stop_price <= 0:
            errors.append(f"{order_type.value} requires valid stop price")
    
    return errors


def normalize_order_status(exchange_status: str, exchange_name: str) -> OrderStatus:
    """Нормализация статуса ордера с разных бирж"""
    status_map = {
        # Общие статусы
        "new": OrderStatus.NEW,
        "open": OrderStatus.NEW,
        "pending": OrderStatus.PENDING,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "partial": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "complete": OrderStatus.FILLED,
        "cancelled": OrderStatus.CANCELLED,
        "canceled": OrderStatus.CANCELLED,
        "rejected": OrderStatus.REJECTED,
        "expired": OrderStatus.EXPIRED,
        "triggered": OrderStatus.TRIGGERED,
        
        # Bybit специфичные статусы
        "created": OrderStatus.NEW,
        "untriggered": OrderStatus.PENDING,
        "deactivated": OrderStatus.DEACTIVATED,
        "active": OrderStatus.NEW,
        
        # Binance специфичные статусы
        "pending_new": OrderStatus.PENDING_NEW,
        "pending_cancel": OrderStatus.PENDING_CANCEL
    }
    
    normalized = exchange_status.lower().replace(" ", "_")
    return status_map.get(normalized, OrderStatus.NEW)


def get_order_type_mapping(exchange_name: str) -> Dict[OrderType, str]:
    """Получение маппинга типов ордеров для конкретной биржи"""
    if exchange_name.lower() == "bybit":
        return {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit", 
            OrderType.STOP_MARKET: "Market",
            OrderType.STOP_LIMIT: "Limit",
            OrderType.TAKE_PROFIT_MARKET: "Market",
            OrderType.TAKE_PROFIT_LIMIT: "Limit",
            OrderType.CONDITIONAL: "Conditional"
        }
    elif exchange_name.lower() == "binance":
        return {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP_MARKET: "STOP_MARKET", 
            OrderType.STOP_LIMIT: "STOP_LOSS_LIMIT",
            OrderType.TAKE_PROFIT_MARKET: "TAKE_PROFIT_MARKET",
            OrderType.TAKE_PROFIT_LIMIT: "TAKE_PROFIT_LIMIT"
        }
    
    # Стандартные значения
    return {order_type: order_type.value for order_type in OrderType}


# Константы
DEFAULT_ORDER_TYPES = [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP_MARKET, OrderType.STOP_LIMIT]
DEFAULT_TIME_IN_FORCE = [TimeInForce.GTC, TimeInForce.IOC, TimeInForce.FOK]