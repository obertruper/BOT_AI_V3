#!/usr/bin/env python3
"""
Вспомогательные функции для работы с SL/TP
"""

import logging
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def round_price_to_tick(price: float, tick_size: float) -> float:
    """
    Округляет цену до ближайшего tick size
    
    Args:
        price: Цена для округления
        tick_size: Минимальный шаг цены
        
    Returns:
        Округленная цена
    """
    if tick_size == 0:
        return price
    
    return round(price / tick_size) * tick_size


def get_tick_size_for_symbol(symbol: str) -> float:
    """
    Возвращает tick size для символа
    
    Args:
        symbol: Торговый символ
        
    Returns:
        Tick size
    """
    # Для основных криптовалют
    if "BTC" in symbol:
        return 0.1
    elif "ETH" in symbol:
        return 0.01
    else:
        # Для остальных используем более мелкий шаг
        return 0.001


def validate_price_levels(symbol: str, stop_loss: float, take_profit: float, 
                         side: str, current_price: float) -> bool:
    """
    Валидирует уровни SL и TP
    
    Args:
        symbol: Торговый символ
        stop_loss: Цена стоп-лосса
        take_profit: Цена тейк-профита
        side: Направление сделки (BUY/SELL)
        current_price: Текущая цена
        
    Returns:
        True если уровни валидны
    """
    try:
        if side.upper() in ["BUY", "LONG"]:
            # Для длинной позиции: SL < текущая цена < TP
            if stop_loss >= current_price:
                logger.error(f"Invalid SL for LONG: SL={stop_loss} >= price={current_price}")
                return False
            if take_profit <= current_price:
                logger.error(f"Invalid TP for LONG: TP={take_profit} <= price={current_price}")
                return False
        else:
            # Для короткой позиции: TP < текущая цена < SL
            if stop_loss <= current_price:
                logger.error(f"Invalid SL for SHORT: SL={stop_loss} <= price={current_price}")
                return False
            if take_profit >= current_price:
                logger.error(f"Invalid TP for SHORT: TP={take_profit} >= price={current_price}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating price levels: {e}")
        return False


def calculate_quantity_with_precision(quantity: float, symbol: str) -> float:
    """
    Рассчитывает количество с правильной точностью для биржи
    
    Args:
        quantity: Количество
        symbol: Торговый символ
        
    Returns:
        Количество с правильной точностью
    """
    # Определяем точность для разных типов активов
    if "BTC" in symbol:
        precision = 3  # 0.001 BTC
    elif "ETH" in symbol:
        precision = 4  # 0.0001 ETH
    else:
        precision = 2  # Для остальных
    
    # Округляем вниз для безопасности
    multiplier = 10 ** precision
    return int(quantity * multiplier) / multiplier


def calculate_risk_reward_ratio(entry_price: float, stop_loss: float, 
                               take_profit: float, side: str) -> float:
    """
    Рассчитывает соотношение риск/прибыль
    
    Args:
        entry_price: Цена входа
        stop_loss: Цена стоп-лосса
        take_profit: Цена тейк-профита
        side: Направление сделки
        
    Returns:
        Соотношение риск/прибыль
    """
    try:
        if side.upper() in ["BUY", "LONG"]:
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            return 0
        
        return reward / risk
        
    except Exception as e:
        logger.error(f"Error calculating risk/reward: {e}")
        return 0


# Алиасы для обратной совместимости
round_to_tick = round_price_to_tick
get_tick_size = get_tick_size_for_symbol
validate_sltp_prices = validate_price_levels


def get_last_price(symbol: str) -> float:
    """
    Заглушка для получения последней цены
    В реальной реализации должна обращаться к exchange_manager
    """
    return 0


def set_trading_stop(symbol: str, sl: float, tp: float) -> bool:
    """
    Заглушка для установки SL/TP на бирже
    В реальной реализации должна обращаться к exchange API
    """
    logger.info(f"Would set SL={sl}, TP={tp} for {symbol}")
    return True