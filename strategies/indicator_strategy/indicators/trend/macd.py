"""
MACD (Moving Average Convergence Divergence) индикатор
Измеряет схождение/расхождение скользящих средних для определения импульса тренда
"""
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import logging

from ..base import IndicatorBase, IndicatorConfig, IndicatorResult

logger = logging.getLogger(__name__)


class MACDIndicator(IndicatorBase):
    """
    Индикатор MACD (Moving Average Convergence Divergence)
    
    Параметры из AI кросс-верификации:
    - Fast EMA: 12 периодов
    - Slow EMA: 26 периодов  
    - Signal line: 9 периодов
    - Гистограмма для визуализации расхождения
    """
    
    def __init__(self, config: IndicatorConfig):
        """
        Инициализация MACD индикатора
        
        Args:
            config: Конфигурация с параметрами:
                - fast_period: Период быстрой EMA (по умолчанию 12)
                - slow_period: Период медленной EMA (по умолчанию 26)
                - signal_period: Период сигнальной линии (по умолчанию 9)
        """
        super().__init__(config)
        
    def _validate_params(self) -> None:
        """Валидация параметров MACD"""
        # Периоды
        self.fast_period = self.params.get('fast_period', 12)
        self.slow_period = self.params.get('slow_period', 26)
        self.signal_period = self.params.get('signal_period', 9)
        
        # Проверка типов
        for period, name in [(self.fast_period, 'fast_period'), 
                           (self.slow_period, 'slow_period'),
                           (self.signal_period, 'signal_period')]:
            if not isinstance(period, int) or period < 1:
                raise ValueError(f"MACD {name} must be positive integer, got {period}")
                
        # Проверка логики периодов
        if self.fast_period >= self.slow_period:
            raise ValueError(
                f"Fast period ({self.fast_period}) must be less than "
                f"slow period ({self.slow_period})"
            )
            
        logger.debug(
            f"MACD initialized: fast={self.fast_period}, "
            f"slow={self.slow_period}, signal={self.signal_period}"
        )
        
    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        """
        Расчет MACD
        
        Args:
            data: DataFrame с ценами
            
        Returns:
            Результат с сигналом и значениями MACD
        """
        # Расчет компонентов MACD
        close_prices = data['close']
        
        # EMA для MACD линии
        ema_fast = self.calculate_ema(close_prices, self.fast_period)
        ema_slow = self.calculate_ema(close_prices, self.slow_period)
        
        # MACD линия
        macd_line = ema_fast - ema_slow
        
        # Сигнальная линия (EMA от MACD)
        signal_line = self.calculate_ema(macd_line, self.signal_period)
        
        # Гистограмма
        histogram = macd_line - signal_line
        
        # Текущие значения
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        
        # Определение сигнала
        signal = self._determine_signal(
            macd_line, signal_line, histogram
        )
        
        # Расчет силы сигнала
        strength = self._calculate_strength(
            current_macd, current_signal, current_histogram, histogram
        )
        
        # Анализ дивергенций
        divergence = self._check_divergence(close_prices, macd_line)
        
        # Метаданные
        metadata = {
            'macd_line': round(current_macd, 4),
            'signal_line': round(current_signal, 4),
            'histogram': round(current_histogram, 4),
            'divergence': divergence,
            'trend': self._get_macd_trend(macd_line, signal_line),
            'histogram_trend': self._analyze_histogram_trend(histogram),
            'zero_cross': self._check_zero_cross(macd_line)
        }
        
        return IndicatorResult(
            name=self.name,
            signal=signal,
            strength=strength,
            value={
                'macd': current_macd,
                'signal': current_signal,
                'histogram': current_histogram
            },
            timestamp=data.index[-1],
            metadata=metadata
        )
        
    def _determine_signal(self,
                         macd_line: pd.Series,
                         signal_line: pd.Series,
                         histogram: pd.Series) -> int:
        """
        Определение торгового сигнала на основе MACD
        
        Args:
            macd_line: Серия значений MACD
            signal_line: Серия значений сигнальной линии
            histogram: Серия значений гистограммы
            
        Returns:
            -1 (продажа), 0 (удержание), 1 (покупка)
        """
        if len(macd_line) < 2:
            return 0
            
        # Текущие и предыдущие значения
        curr_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        curr_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        curr_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        
        # Пересечение MACD и сигнальной линии
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            # MACD пересекает сигнальную снизу вверх - покупка
            return 1
            
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            # MACD пересекает сигнальную сверху вниз - продажа
            return -1
            
        # Дополнительные сигналы по гистограмме
        elif prev_hist < 0 < curr_hist:
            # Гистограмма переходит из отрицательной в положительную
            return 1
            
        elif prev_hist > 0 > curr_hist:
            # Гистограмма переходит из положительной в отрицательную
            return -1
            
        else:
            # Нет явного сигнала
            return 0
            
    def _calculate_strength(self,
                          current_macd: float,
                          current_signal: float,
                          current_histogram: float,
                          histogram_series: pd.Series) -> float:
        """
        Расчет силы сигнала (0-100)
        
        Args:
            current_macd: Текущее значение MACD
            current_signal: Текущее значение сигнальной линии
            current_histogram: Текущее значение гистограммы
            histogram_series: Серия значений гистограммы
            
        Returns:
            Сила сигнала от 0 до 100
        """
        strengths = []
        
        # 1. Сила на основе расхождения MACD и сигнальной линии
        divergence_strength = abs(current_histogram)
        
        # Нормализация относительно исторических значений
        if len(histogram_series) >= 20:
            recent_hist = histogram_series.iloc[-20:]
            hist_std = recent_hist.std()
            if hist_std > 0:
                normalized_divergence = min(100, abs(current_histogram) / hist_std * 33)
                strengths.append(normalized_divergence)
                
        # 2. Сила на основе скорости изменения гистограммы
        if len(histogram_series) >= 5:
            hist_change = histogram_series.iloc[-1] - histogram_series.iloc[-5]
            hist_velocity = abs(hist_change) / 5
            
            # Нормализация скорости
            velocity_strength = min(100, hist_velocity * 100)
            strengths.append(velocity_strength)
            
        # 3. Сила на основе расстояния MACD от нулевой линии
        zero_distance = abs(current_macd)
        if len(histogram_series) >= 20:
            macd_values = histogram_series.iloc[-20:] + histogram_series.iloc[-20:].mean()
            macd_range = macd_values.max() - macd_values.min()
            if macd_range > 0:
                zero_strength = min(100, zero_distance / macd_range * 100)
                strengths.append(zero_strength)
                
        # Средняя сила
        if strengths:
            avg_strength = np.mean(strengths)
        else:
            # Fallback расчет
            avg_strength = min(100, abs(current_histogram) * 1000)
            
        return avg_strength
        
    def _check_divergence(self, prices: pd.Series, macd: pd.Series) -> Optional[str]:
        """
        Проверка дивергенций между ценой и MACD
        
        Args:
            prices: Серия цен
            macd: Серия значений MACD
            
        Returns:
            Тип дивергенции или None
        """
        if len(prices) < 30:
            return None
            
        # Анализ последних 30 периодов
        recent_prices = prices.iloc[-30:]
        recent_macd = macd.iloc[-30:]
        
        # Поиск локальных экстремумов
        price_peaks = self._find_peaks(recent_prices, distance=5)
        price_troughs = self._find_peaks(-recent_prices, distance=5)
        macd_peaks = self._find_peaks(recent_macd, distance=5)
        macd_troughs = self._find_peaks(-recent_macd, distance=5)
        
        # Индексы экстремумов
        price_peak_idx = self._get_peak_indices(recent_prices, distance=5)
        price_trough_idx = self._get_peak_indices(-recent_prices, distance=5)
        macd_peak_idx = self._get_peak_indices(recent_macd, distance=5)
        macd_trough_idx = self._get_peak_indices(-recent_macd, distance=5)
        
        # Проверка бычьей дивергенции
        if (len(price_trough_idx) >= 2 and len(macd_trough_idx) >= 2 and
            price_trough_idx[-1] > price_trough_idx[-2] + 3):
            
            # Цена делает более низкий минимум
            if (recent_prices.iloc[price_trough_idx[-1]] < 
                recent_prices.iloc[price_trough_idx[-2]]):
                
                # MACD делает более высокий минимум
                nearest_macd_trough = min(macd_trough_idx, 
                                        key=lambda x: abs(x - price_trough_idx[-1]))
                prev_macd_trough = min(macd_trough_idx,
                                     key=lambda x: abs(x - price_trough_idx[-2]))
                
                if (recent_macd.iloc[nearest_macd_trough] > 
                    recent_macd.iloc[prev_macd_trough]):
                    return "bullish_divergence"
                    
        # Проверка медвежьей дивергенции
        if (len(price_peak_idx) >= 2 and len(macd_peak_idx) >= 2 and
            price_peak_idx[-1] > price_peak_idx[-2] + 3):
            
            # Цена делает более высокий максимум
            if (recent_prices.iloc[price_peak_idx[-1]] > 
                recent_prices.iloc[price_peak_idx[-2]]):
                
                # MACD делает более низкий максимум
                nearest_macd_peak = min(macd_peak_idx,
                                      key=lambda x: abs(x - price_peak_idx[-1]))
                prev_macd_peak = min(macd_peak_idx,
                                   key=lambda x: abs(x - price_peak_idx[-2]))
                
                if (recent_macd.iloc[nearest_macd_peak] < 
                    recent_macd.iloc[prev_macd_peak]):
                    return "bearish_divergence"
                    
        return None
        
    def _find_peaks(self, series: pd.Series, distance: int = 3) -> List[float]:
        """
        Поиск локальных максимумов в серии
        
        Args:
            series: Анализируемая серия
            distance: Минимальное расстояние между пиками
            
        Returns:
            Список значений пиков
        """
        peaks = []
        values = series.values
        
        for i in range(distance, len(values) - distance):
            # Проверяем, является ли точка локальным максимумом
            if all(values[i] >= values[i-j] for j in range(1, distance+1)) and \
               all(values[i] >= values[i+j] for j in range(1, distance+1)):
                peaks.append(values[i])
                
        return peaks
        
    def _get_peak_indices(self, series: pd.Series, distance: int = 3) -> List[int]:
        """
        Получение индексов локальных максимумов
        
        Args:
            series: Анализируемая серия
            distance: Минимальное расстояние между пиками
            
        Returns:
            Список индексов пиков
        """
        indices = []
        values = series.values
        
        for i in range(distance, len(values) - distance):
            if all(values[i] >= values[i-j] for j in range(1, distance+1)) and \
               all(values[i] >= values[i+j] for j in range(1, distance+1)):
                indices.append(i)
                
        return indices
        
    def _get_macd_trend(self, macd_line: pd.Series, signal_line: pd.Series) -> str:
        """
        Определение тренда MACD
        
        Args:
            macd_line: Серия MACD
            signal_line: Серия сигнальной линии
            
        Returns:
            Направление тренда
        """
        if len(macd_line) < 5:
            return "undefined"
            
        # Текущее расположение
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        
        # Направление MACD
        macd_direction = "rising" if macd_line.iloc[-1] > macd_line.iloc[-5] else "falling"
        
        # Расположение относительно сигнальной линии
        position = "above" if current_macd > current_signal else "below"
        
        # Расположение относительно нуля
        zero_position = "positive" if current_macd > 0 else "negative"
        
        return f"{macd_direction}_{position}_{zero_position}"
        
    def _analyze_histogram_trend(self, histogram: pd.Series) -> str:
        """
        Анализ тренда гистограммы
        
        Args:
            histogram: Серия значений гистограммы
            
        Returns:
            Характеристика тренда
        """
        if len(histogram) < 5:
            return "undefined"
            
        recent_hist = histogram.iloc[-5:]
        
        # Проверка роста/падения
        if all(recent_hist.iloc[i] > recent_hist.iloc[i-1] 
               for i in range(1, len(recent_hist))):
            return "strongly_rising"
            
        elif all(recent_hist.iloc[i] < recent_hist.iloc[i-1] 
                for i in range(1, len(recent_hist))):
            return "strongly_falling"
            
        elif recent_hist.iloc[-1] > recent_hist.iloc[0]:
            return "rising"
            
        elif recent_hist.iloc[-1] < recent_hist.iloc[0]:
            return "falling"
            
        else:
            return "neutral"
            
    def _check_zero_cross(self, macd_line: pd.Series) -> Optional[str]:
        """
        Проверка пересечения нулевой линии
        
        Args:
            macd_line: Серия MACD
            
        Returns:
            Тип пересечения или None
        """
        if len(macd_line) < 2:
            return None
            
        prev_macd = macd_line.iloc[-2]
        curr_macd = macd_line.iloc[-1]
        
        if prev_macd < 0 <= curr_macd:
            return "bullish_zero_cross"
        elif prev_macd > 0 >= curr_macd:
            return "bearish_zero_cross"
            
        return None
        
    def get_required_columns(self) -> List[str]:
        """Необходимые колонки данных"""
        return ['close']
        
    def get_min_periods(self) -> int:
        """Минимальное количество периодов для расчета"""
        # Нужно достаточно данных для медленной EMA + сигнальной линии
        return self.slow_period + self.signal_period