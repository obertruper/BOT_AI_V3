#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль с настройками инструментов для торговой системы.

Содержит предустановленные параметры для известных инструментов,
такие как размер тика, шаг количества, минимальный объем и т.д.
Эти настройки используются для корректного округления цен и объемов
при создании ордеров и расчете уровней.
"""

import logging

logger = logging.getLogger('instrument_settings')

# Таблица с известными значениями для инструментов Bybit
# Содержит актуальные параметры для корректного округления
INSTRUMENT_SETTINGS = {
    # Символ: {tickSize, qtyStep, minOrderQty, requiresWholeNumber, maxOrderQty, maxMktOrderQty}
    
    # Основные криптовалюты - настройки подтверждены по API
    "BTCUSDT":    {"tickSize": 0.1,    "qtyStep": 0.001, "minOrderQty": 0.001, "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 1190.000, "maxMktOrderQty": 500.000},
    "ETHUSDT":    {"tickSize": 0.01,   "qtyStep": 0.01,  "minOrderQty": 0.01,  "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 7240.00, "maxMktOrderQty": 724.00},
    "BNBUSDT":    {"tickSize": 0.10,   "qtyStep": 0.01,  "minOrderQty": 0.01,  "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 5120.00, "maxMktOrderQty": 1000.00},
    "XRPUSDT":    {"tickSize": 0.0001, "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 1000000, "maxMktOrderQty": 500000},
    
    # Популярные альткоины - настройки сверены с логами COPE сервера и API
    "SOLUSDT":    {"tickSize": 0.010,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 79770.0, "maxMktOrderQty": 39880.0},
    "ADAUSDT":    {"tickSize": 0.0001, "qtyStep": 1.0,   "minOrderQty": 1.0,   "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 1000000, "maxMktOrderQty": 500000},
    "DOGEUSDT":   {"tickSize": 0.00001,"qtyStep": 1.0,   "minOrderQty": 1.0,   "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 5000000, "maxMktOrderQty": 2500000},
    "DOTUSDT":    {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 500000, "maxMktOrderQty": 250000},
    "LTCUSDT":    {"tickSize": 0.01,   "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 28740.0, "maxMktOrderQty": 6160.0},
    "TONUSDT":    {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 500000, "maxMktOrderQty": 250000},
    "AVAXUSDT":   {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 75000, "maxMktOrderQty": 35000},
    "ATOMUSDT":   {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 100000, "maxMktOrderQty": 50000},
    "MATICUSDT":  {"tickSize": 0.0001, "qtyStep": 1.0,   "minOrderQty": 1.0,   "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 1500000, "maxMktOrderQty": 750000},
    "TRXUSDT":    {"tickSize": 0.00001,"qtyStep": 1.0,   "minOrderQty": 1.0,   "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 5000000, "maxMktOrderQty": 2500000},
    "LINKUSDT":   {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 250000, "maxMktOrderQty": 125000},
    
    # DeFi токены - подтверждены данными из логов
    "ALGOUSDT":   {"tickSize": 0.0001, "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 3190810.0, "maxMktOrderQty": 1595400.0},
    "DYDXUSDT":   {"tickSize": 0.0001, "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 662810.0, "maxMktOrderQty": 331400.0},
    "UNIUSDT":    {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 175380.0, "maxMktOrderQty": 87690.0},
    "CAKEUSDT":   {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 146350.0, "maxMktOrderQty": 73170.0},
    "TRBUSDT":    {"tickSize": 0.010,  "qtyStep": 0.01,  "minOrderQty": 0.01,  "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 8580.00, "maxMktOrderQty": 4290.00},
    "AAVEUSDT":   {"tickSize": 0.01,   "qtyStep": 0.01,  "minOrderQty": 0.01,  "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 9000.00, "maxMktOrderQty": 4500.00},
    
    # Новые и популярные монеты - добавлены параметры maxMktOrderQty
    "TWTUSDT":    {"tickSize": 0.0001, "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 171640.0, "maxMktOrderQty": 85820.0},
    "TIAUSDT":    {"tickSize": 0.0010, "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 136720.0, "maxMktOrderQty": 68360.0},
    "MELANIAUSDT":{"tickSize": 0.0001, "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 100000.0, "maxMktOrderQty": 20000.0},
    "GALAUSDT":   {"tickSize": 0.0001, "qtyStep": 1.0,   "minOrderQty": 1.0,   "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 10000000, "maxMktOrderQty": 5000000},
    "WIFUSDT":    {"tickSize": 0.001,  "qtyStep": 1.0,   "minOrderQty": 1.0,   "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 1000000, "maxMktOrderQty": 500000},
    "ENAUSDT":    {"tickSize": 0.0001, "qtyStep": 1.0,   "minOrderQty": 1.0,   "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 5000000, "maxMktOrderQty": 2500000},
    "GRIFFAINUSDT": {"tickSize": 0.00001, "qtyStep": 1.0, "minOrderQty": 1.0, "minNotionalValue": 5.0, "requiresWholeNumber": True, "maxOrderQty": 5000000, "maxMktOrderQty": 1000000},
    "APTUSDT":    {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 65000, "maxMktOrderQty": 32500},
    "ARBITRUM":   {"tickSize": 0.0001, "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 500000, "maxMktOrderQty": 250000},
    "NEARUSDT":   {"tickSize": 0.001,  "qtyStep": 0.1,   "minOrderQty": 0.1,   "minNotionalValue": 5.0, "requiresWholeNumber": False, "maxOrderQty": 140000, "maxMktOrderQty": 70000},
}

# Настройки по умолчанию для инструментов, которых нет в таблице
DEFAULT_INSTRUMENT_SETTINGS = {
    "tickSize": 0.001,
    "qtyStep": 0.01,
    "minOrderQty": 0.01,
    "minNotionalValue": 5.0,
    "requiresWholeNumber": False,
    "maxOrderQty": 100000,
    "maxMktOrderQty": 50000
}

def get_instrument_settings(symbol: str, api_client=None):
    """
    Получает настройки инструмента для правильного округления цен и количеств.
    
    Сначала пытается получить информацию через API, если это не удается или значения
    некорректны, используем предустановленные значения из таблицы INSTRUMENT_SETTINGS.
    
    Args:
        symbol: Символ инструмента
        api_client: Клиент API (опционально)
        
    Returns:
        Dict[str, Any]: Настройки инструмента
    """
    # Начальные настройки по умолчанию
    settings = DEFAULT_INSTRUMENT_SETTINGS.copy()
    
    # Получаем предустановленные настройки из таблицы
    # Если символ с суффиксом .P, пробуем сначала с ним, потом без него
    table_settings = INSTRUMENT_SETTINGS.get(symbol, {})
    if not table_settings and symbol.endswith('.P'):
        clean_symbol = symbol.replace('.P', '')
        table_settings = INSTRUMENT_SETTINGS.get(clean_symbol, {})
    
    # Если передан клиент API, пытаемся получить актуальные настройки
    api_settings = {}
    if api_client:
        try:
            logger.info(f"[get_instrument_settings] => Запрос настроек через API для {symbol}")
            instrument_info = api_client.get_instrument_info(symbol)
            
            if instrument_info:
                # Обрабатываем параметры цены
                price_filter = instrument_info.get("priceFilter", {})
                if price_filter:
                    try:
                        if "tickSize" in price_filter:
                            api_settings["tickSize"] = float(price_filter["tickSize"])
                        if "minPrice" in price_filter:
                            api_settings["minPrice"] = float(price_filter["minPrice"])
                    except (ValueError, TypeError) as e:
                        logger.error(f"[get_instrument_settings] => Ошибка при обработке priceFilter: {e}")
                
                # Обрабатываем параметры количества
                lot_size_filter = instrument_info.get("lotSizeFilter", {})
                if lot_size_filter:
                    try:
                        if "qtyStep" in lot_size_filter:
                            api_settings["qtyStep"] = float(lot_size_filter["qtyStep"])
                        if "minOrderQty" in lot_size_filter:
                            api_settings["minOrderQty"] = float(lot_size_filter["minOrderQty"])
                        if "maxOrderQty" in lot_size_filter:
                            api_settings["maxOrderQty"] = float(lot_size_filter["maxOrderQty"])
                        if "maxMktOrderQty" in lot_size_filter:
                            api_settings["maxMktOrderQty"] = float(lot_size_filter["maxMktOrderQty"])
                    except (ValueError, TypeError) as e:
                        logger.error(f"[get_instrument_settings] => Ошибка при обработке lotSizeFilter: {e}")
                
                # Обрабатываем параметры минимальной стоимости ордера
                notional_filter = instrument_info.get("notionalFilter", {}) or {}
                if notional_filter:
                    try:
                        if "minNotional" in notional_filter:
                            api_settings["minNotionalValue"] = float(notional_filter["minNotional"])
                    except (ValueError, TypeError) as e:
                        logger.error(f"[get_instrument_settings] => Ошибка при обработке notionalFilter: {e}")
                
                # Определяем, требуются ли целые числа
                api_settings["requiresWholeNumber"] = (api_settings.get("qtyStep", 0.001) >= 1.0)
        except Exception as e:
            logger.error(f"[get_instrument_settings] => Ошибка при запросе API: {e}")
    
    # Сначала применяем настройки по умолчанию
    # Затем обновляем их таблицей (если есть настройки в таблице для данного символа)
    # И только потом данными API (если они получены)
    if table_settings:
        settings.update(table_settings)
    
    # Проверяем и корректируем данные API при необходимости
    if api_settings:
        # Специальная проверка для проблемных инструментов 
        if symbol == "ETHUSDT":
            # Если API вернул minOrderQty меньше 0.01, корректируем его
            if api_settings.get("minOrderQty", 0.001) < 0.01:
                logger.warning(f"[get_instrument_settings] => Для ETHUSDT API вернул minOrderQty={api_settings.get('minOrderQty')}, корректируем до 0.01")
                api_settings["minOrderQty"] = 0.01
            
            # Аналогично для qtyStep
            if api_settings.get("qtyStep", 0.001) < 0.01:
                logger.warning(f"[get_instrument_settings] => Для ETHUSDT API вернул qtyStep={api_settings.get('qtyStep')}, корректируем до 0.01")
                api_settings["qtyStep"] = 0.01
        
        # Проверка для ALGO
        if "ALGO" in symbol and api_settings.get("qtyStep", 0.001) < 0.1:
            logger.warning(f"[get_instrument_settings] => Для {symbol} API вернул qtyStep={api_settings.get('qtyStep')}, корректируем до 0.1")
            api_settings["qtyStep"] = 0.1
        
        # Применяем настройки из API, но с проверками
        for key in ["minOrderQty", "qtyStep"]:
            # Если есть в API и в таблице, сравниваем значения
            if key in api_settings and key in table_settings:
                api_value = api_settings[key]
                table_value = table_settings[key]
                
                # Если значение из API значительно меньше, чем из таблицы, используем значение из таблицы
                if api_value < table_value / 2:
                    logger.warning(f"[get_instrument_settings] => Настройка {key} из API ({api_value}) для {symbol} подозрительно мала, используем значение из таблицы ({table_value})")
                    api_settings[key] = table_value
        
        # Обновляем финальные настройки данными из API (прошедшими проверку)
        settings.update(api_settings)
    
    logger.info(f"[get_instrument_settings] => Финальные настройки для {symbol}: {settings}")
    return settings

def round_to_step(value, step):
    """
    Округляет значение до ближайшего кратного шагу. 
    Использует округление вниз (floor) для избежания превышения лимитов.
    
    Args:
        value: Значение для округления
        step: Шаг, до которого округлять
        
    Returns:
        float: Округленное значение
    """
    import math
    
    if step <= 0:
        return value
    
    # Округляем вниз до ближайшего шага
    steps = math.floor(value / step)
    result = steps * step
    
    # Определяем количество десятичных знаков для устранения проблем с плавающей запятой
    decimal_places = -int(math.log10(step)) if step < 1 else 0
    result = round(result, decimal_places)
    
    return result