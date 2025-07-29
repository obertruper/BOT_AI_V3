"""
EMA (Exponential Moving Average) индикатор
Экспоненциальная скользящая средняя для определения тренда
"""
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging

from ..base import IndicatorBase, IndicatorConfig, IndicatorResult

logger = logging.getLogger(__name__)


class EMAIndicator(IndicatorBase):
    """
    Индикатор EMA (Exponential Moving Average)
    
    Параметры из AI кросс-верификации:
    - Периоды: [12, 26, 50, 200] для разных временных горизонтов
    - Использует множественные EMA для подтверждения тренда
    - Анализирует расположение цены относительно EMA
    """
    
    def __init__(self, config: IndicatorConfig):
        """
        Инициализация EMA индикатора
        
        Args:
            config: Конфигурация с параметрами:
                - periods: Список периодов EMA (по умолчанию [12, 26, 50, 200])
                - price_type: Тип цены для расчета (по умолчанию 'close')
        """
        super().__init__(config)
        
    def _validate_params(self) -> None:
        """Валидация параметров EMA"""
        # Периоды
        self.periods = self.params.get('periods', [12, 26, 50, 200])
        if not isinstance(self.periods, list) or not self.periods:
            raise ValueError(f"EMA periods must be a non-empty list, got {self.periods}")
            
        # Проверка что все периоды - положительные числа
        for period in self.periods:
            if not isinstance(period, (int, float)) or period < 1:
                raise ValueError(f"EMA period must be positive number, got {period}")
                
        # Сортировка периодов по возрастанию
        self.periods = sorted(self.periods)
        
        # Тип цены
        self.price_type = self.params.get('price_type', 'close')
        if self.price_type not in ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']:
            raise ValueError(f"Unknown price type: {self.price_type}")
            
        logger.debug(
            f"EMA initialized: periods={self.periods}, price_type={self.price_type}"
        )
        
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """
        Расчет EMA
        
        Args:
            data: DataFrame с ценами
            
        Returns:
            Результат с сигналом и значениями EMA
        """
        # Получение ценовых данных
        price_series = self._get_price_series(data)
        
        # Расчет всех EMA
        emas = {}
        for period in self.periods:
            ema = self.calculate_ema(price_series, period)
            emas[f'ema_{period}'] = ema
            
        # Текущие значения
        current_price = price_series.iloc[-1]
        current_emas = {k: v.iloc[-1] for k, v in emas.items()}
        
        # Определение сигнала
        signal = self._determine_signal(current_price, current_emas, emas)
        
        # Расчет силы сигнала
        strength = self._calculate_strength(current_price, current_emas)
        
        # Анализ структуры EMA
        ema_structure = self._analyze_ema_structure(current_emas)
        
        # Метаданные
        metadata = {
            'price': round(current_price, 2),
            'emas': {k: round(v, 2) for k, v in current_emas.items()},
            'structure': ema_structure,
            'trend_strength': self._calculate_trend_strength(price_series, emas),
            'golden_cross': self._check_golden_cross(emas),
            'death_cross': self._check_death_cross(emas)
        }
        
        return IndicatorResult(
            name=self.name,
            signal=signal,
            strength=strength,
            value=current_emas,
            timestamp=data.index[-1],
            metadata=metadata
        )
        
    def _get_price_series(self, data: pd.DataFrame) -> pd.Series:
        """
        Получение серии цен в зависимости от типа
        
        Args:
            data: DataFrame с ценами
            
        Returns:
            Серия цен
        """
        if self.price_type == 'close':
            return data['close']
        elif self.price_type == 'open':
            return data['open']
        elif self.price_type == 'high':
            return data['high']
        elif self.price_type == 'low':
            return data['low']
        elif self.price_type == 'hl2':
            return (data['high'] + data['low']) / 2
        elif self.price_type == 'hlc3':
            return (data['high'] + data['low'] + data['close']) / 3
        elif self.price_type == 'ohlc4':
            return (data['open'] + data['high'] + data['low'] + data['close']) / 4
            
    def _determine_signal(self, 
                         current_price: float, 
                         current_emas: Dict[str, float],
                         ema_series: Dict[str, pd.Series]) -> int:
        """
        Определение торгового сигнала на основе EMA
        
        Args:
            current_price: Текущая цена
            current_emas: Текущие значения EMA
            ema_series: Серии EMA
            
        Returns:
            -1 (продажа), 0 (удержание), 1 (покупка)
        """
        # Подсчет EMA выше и ниже цены
        emas_below = sum(1 for ema in current_emas.values() if current_price > ema)
        emas_above = sum(1 for ema in current_emas.values() if current_price < ema)
        total_emas = len(current_emas)
        
        # Проверка пересечений краткосрочных EMA
        short_ema_key = f'ema_{self.periods[0]}'
        if short_ema_key in ema_series and len(ema_series[short_ema_key]) >= 2:
            prev_ema = ema_series[short_ema_key].iloc[-2]
            curr_ema = ema_series[short_ema_key].iloc[-1]
            prev_price = ema_series[short_ema_key].index[-2]
            
            # Пересечение краткосрочной EMA снизу вверх
            if prev_price < prev_ema and current_price > curr_ema:
                return 1
                
            # Пересечение краткосрочной EMA сверху вниз
            elif prev_price > prev_ema and current_price < curr_ema:
                return -1
                
        # Сигнал на основе расположения относительно всех EMA
        if emas_below >= total_emas * 0.75:  # Цена выше 75% EMA
            return 1
        elif emas_above >= total_emas * 0.75:  # Цена ниже 75% EMA
            return -1
        else:
            return 0
            
    def _calculate_strength(self, 
                          current_price: float, 
                          current_emas: Dict[str, float]) -> float:
        """
        Расчет силы сигнала (0-100)
        
        Args:
            current_price: Текущая цена
            current_emas: Текущие значения EMA
            
        Returns:
            Сила сигнала от 0 до 100
        """
        strengths = []
        
        # Расчет отклонения от каждой EMA
        for ema_key, ema_value in current_emas.items():
            # Процентное отклонение
            deviation_pct = abs((current_price - ema_value) / ema_value * 100)
            
            # Конвертация в силу (больше отклонение = сильнее сигнал)
            strength = min(100, deviation_pct * 10)
            strengths.append(strength)
            
        # Средняя сила с учетом согласованности
        avg_strength = np.mean(strengths)
        
        # Бонус за согласованность (все EMA с одной стороны)
        emas_below = sum(1 for ema in current_emas.values() if current_price > ema)
        emas_above = sum(1 for ema in current_emas.values() if current_price < ema)
        
        if emas_below == len(current_emas) or emas_above == len(current_emas):
            avg_strength = min(100, avg_strength * 1.2)
            
        return avg_strength
        
    def _analyze_ema_structure(self, current_emas: Dict[str, float]) -> str:
        """
        Анализ структуры EMA (бычья, медвежья, смешанная)
        
        Args:
            current_emas: Текущие значения EMA
            
        Returns:
            Тип структуры
        """
        # Получаем EMA в порядке периодов
        sorted_emas = []
        for period in self.periods:
            key = f'ema_{period}'
            if key in current_emas:
                sorted_emas.append(current_emas[key])
                
        if len(sorted_emas) < 2:
            return "undefined"
            
        # Проверка порядка EMA
        # Бычья: краткосрочные > долгосрочные
        is_bullish = all(sorted_emas[i] >= sorted_emas[i+1] 
                        for i in range(len(sorted_emas)-1))
        
        # Медвежья: краткосрочные < долгосрочные
        is_bearish = all(sorted_emas[i] <= sorted_emas[i+1] 
                        for i in range(len(sorted_emas)-1))
        
        if is_bullish:
            return "bullish"
        elif is_bearish:
            return "bearish"
        else:
            return "mixed"
            
    def _calculate_trend_strength(self, 
                                prices: pd.Series, 
                                emas: Dict[str, pd.Series]) -> float:
        """
        Расчет силы тренда (0-100)
        
        Args:
            prices: Серия цен
            emas: Словарь серий EMA
            
        Returns:
            Сила тренда
        """
        if len(prices) < 20:
            return 0.0
            
        strengths = []
        
        # Для каждой EMA считаем процент времени, когда цена была выше/ниже
        for ema_key, ema_series in emas.items():
            recent_prices = prices.iloc[-20:]
            recent_ema = ema_series.iloc[-20:]
            
            # Процент времени выше EMA
            pct_above = (recent_prices > recent_ema).sum() / len(recent_prices) * 100
            
            # Сила = отклонение от 50% (чем дальше от 50, тем сильнее тренд)
            strength = abs(pct_above - 50) * 2
            strengths.append(strength)
            
        return np.mean(strengths)
        
    def _check_golden_cross(self, emas: Dict[str, pd.Series]) -> bool:
        """
        Проверка золотого креста (50 EMA пересекает 200 EMA снизу вверх)
        
        Args:
            emas: Словарь серий EMA
            
        Returns:
            True если обнаружен золотой крест
        """
        ema_50 = emas.get('ema_50')
        ema_200 = emas.get('ema_200')
        
        if ema_50 is None or ema_200 is None or len(ema_50) < 2:
            return False
            
        # Проверка пересечения
        prev_50 = ema_50.iloc[-2]
        curr_50 = ema_50.iloc[-1]
        prev_200 = ema_200.iloc[-2]
        curr_200 = ema_200.iloc[-1]
        
        return prev_50 < prev_200 and curr_50 > curr_200
        
    def _check_death_cross(self, emas: Dict[str, pd.Series]) -> bool:
        """
        Проверка креста смерти (50 EMA пересекает 200 EMA сверху вниз)
        
        Args:
            emas: Словарь серий EMA
            
        Returns:
            True если обнаружен крест смерти
        """
        ema_50 = emas.get('ema_50')
        ema_200 = emas.get('ema_200')
        
        if ema_50 is None or ema_200 is None or len(ema_50) < 2:
            return False
            
        # Проверка пересечения
        prev_50 = ema_50.iloc[-2]
        curr_50 = ema_50.iloc[-1]
        prev_200 = ema_200.iloc[-2]
        curr_200 = ema_200.iloc[-1]
        
        return prev_50 > prev_200 and curr_50 < curr_200
        
    def get_required_columns(self) -> List[str]:
        """Необходимые колонки данных"""
        if self.price_type in ['close', 'open', 'high', 'low']:
            return [self.price_type]
        elif self.price_type == 'hl2':
            return ['high', 'low']
        elif self.price_type == 'hlc3':
            return ['high', 'low', 'close']
        elif self.price_type == 'ohlc4':
            return ['open', 'high', 'low', 'close']
            
    def get_min_periods(self) -> int:
        """Минимальное количество периодов для расчета"""
        return max(self.periods) + 1