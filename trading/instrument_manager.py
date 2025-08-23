# -*- coding: utf-8 -*-

"""
Единый менеджер для работы с параметрами инструментов.

Этот модуль предоставляет централизованный интерфейс для получения
и управления параметрами торговых инструментов (tick_size, qty_step и т.д.).

Основные возможности:
- Динамическое получение параметров через API с кэшированием
- Автоматическое обновление кэша
- Fallback на предустановленные значения при недоступности API
- Единые методы округления для всего проекта
"""

import logging
import time
import math
from typing import Dict, Any, Optional, Union
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import threading

from .instrument_settings import INSTRUMENT_SETTINGS, DEFAULT_INSTRUMENT_SETTINGS, get_instrument_settings

logger = logging.getLogger('instrument_manager')

# Используем настройки из instrument_settings.py
# Преобразуем формат ключей для совместимости
FALLBACK_INSTRUMENT_SETTINGS = {}
for symbol, settings in INSTRUMENT_SETTINGS.items():
    FALLBACK_INSTRUMENT_SETTINGS[symbol] = {
        "tick_size": settings.get("tickSize", 0.001),
        "qty_step": settings.get("qtyStep", 0.01),
        "min_qty": settings.get("minOrderQty", 0.01),
        "min_notional": settings.get("minNotionalValue", 5.0),
        "max_qty": settings.get("maxOrderQty", 100000),
        "max_market_qty": settings.get("maxMktOrderQty", 50000)
    }

# Дефолтные параметры для неизвестных инструментов
DEFAULT_SETTINGS = {
    "tick_size": DEFAULT_INSTRUMENT_SETTINGS.get("tickSize", 0.001),
    "qty_step": DEFAULT_INSTRUMENT_SETTINGS.get("qtyStep", 0.01),
    "min_qty": DEFAULT_INSTRUMENT_SETTINGS.get("minOrderQty", 0.01),
    "min_notional": DEFAULT_INSTRUMENT_SETTINGS.get("minNotionalValue", 5.0),
    "max_qty": DEFAULT_INSTRUMENT_SETTINGS.get("maxOrderQty", 100000),
    "max_market_qty": DEFAULT_INSTRUMENT_SETTINGS.get("maxMktOrderQty", 50000)
}


