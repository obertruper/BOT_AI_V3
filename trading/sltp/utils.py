#!/usr/bin/env python3
"""
Утилиты для SL/TP системы
"""

# Конфигурация точности для различных символов
SYMBOL_PRECISION = {
    # Основные пары
    "BTCUSDT": {"price": 2, "qty": 6},
    "ETHUSDT": {"price": 2, "qty": 5},
    "BNBUSDT": {"price": 2, "qty": 4},
    "SOLUSDT": {"price": 3, "qty": 3},
    "XRPUSDT": {"price": 4, "qty": 1},
    "DOGEUSDT": {"price": 5, "qty": 0},
    "ADAUSDT": {"price": 4, "qty": 1},
    "AVAXUSDT": {"price": 3, "qty": 3},
    "DOTUSDT": {"price": 3, "qty": 3},
    "MATICUSDT": {"price": 4, "qty": 1},
    # Дефолт для неизвестных пар
    "DEFAULT": {"price": 8, "qty": 8},
}


def get_symbol_precision(symbol: str) -> dict[str, int]:
    """Получить точность для символа"""
    symbol = symbol.upper()
    return SYMBOL_PRECISION.get(symbol, SYMBOL_PRECISION["DEFAULT"])


def round_price(symbol: str, price: float) -> float:
    """
    Округление цены до правильной точности для символа

    Args:
        symbol: Торговый символ
        price: Цена для округления

    Returns:
        Округленная цена
    """
    precision = get_symbol_precision(symbol)["price"]
    return round(price, precision)


def round_qty(symbol: str, qty: float) -> float:
    """
    Округление количества до правильной точности для символа

    Args:
        symbol: Торговый символ
        qty: Количество для округления

    Returns:
        Округленное количество
    """
    precision = get_symbol_precision(symbol)["qty"]
    if precision == 0:
        return float(int(qty))
    return round(qty, precision)


def calculate_qty_from_usdt(symbol: str, usdt_amount: float, price: float) -> float:
    """
    Рассчитать количество токенов из суммы в USDT

    Args:
        symbol: Торговый символ
        usdt_amount: Сумма в USDT
        price: Текущая цена

    Returns:
        Количество токенов
    """
    if price <= 0:
        return 0.0

    qty = usdt_amount / price
    return round_qty(symbol, qty)


def calculate_position_value(qty: float, price: float) -> float:
    """
    Рассчитать стоимость позиции в USDT

    Args:
        qty: Количество токенов
        price: Цена за токен

    Returns:
        Стоимость в USDT
    """
    return round(qty * price, 2)


def calculate_pnl_percentage(entry_price: float, current_price: float, side: str) -> float:
    """
    Рассчитать процент прибыли/убытка

    Args:
        entry_price: Цена входа
        current_price: Текущая цена
        side: Направление позиции (Buy/Sell)

    Returns:
        Процент PnL
    """
    if entry_price <= 0:
        return 0.0

    if side.upper() in ["BUY", "LONG"]:
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
    else:  # SELL/SHORT
        pnl_pct = ((entry_price - current_price) / entry_price) * 100

    return round(pnl_pct, 2)


def normalize_percentage(value: float) -> float:
    """
    Нормализация процентов - конвертация 0.01 в 1.0 если нужно

    Args:
        value: Значение процента

    Returns:
        Нормализованный процент
    """
    # Если значение меньше 0.1, вероятно это доля (0.01 = 1%)
    # Конвертируем в проценты
    if value < 0.1:
        return value * 100
    return value
