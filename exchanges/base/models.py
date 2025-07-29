"""
Унифицированные модели данных для мульти-биржевой системы BOT_Trading v3.0

Содержит стандартизированные структуры данных для всех поддерживаемых бирж:
- Позиции, ордеры, балансы
- Рыночные данные (тикеры, стаканы, свечи)
- Информация об аккаунтах и инструментах
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum

# =================== БАЗОВЫЕ ТИПЫ ===================

@dataclass
class Instrument:
    """Торговый инструмент"""
    symbol: str                          # Символ инструмента (BTCUSDT)
    base_currency: str                   # Базовая валюта (BTC)
    quote_currency: str                  # Котируемая валюта (USDT)
    category: str                        # Категория (spot, linear, inverse)
    
    # Параметры торговли
    min_order_qty: float = 0.0          # Минимальный размер ордера
    max_order_qty: float = 1000000.0    # Максимальный размер ордера
    qty_step: float = 0.001             # Шаг изменения количества
    
    price_precision: int = 4             # Точность цены
    qty_precision: int = 3               # Точность количества
    
    min_price: float = 0.0001           # Минимальная цена
    max_price: float = 1000000.0        # Максимальная цена  
    tick_size: float = 0.01             # Минимальный шаг цены
    
    # Статус инструмента
    status: str = "Trading"             # Статус торговли
    is_tradable: bool = True            # Доступен для торговли
    
    # Дополнительная информация
    contract_type: Optional[str] = None  # Тип контракта (для фьючерсов)
    settlement_coin: Optional[str] = None # Валюта расчетов
    launch_time: Optional[datetime] = None # Время запуска
    delivery_time: Optional[datetime] = None # Время поставки
    
    # Маржинальная торговля
    margin_trading: bool = False        # Поддержка маржинальной торговли
    max_leverage: float = 1.0          # Максимальное плечо
    
    # Метаданные
    exchange_info: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class Balance:
    """Баланс аккаунта"""
    currency: str                       # Валюта
    total: float                        # Общий баланс
    available: float                    # Доступный баланс
    frozen: float = 0.0                # Замороженный баланс
    
    # Дополнительные поля для маржинальных аккаунтов
    borrowed: float = 0.0              # Заемные средства
    interest: float = 0.0              # Проценты
    net_asset: float = 0.0             # Чистые активы
    
    # Метаданные
    account_type: str = "spot"         # Тип аккаунта
    last_update: Optional[datetime] = None
    
    @property
    def free(self) -> float:
        """Свободный баланс (алиас для available)"""
        return self.available
    
    @property
    def locked(self) -> float:
        """Заблокированный баланс (алиас для frozen)"""
        return self.frozen


@dataclass
class Position:
    """Торговая позиция"""
    symbol: str                         # Символ инструмента
    side: str                          # Сторона позиции (Buy/Sell/None)
    size: float                        # Размер позиции
    entry_price: float                 # Цена входа
    mark_price: float                  # Маркировочная цена
    
    # PnL
    unrealised_pnl: float = 0.0        # Нереализованная прибыль/убыток
    realised_pnl: float = 0.0          # Реализованная прибыль/убыток
    percentage_pnl: float = 0.0        # PnL в процентах
    
    # Маржа и плечо
    leverage: float = 1.0              # Плечо
    margin: float = 0.0                # Маржа
    position_margin: float = 0.0       # Позиционная маржа
    initial_margin: float = 0.0        # Начальная маржа
    maintenance_margin: float = 0.0    # Поддерживающая маржа
    
    # Ликвидация
    liq_price: Optional[float] = None  # Цена ликвидации
    bust_price: Optional[float] = None # Цена банкротства
    
    # Stop Loss / Take Profit
    stop_loss: Optional[float] = None   # Stop Loss цена
    take_profit: Optional[float] = None # Take Profit цена
    trailing_stop: Optional[float] = None # Trailing Stop
    
    # Режимы
    position_mode: str = "MergedSingle" # Режим позиции
    auto_add_margin: bool = False      # Автодобавление маржи
    
    # Время
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    
    # Метаданные
    position_idx: int = 0              # Индекс позиции (для hedge mode)
    risk_id: int = 0                   # ID риска
    risk_limit_value: float = 0.0      # Лимит риска
    
    @property
    def is_long(self) -> bool:
        """Является ли позиция длинной"""
        return self.side.lower() in ["buy", "long"] and self.size > 0
    
    @property
    def is_short(self) -> bool:
        """Является ли позиция короткой"""
        return self.side.lower() in ["sell", "short"] and self.size > 0
    
    @property 
    def is_open(self) -> bool:
        """Открыта ли позиция"""
        return abs(self.size) > 0
    
    @property
    def position_value(self) -> float:
        """Стоимость позиции"""
        return abs(self.size * self.mark_price)


@dataclass
class Order:
    """Торговый ордер"""
    order_id: str                      # ID ордера
    client_order_id: Optional[str]     # Клиентский ID ордера
    symbol: str                        # Символ инструмента
    side: str                          # Сторона (Buy/Sell)
    order_type: str                    # Тип ордера (Market/Limit/etc)
    
    # Количество и цена
    quantity: float                    # Количество
    price: float                       # Цена (0 для рыночных ордеров)
    filled_quantity: float = 0.0       # Исполненное количество
    remaining_quantity: float = 0.0     # Оставшееся количество
    
    # Статус
    status: str = "New"                # Статус ордера
    time_in_force: str = "GTC"         # Время действия ордера
    
    # Цены исполнения
    avg_price: float = 0.0             # Средняя цена исполнения
    cumulative_quote_qty: float = 0.0  # Накопленная сумма в котируемой валюте
    
    # Условные ордеры
    stop_price: Optional[float] = None  # Стоп-цена
    trigger_price: Optional[float] = None # Цена срабатывания
    trigger_direction: Optional[str] = None # Направление триггера
    
    # Комиссии
    commission: float = 0.0            # Комиссия
    commission_asset: str = ""         # Валюта комиссии
    
    # Время
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    
    # Дополнительные параметры
    reduce_only: bool = False          # Только уменьшение позиции
    close_on_trigger: bool = False     # Закрытие по триггеру
    position_idx: int = 0              # Индекс позиции
    
    # Метаданные биржи
    exchange_order_id: Optional[str] = None
    exchange_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_filled(self) -> bool:
        """Полностью ли исполнен ордер"""
        return self.status.lower() in ["filled", "completely_filled"]
    
    @property  
    def is_active(self) -> bool:
        """Активен ли ордер"""
        return self.status.lower() in ["new", "partially_filled", "accepted"]
    
    @property
    def is_cancelled(self) -> bool:
        """Отменен ли ордер"""
        return self.status.lower() in ["cancelled", "canceled", "rejected"]
    
    @property
    def fill_percentage(self) -> float:
        """Процент исполнения ордера"""
        if self.quantity == 0:
            return 0.0
        return (self.filled_quantity / self.quantity) * 100


@dataclass
class Ticker:
    """Тикер инструмента"""
    symbol: str                        # Символ инструмента
    last_price: float                  # Последняя цена
    bid_price: float                   # Цена покупки
    ask_price: float                   # Цена продажи
    
    # Изменения за 24 часа
    high_24h: float = 0.0              # Максимум за 24ч
    low_24h: float = 0.0               # Минимум за 24ч
    volume_24h: float = 0.0            # Объем за 24ч
    quote_volume_24h: float = 0.0      # Объем в котируемой валюте за 24ч
    price_change_24h: float = 0.0      # Изменение цены за 24ч
    price_change_percent_24h: float = 0.0 # Изменение цены в % за 24ч
    
    # Дополнительная информация
    open_price: float = 0.0            # Цена открытия
    prev_close_price: float = 0.0      # Предыдущая цена закрытия
    weighted_avg_price: float = 0.0    # Средневзвешенная цена
    
    # Spread
    bid_size: float = 0.0              # Размер покупки
    ask_size: float = 0.0              # Размер продажи
    spread: float = 0.0                # Спред
    spread_percentage: float = 0.0     # Спред в процентах
    
    # Время
    timestamp: Optional[datetime] = None
    
    @property
    def mid_price(self) -> float:
        """Средняя цена между bid и ask"""
        return (self.bid_price + self.ask_price) / 2 if self.bid_price and self.ask_price else 0.0


@dataclass
class OrderBookEntry:
    """Запись в стакане ордеров"""
    price: float                       # Цена
    quantity: float                    # Количество
    
    @property
    def total_value(self) -> float:
        """Общая стоимость на уровне"""
        return self.price * self.quantity


@dataclass
class OrderBook:
    """Стакан ордеров"""
    symbol: str                        # Символ инструмента
    bids: List[OrderBookEntry]         # Заявки на покупку
    asks: List[OrderBookEntry]         # Заявки на продажу
    timestamp: Optional[datetime] = None
    
    @property
    def best_bid(self) -> Optional[OrderBookEntry]:
        """Лучшая цена покупки"""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookEntry]:
        """Лучшая цена продажи"""
        return self.asks[0] if self.asks else None
    
    @property
    def spread(self) -> float:
        """Спред между лучшими ценами"""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return 0.0
    
    @property
    def mid_price(self) -> float:
        """Средняя цена"""
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return 0.0


@dataclass
class Kline:
    """Свечные данные"""
    symbol: str                        # Символ инструмента
    interval: str                      # Интервал (1m, 5m, 1h, etc.)
    open_time: datetime                # Время открытия свечи
    close_time: datetime               # Время закрытия свечи
    
    # OHLCV данные
    open_price: float                  # Цена открытия
    high_price: float                  # Максимальная цена
    low_price: float                   # Минимальная цена
    close_price: float                 # Цена закрытия
    volume: float                      # Объем торгов
    
    # Дополнительные данные
    quote_volume: float = 0.0          # Объем в котируемой валюте
    trades_count: int = 0              # Количество сделок
    taker_buy_volume: float = 0.0      # Объем покупок тейкеров
    taker_buy_quote_volume: float = 0.0 # Объем покупок тейкеров в котируемой валюте
    
    # Технические индикаторы (могут быть добавлены)
    turnover: float = 0.0              # Оборот
    
    @property
    def is_bullish(self) -> bool:
        """Бычья ли свеча"""
        return self.close_price > self.open_price
    
    @property
    def is_bearish(self) -> bool:
        """Медвежья ли свеча"""
        return self.close_price < self.open_price
    
    @property
    def body_size(self) -> float:
        """Размер тела свечи"""
        return abs(self.close_price - self.open_price)
    
    @property
    def upper_shadow(self) -> float:
        """Верхняя тень свечи"""
        return self.high_price - max(self.open_price, self.close_price)
    
    @property
    def lower_shadow(self) -> float:
        """Нижняя тень свечи"""
        return min(self.open_price, self.close_price) - self.low_price


@dataclass
class AccountInfo:
    """Информация об аккаунте"""
    account_type: str                  # Тип аккаунта
    account_id: str                    # ID аккаунта
    margin_mode: str = "ISOLATED"      # Режим маржи
    
    # Балансы и маржа
    total_equity: float = 0.0          # Общий капитал
    total_wallet_balance: float = 0.0  # Общий баланс кошелька
    total_margin_balance: float = 0.0  # Общий маржинальный баланс
    available_balance: float = 0.0     # Доступный баланс
    
    # Маржинальные показатели
    total_initial_margin: float = 0.0  # Общая начальная маржа
    total_maintenance_margin: float = 0.0 # Общая поддерживающая маржа
    total_position_initial_margin: float = 0.0 # Начальная маржа позиций
    total_open_order_initial_margin: float = 0.0 # Начальная маржа ордеров
    
    # Уровень маржи
    margin_ratio: float = 0.0          # Коэффициент маржи
    max_withdraw_amount: float = 0.0   # Максимальная сумма для вывода
    
    # Статус аккаунта  
    can_trade: bool = True             # Может торговать
    can_withdraw: bool = True          # Может выводить
    can_deposit: bool = True           # Может вносить
    
    # Время обновления
    last_update: Optional[datetime] = None
    
    # Дополнительная информация
    borrow_enabled: bool = False       # Заимствование включено
    multi_assets_margin: bool = False  # Мультиактивная маржа
    trade_group_id: Optional[int] = None # ID торговой группы


@dataclass
class ExchangeInfo:
    """Информация о бирже"""
    exchange_name: str                 # Название биржи
    timezone: str                      # Часовой пояс
    server_time: datetime              # Время сервера
    
    # Лимиты API
    rate_limits: List[Dict[str, Any]] = field(default_factory=list)
    
    # Фильтры для символов
    exchange_filters: List[Dict[str, Any]] = field(default_factory=list)
    
    # Поддерживаемые возможности
    supported_order_types: List[str] = field(default_factory=list)
    supported_time_in_force: List[str] = field(default_factory=list)
    
    # Статус биржи
    status: str = "NORMAL"             # Статус работы биржи
    
    # Дополнительная информация
    permissions: List[str] = field(default_factory=list)
    symbols: List[Instrument] = field(default_factory=list)


# =================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===================

def create_empty_position(symbol: str) -> Position:
    """Создание пустой позиции"""
    return Position(
        symbol=symbol,
        side="None",
        size=0.0,
        entry_price=0.0,
        mark_price=0.0
    )


def create_order_from_dict(order_data: Dict[str, Any]) -> Order:
    """Создание ордера из словаря данных"""
    return Order(
        order_id=order_data.get("orderId", ""),
        client_order_id=order_data.get("clientOrderId"),
        symbol=order_data.get("symbol", ""),
        side=order_data.get("side", ""),
        order_type=order_data.get("orderType", ""),
        quantity=float(order_data.get("quantity", 0)),
        price=float(order_data.get("price", 0)),
        filled_quantity=float(order_data.get("filledQty", 0)),
        status=order_data.get("orderStatus", "New"),
        time_in_force=order_data.get("timeInForce", "GTC"),
        avg_price=float(order_data.get("avgPrice", 0)),
        commission=float(order_data.get("commission", 0)),
        commission_asset=order_data.get("commissionAsset", ""),
        reduce_only=order_data.get("reduceOnly", False),
        exchange_data=order_data
    )


def create_position_from_dict(position_data: Dict[str, Any]) -> Position:
    """Создание позиции из словаря данных"""
    return Position(
        symbol=position_data.get("symbol", ""),
        side=position_data.get("side", "None"),
        size=float(position_data.get("size", 0)),
        entry_price=float(position_data.get("entryPrice", 0)),
        mark_price=float(position_data.get("markPrice", 0)),
        unrealised_pnl=float(position_data.get("unrealisedPnl", 0)),
        leverage=float(position_data.get("leverage", 1)),
        margin=float(position_data.get("positionMargin", 0)),
        liq_price=float(position_data.get("liqPrice")) if position_data.get("liqPrice") else None,
        stop_loss=float(position_data.get("stopLoss")) if position_data.get("stopLoss") else None,
        take_profit=float(position_data.get("takeProfit")) if position_data.get("takeProfit") else None,
        position_mode=position_data.get("positionMode", "MergedSingle"),
        auto_add_margin=position_data.get("autoAddMargin", False)
    )


def calculate_position_pnl(position: Position, current_price: float) -> float:
    """Расчет PnL позиции по текущей цене"""
    if position.size == 0:
        return 0.0
    
    if position.is_long:
        return position.size * (current_price - position.entry_price)
    else:
        return position.size * (position.entry_price - current_price)


def format_currency(amount: float, precision: int = 8) -> str:
    """Форматирование валютной суммы"""
    return f"{amount:.{precision}f}".rstrip('0').rstrip('.')


def normalize_symbol_format(symbol: str, format_type: str = "standard") -> str:
    """
    Нормализация формата символа
    
    Args:
        symbol: Исходный символ
        format_type: Тип формата (standard, underscore, slash)
    """
    # Удаляем все разделители
    clean_symbol = symbol.replace("/", "").replace("_", "").replace("-", "").upper()
    
    if format_type == "underscore":
        # BTCUSDT -> BTC_USDT
        if len(clean_symbol) >= 6:
            return f"{clean_symbol[:-4]}_{clean_symbol[-4:]}"
    elif format_type == "slash":
        # BTCUSDT -> BTC/USDT
        if len(clean_symbol) >= 6:
            return f"{clean_symbol[:-4]}/{clean_symbol[-4:]}"
    
    return clean_symbol  # Возвращаем стандартный формат


# Константы для работы с моделями
POSITION_SIDES = ["Buy", "Sell", "None"]
ORDER_STATUSES = ["New", "PartiallyFilled", "Filled", "Cancelled", "Rejected"]
ORDER_TYPES = ["Market", "Limit", "StopMarket", "StopLimit", "TakeProfit", "TakeProfitLimit"]
TIME_IN_FORCE = ["GTC", "IOC", "FOK", "GTX"]