class InstrumentManager:
    """
    Менеджер для работы с параметрами торговых инструментов.
    
    Обеспечивает:
    - Кэширование параметров инструментов
    - Автоматическое обновление кэша
    - Thread-safe доступ к данным
    - Единые методы округления
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern для обеспечения единого экземпляра."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, api_client=None, cache_ttl: int = 1800):
        """
        Инициализация менеджера инструментов.
        
        Args:
            api_client: Клиент API для получения данных (опционально)
            cache_ttl: Время жизни кэша в секундах (по умолчанию 30 минут)
        """
        if hasattr(self, '_initialized'):
            return
            
        self.api_client = api_client
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._last_update = {}
        self._cache_lock = threading.Lock()
        self._initialized = True
        
        logger.info(f"InstrumentManager initialized with cache TTL: {cache_ttl}s")
    
    def set_api_client(self, api_client):
        """Установка или обновление API клиента."""
        self.api_client = api_client
        logger.info("API client updated")
    
    def get_instrument_info(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Получает параметры инструмента с кэшированием.
        
        Args:
            symbol: Символ инструмента (например, "BTCUSDT" или "BTCUSDT.P")
            force_refresh: Принудительное обновление из API
            
        Returns:
            Словарь с параметрами инструмента
        """
        # Очищаем символ от возможного суффикса .P для работы с API
        clean_symbol = symbol.replace(".P", "")
        
        with self._cache_lock:
            # Проверяем кэш (используем clean_symbol для консистентности)
            if not force_refresh and clean_symbol in self._cache:
                if time.time() - self._last_update.get(clean_symbol, 0) < self.cache_ttl:
                    logger.debug(f"Using cached data for {clean_symbol} (original: {symbol})")
                    return self._cache[clean_symbol].copy()
            
            # Пытаемся получить из API
            if self.api_client:
                try:
                    logger.info(f"Fetching instrument info from API for {clean_symbol} (original: {symbol})")
                    api_data = self._fetch_from_api(clean_symbol)
                    if api_data:
                        self._cache[clean_symbol] = api_data
                        self._last_update[clean_symbol] = time.time()
                        return api_data.copy()
                except Exception as e:
                    logger.error(f"Failed to fetch instrument info from API: {e}")
            
            # Используем fallback данные
            logger.warning(f"Using fallback data for {clean_symbol} (original: {symbol})")
            fallback_data = FALLBACK_INSTRUMENT_SETTINGS.get(clean_symbol, DEFAULT_SETTINGS).copy()
            self._cache[clean_symbol] = fallback_data
            self._last_update[clean_symbol] = time.time()
            return fallback_data
    
    def _fetch_from_api(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Получает параметры инструмента из API.
        
        Args:
            symbol: Символ инструмента
            
        Returns:
            Словарь с параметрами или None при ошибке
        """
        if not self.api_client:
            return None
            
        try:
            # Получаем информацию о инструменте
            response = self.api_client.get_instrument_info(symbol)
            if not response or response.get("retCode") != 0:
                logger.warning(f"API вернул ошибку для {symbol}: {response}")
                return None
            
            # Извлекаем данные об инструменте из ответа
            result_data = response.get("result", {})
            instrument_list = result_data.get("list", [])
            
            if not instrument_list:
                logger.warning(f"Пустой список инструментов для {symbol}")
                return None
            
            # Берем первый инструмент из списка
            info = instrument_list[0]
            
            # Извлекаем параметры
            result = {}
            
            # Параметры цены
            price_filter = info.get("priceFilter", {})
            if price_filter:
                tick_size = price_filter.get("tickSize")
                if tick_size:
                    result["tick_size"] = float(tick_size)
                result["min_price"] = float(price_filter.get("minPrice", 0))
                result["max_price"] = float(price_filter.get("maxPrice", 999999))
            
            # Параметры количества
            lot_size_filter = info.get("lotSizeFilter", {})
            if lot_size_filter:
                qty_step = lot_size_filter.get("qtyStep")
                min_order_qty = lot_size_filter.get("minOrderQty")
                
                if qty_step:
                    result["qty_step"] = float(qty_step)
                if min_order_qty:
                    result["min_qty"] = float(min_order_qty)
                    
                result["max_qty"] = float(lot_size_filter.get("maxOrderQty", DEFAULT_SETTINGS["max_qty"]))
                result["max_market_qty"] = float(lot_size_filter.get("maxMktOrderQty", DEFAULT_SETTINGS["max_market_qty"]))
                
                # Минимальная стоимость также может быть в lotSizeFilter
                min_notional = lot_size_filter.get("minNotionalValue")
                if min_notional:
                    result["min_notional"] = float(min_notional)
            
            # Минимальная стоимость (альтернативный источник)
            notional_filter = info.get("notionalFilter", {})
            if notional_filter and "min_notional" not in result:
                result["min_notional"] = float(notional_filter.get("minNotional", DEFAULT_SETTINGS["min_notional"]))
            
            # Устанавливаем значения по умолчанию если не получили из API
            if "tick_size" not in result:
                result["tick_size"] = DEFAULT_SETTINGS["tick_size"]
            if "qty_step" not in result:
                result["qty_step"] = DEFAULT_SETTINGS["qty_step"]
            if "min_qty" not in result:
                result["min_qty"] = DEFAULT_SETTINGS["min_qty"]
            if "min_notional" not in result:
                result["min_notional"] = DEFAULT_SETTINGS["min_notional"]
            
            logger.info(f"Получены параметры для {symbol}: {result}")
            
            # Валидация полученных данных
            if self._validate_instrument_data(symbol, result):
                return result
            else:
                logger.warning(f"Invalid data from API for {symbol}, using fallback")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching instrument info for {symbol}: {e}")
            return None
    
    def _validate_instrument_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        Валидирует полученные данные инструмента.
        
        Args:
            symbol: Символ инструмента
            data: Данные для валидации
            
        Returns:
            True если данные валидны, False иначе
        """
        required_fields = ["tick_size", "qty_step", "min_qty"]
        
        # Проверяем наличие обязательных полей
        for field in required_fields:
            if field not in data or data[field] <= 0:
                logger.warning(f"Invalid {field} for {symbol}: {data.get(field)}")
                return False
        
        # Специальные проверки для известных инструментов
        if symbol == "ETHUSDT":
            if data["qty_step"] < 0.01 or data["min_qty"] < 0.01:
                logger.warning(f"Suspicious values for ETHUSDT: qty_step={data['qty_step']}, min_qty={data['min_qty']}")
                return False
        
        return True
    
    def get_tick_size(self, symbol: str) -> float:
        """Получает размер тика (минимальное изменение цены)."""
        info = self.get_instrument_info(symbol)
        return info.get("tick_size", DEFAULT_SETTINGS["tick_size"])
    
    def get_qty_step(self, symbol: str) -> float:
        """Получает шаг изменения количества."""
        info = self.get_instrument_info(symbol)
        return info.get("qty_step", DEFAULT_SETTINGS["qty_step"])
    
    def get_min_qty(self, symbol: str) -> float:
        """Получает минимальное количество для ордера."""
        info = self.get_instrument_info(symbol)
        return info.get("min_qty", DEFAULT_SETTINGS["min_qty"])
    
    def get_min_notional(self, symbol: str) -> float:
        """Получает минимальную стоимость ордера."""
        info = self.get_instrument_info(symbol)
        return info.get("min_notional", DEFAULT_SETTINGS["min_notional"])
    
    def round_price(self, symbol: str, price: float, round_up: bool = False) -> float:
        """
        Округляет цену до правильного тика.
        
        Args:
            symbol: Символ инструмента
            price: Цена для округления
            round_up: Округлять вверх (по умолчанию вниз)
            
        Returns:
            Округленная цена
        """
        tick_size = self.get_tick_size(symbol)
        return self._round_to_step(price, tick_size, round_up)
    
    def format_qty(self, symbol: str, qty: float) -> str:
        """
        Форматирует количество в строку с правильным числом знаков после запятой
        
        Args:
            symbol: Символ инструмента
            qty: Количество для форматирования
            
        Returns:
            Отформатированная строка количества
        """
        qty_step = self.get_qty_step(symbol)
        
        # Определяем количество знаков после запятой
        if qty_step >= 1:
            decimal_places = 0
        else:
            # Считаем количество знаков после запятой в qty_step
            step_str = f"{qty_step:.10f}".rstrip('0')
            if "." in step_str:
                decimal_places = len(step_str.split(".")[1])
            else:
                decimal_places = 0
        
        # Форматируем с нужным количеством знаков
        if decimal_places == 0:
            return str(int(qty))
        else:
            return format(qty, f'.{decimal_places}f')
    
    def round_qty(self, symbol: str, qty: float, round_up: bool = False, enforce_min: bool = True) -> float:
        """
        Округляет количество до правильного шага.
        
        Args:
            symbol: Символ инструмента
            qty: Количество для округления
            round_up: Округлять вверх (по умолчанию вниз)
            enforce_min: Принудительно увеличивать до минимального количества (по умолчанию True для обратной совместимости)
            
        Returns:
            Округленное количество
        """
        qty_step = self.get_qty_step(symbol)
        rounded_qty = self._round_to_step(qty, qty_step, round_up)
        
        logger.info(f"round_qty для {symbol}: {qty} -> {rounded_qty} (шаг: {qty_step}, round_up: {round_up})")
        
        # Проверяем минимальное количество только если enforce_min=True
        if enforce_min:
            min_qty = self.get_min_qty(symbol)
            if rounded_qty < min_qty:
                logger.warning(f"Rounded quantity {rounded_qty} is below minimum {min_qty} for {symbol}")
                # Если округленное количество меньше минимального, возвращаем минимальное
                return min_qty
        
        return rounded_qty
    
    def _round_to_step(self, value: float, step: float, round_up: bool = False) -> float:
        """
        Универсальный метод округления до шага.
        
        Args:
            value: Значение для округления
            step: Шаг округления
            round_up: Округлять вверх (по умолчанию вниз)
            
        Returns:
            Округленное значение
        """
        if step <= 0:
            return value
        
        # Используем Decimal для точности
        decimal_value = Decimal(str(value))
        decimal_step = Decimal(str(step))
        
        if round_up:
            steps = decimal_value / decimal_step
            steps = steps.quantize(Decimal('1'), rounding=ROUND_UP)
        else:
            steps = decimal_value / decimal_step
            steps = steps.quantize(Decimal('1'), rounding=ROUND_DOWN)
        
        result = steps * decimal_step
        
        # Определяем количество десятичных знаков для корректного округления
        decimal_step_str = str(decimal_step)
        if '.' in decimal_step_str and 'E' not in decimal_step_str.upper():
            # Обычная десятичная запись
            decimal_places = len(decimal_step_str.split('.')[1])
        else:
            # Научная нотация или целое число
            # Конвертируем в обычный формат для подсчета знаков
            formatted_step = f"{step:.10f}".rstrip('0')
            if '.' in formatted_step:
                decimal_places = len(formatted_step.split('.')[1])
            else:
                decimal_places = 0
        
        # Округляем с учетом количества знаков после запятой
        return float(result.quantize(Decimal(f"0.{'0' * decimal_places}")))
    
    def validate_order_params(self, symbol: str, qty: float, price: float) -> Dict[str, Any]:
        """
        Валидирует и корректирует параметры ордера.
        
        Args:
            symbol: Символ инструмента
            qty: Количество
            price: Цена
            
        Returns:
            Словарь с результатами валидации и скорректированными значениями
        """
        info = self.get_instrument_info(symbol)
        
        # Округляем значения
        corrected_qty = self.round_qty(symbol, qty)
        corrected_price = self.round_price(symbol, price)
        
        # Проверяем минимальное количество
        min_qty = info.get("min_qty", DEFAULT_SETTINGS["min_qty"])
        if corrected_qty < min_qty:
            corrected_qty = min_qty
        
        # Проверяем минимальную стоимость
        notional_value = corrected_qty * corrected_price
        min_notional = info.get("min_notional", DEFAULT_SETTINGS["min_notional"])
        
        result = {
            "valid": True,
            "original_qty": qty,
            "original_price": price,
            "corrected_qty": corrected_qty,
            "corrected_price": corrected_price,
            "notional_value": notional_value,
            "errors": []
        }
        
        # Проверка минимальной стоимости
        if notional_value < min_notional:
            result["valid"] = False
            result["errors"].append(f"Notional value {notional_value:.2f} < min {min_notional}")
        
        # Проверка максимального количества
        max_qty = info.get("max_qty", float('inf'))
        if corrected_qty > max_qty:
            result["valid"] = False
            result["errors"].append(f"Quantity {corrected_qty} > max {max_qty}")
        
        return result
    
    def clear_cache(self, symbol: Optional[str] = None):
        """
        Очищает кэш.
        
        Args:
            symbol: Если указан, очищает только для конкретного символа
        """
        with self._cache_lock:
            if symbol:
                self._cache.pop(symbol, None)
                self._last_update.pop(symbol, None)
                logger.info(f"Cache cleared for {symbol}")
            else:
                self._cache.clear()
                self._last_update.clear()
                logger.info("All cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша."""
        with self._cache_lock:
            current_time = time.time()
            stats = {
                "total_symbols": len(self._cache),
                "cache_ttl": self.cache_ttl,
                "symbols": {}
            }
            
            for symbol, last_update in self._last_update.items():
                age = current_time - last_update
                stats["symbols"][symbol] = {
                    "age_seconds": round(age, 2),
                    "expired": age > self.cache_ttl
                }
            
            return stats


# Глобальный экземпляр менеджера
_instrument_manager = InstrumentManager()


# Удобные функции для прямого использования
def get_instrument_info(symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Получает информацию об инструменте."""
    return _instrument_manager.get_instrument_info(symbol, force_refresh)


def round_price(symbol: str, price: float, round_up: bool = False) -> float:
    """Округляет цену до правильного тика."""
    return _instrument_manager.round_price(symbol, price, round_up)


def round_qty(symbol: str, qty: float, round_up: bool = False, enforce_min: bool = True) -> float:
    """Округляет количество до правильного шага."""
    return _instrument_manager.round_qty(symbol, qty, round_up, enforce_min)


def validate_order_params(symbol: str, qty: float, price: float) -> Dict[str, Any]:
    """Валидирует параметры ордера."""
    return _instrument_manager.validate_order_params(symbol, qty, price)


def set_api_client(api_client):
    """Устанавливает API клиент для менеджера."""
    _instrument_manager.set_api_client(api_client)


def get_manager() -> InstrumentManager:
    """Возвращает экземпляр менеджера инструментов."""
    return _instrument_manager