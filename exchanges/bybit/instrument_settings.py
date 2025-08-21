#!/usr/bin/env python3
"""
Модуль с настройками инструментов для торговой системы Bybit.

Содержит предустановленные параметры для известных инструментов,
такие как размер тика, шаг количества, минимальный объем и т.д.
Эти настройки используются для корректного округления цен и объемов
при создании ордеров и расчете уровней.

Перенесено из V2_bot для исправления ошибок "Qty invalid"
"""

import logging

logger = logging.getLogger(__name__)

# Таблица с известными значениями для инструментов Bybit
# Содержит актуальные параметры для корректного округления
INSTRUMENT_SETTINGS = {
    # Символ: {tickSize, qtyStep, minOrderQty, requiresWholeNumber, maxOrderQty, maxMktOrderQty}
    # Основные криптовалюты - настройки подтверждены по API
    "BTCUSDT": {
        "tickSize": 0.1,
        "qtyStep": 0.001,
        "minOrderQty": 0.001,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 1190.000,
        "maxMktOrderQty": 500.000,
    },
    "ETHUSDT": {
        "tickSize": 0.01,
        "qtyStep": 0.01,
        "minOrderQty": 0.01,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 7240.00,
        "maxMktOrderQty": 724.00,
    },
    "BNBUSDT": {
        "tickSize": 0.10,
        "qtyStep": 0.01,
        "minOrderQty": 0.01,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 5120.00,
        "maxMktOrderQty": 1000.00,
    },
    "XRPUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,  # Changed from True to match API requirements
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    # Популярные альткоины - настройки сверены с логами и API
    "SOLUSDT": {
        "tickSize": 0.010,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 79770.0,
        "maxMktOrderQty": 39880.0,
    },
    "ADAUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "DOGEUSDT": {
        "tickSize": 0.00001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 5000000,
        "maxMktOrderQty": 2500000,
    },
    "DOTUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "LTCUSDT": {
        "tickSize": 0.01,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 28740.0,
        "maxMktOrderQty": 6160.0,
    },
    "AVAXUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "MATICUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "LINKUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "ATOMUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "UNIUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "ETCUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "XLMUSDT": {
        "tickSize": 0.00001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "FILUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "AAVEUSDT": {
        "tickSize": 0.01,
        "qtyStep": 0.01,
        "minOrderQty": 0.01,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 10000,
        "maxMktOrderQty": 5000,
    },
    "AXSUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "SANDUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "MANAUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "GALAUSDT": {
        "tickSize": 0.00001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "ICPUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 100000,
        "maxMktOrderQty": 50000,
    },
    "APTUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "INJUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "NEARUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "FTMUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "RNDRUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "OPUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "ARBUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "LDOUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "STXUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "SUIUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "TIAUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "WLDUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "SEIUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    "CYBERUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    "ARKMUSDT": {
        "tickSize": 0.001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 500000,
        "maxMktOrderQty": 250000,
    },
    # Мемкоины
    "SHIBUSDT": {
        "tickSize": 0.0000001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 10000000000,
        "maxMktOrderQty": 5000000000,
    },
    "PEPEUSDT": {
        "tickSize": 0.0000000001,
        "qtyStep": 100.0,
        "minOrderQty": 100.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 10000000000,
        "maxMktOrderQty": 5000000000,
    },
    "FLOKIUSDT": {
        "tickSize": 0.00000001,
        "qtyStep": 1.0,
        "minOrderQty": 1.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 10000000000,
        "maxMktOrderQty": 5000000000,
    },
    "BONKUSDT": {
        "tickSize": 0.0000000001,
        "qtyStep": 100.0,
        "minOrderQty": 100.0,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": True,
        "maxOrderQty": 10000000000,
        "maxMktOrderQty": 5000000000,
    },
    # Стейблкоины и другие
    "USDCUSDT": {
        "tickSize": 0.0001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
    # Default settings for unknown instruments
    "_DEFAULT": {
        "tickSize": 0.0001,
        "qtyStep": 0.1,
        "minOrderQty": 0.1,
        "minNotionalValue": 5.0,
        "requiresWholeNumber": False,
        "maxOrderQty": 1000000,
        "maxMktOrderQty": 500000,
    },
}


def get_instrument_settings(symbol: str) -> dict:
    """
    Получить настройки инструмента по символу.
    
    Args:
        symbol: Символ инструмента (например, 'BTCUSDT')
        
    Returns:
        Словарь с настройками инструмента
    """
    settings = INSTRUMENT_SETTINGS.get(symbol.upper())
    if not settings:
        logger.warning(f"Instrument settings not found for {symbol}, using defaults")
        settings = INSTRUMENT_SETTINGS["_DEFAULT"]
    return settings.copy()