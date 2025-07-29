"""
Базовый класс для всех технических индикаторов
Определяет интерфейс и общую функциональность
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class IndicatorConfig:
    """Конфигурация индикатора"""
    name: str
    enabled: bool = True
    params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class IndicatorResult:
    """Результат расчета индикатора"""
    name: str
    signal: int  # -1 (продавать), 0 (нейтрально), 1 (покупать)
    strength: float  # 0-100 сила сигнала
    value: Union[float, Dict[str, float]]  # Значение индикатора
    
    # Дополнительные данные
    timestamp: Optional[pd.Timestamp] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # Валидация сигнала
        if self.signal not in [-1, 0, 1]:
            raise ValueError(f"Signal must be -1, 0, or 1, got {self.signal}")
            
        # Валидация силы
        if not 0 <= self.strength <= 100:
            raise ValueError(f"Strength must be between 0 and 100, got {self.strength}")
            
        if self.metadata is None:
            self.metadata = {}
            
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        result = {
            'signal': self.signal,
            'strength': self.strength,
            'value': self.value
        }
        
        if self.timestamp:
            result['timestamp'] = self.timestamp.isoformat()
            
        if self.metadata:
            result.update(self.metadata)
            
        return result


class IndicatorBase(ABC):
    """Абстрактный базовый класс для всех индикаторов"""
    
    def __init__(self, config: IndicatorConfig):
        """
        Инициализация индикатора
        
        Args:
            config: Конфигурация индикатора
        """
        self.config = config
        self.name = config.name
        self.enabled = config.enabled
        self.params = config.params
        
        # Валидация параметров
        self._validate_params()
        
        # История расчетов для оптимизации
        self._cache = {}
        self._last_calculation_index = None
        
        logger.debug(f"Initialized {self.name} indicator with params: {self.params}")
        
    @abstractmethod
    def _validate_params(self) -> None:
        """Валидация параметров индикатора"""
        pass
        
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """
        Расчет индикатора
        
        Args:
            data: DataFrame с колонками 'open', 'high', 'low', 'close', 'volume'
            
        Returns:
            Результат расчета индикатора
        """
        pass
        
    @abstractmethod
    def get_required_columns(self) -> List[str]:
        """Получение списка необходимых колонок данных"""
        pass
        
    @abstractmethod
    def get_min_periods(self) -> int:
        """Минимальное количество периодов для расчета"""
        pass
        
    def is_data_valid(self, data: pd.DataFrame) -> bool:
        """
        Проверка валидности данных
        
        Args:
            data: DataFrame для проверки
            
        Returns:
            True если данные валидны
        """
        if data is None or data.empty:
            return False
            
        # Проверка наличия необходимых колонок
        required_columns = self.get_required_columns()
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"Missing required column '{col}' for {self.name}")
                return False
                
        # Проверка минимального количества данных
        min_periods = self.get_min_periods()
        if len(data) < min_periods:
            logger.warning(
                f"Insufficient data for {self.name}: {len(data)} < {min_periods}"
            )
            return False
            
        return True
        
    def safe_calculate(self, data: pd.DataFrame) -> Optional[IndicatorResult]:
        """
        Безопасный расчет индикатора с обработкой ошибок
        
        Args:
            data: DataFrame с рыночными данными
            
        Returns:
            Результат расчета или None при ошибке
        """
        if not self.enabled:
            logger.debug(f"{self.name} indicator is disabled")
            return None
            
        if not self.is_data_valid(data):
            return None
            
        try:
            # Проверка кэша
            cache_key = f"{len(data)}_{data.index[-1]}"
            if cache_key in self._cache:
                logger.debug(f"Using cached result for {self.name}")
                return self._cache[cache_key]
                
            # Расчет индикатора
            result = self.calculate(data)
            
            # Кэширование результата
            self._cache[cache_key] = result
            
            # Ограничение размера кэша
            if len(self._cache) > 100:
                # Удаляем старые записи
                oldest_key = list(self._cache.keys())[0]
                del self._cache[oldest_key]
                
            return result
            
        except Exception as e:
            logger.error(f"Error calculating {self.name}: {e}")
            return None
            
    def get_signal_interpretation(self, result: IndicatorResult) -> str:
        """
        Интерпретация сигнала индикатора
        
        Args:
            result: Результат расчета
            
        Returns:
            Текстовое описание сигнала
        """
        if result.signal == 1:
            signal_type = "Бычий"
        elif result.signal == -1:
            signal_type = "Медвежий"
        else:
            signal_type = "Нейтральный"
            
        if result.strength >= 70:
            strength_desc = "сильный"
        elif result.strength >= 40:
            strength_desc = "умеренный"
        else:
            strength_desc = "слабый"
            
        return f"{strength_desc} {signal_type.lower()} сигнал"
        
    def reset_cache(self) -> None:
        """Сброс кэша расчетов"""
        self._cache.clear()
        self._last_calculation_index = None
        
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """Расчет простой скользящей средней"""
        return data.rolling(window=period).mean()
        
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Расчет экспоненциальной скользящей средней"""
        return data.ewm(span=period, adjust=False).mean()
        
    @staticmethod
    def calculate_std(data: pd.Series, period: int) -> pd.Series:
        """Расчет стандартного отклонения"""
        return data.rolling(window=period).std()
        
    @staticmethod
    def normalize_value(value: float, min_val: float, max_val: float) -> float:
        """Нормализация значения в диапазон 0-100"""
        if max_val == min_val:
            return 50.0
            
        normalized = (value - min_val) / (max_val - min_val) * 100
        return max(0, min(100, normalized))
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, enabled={self.enabled})"