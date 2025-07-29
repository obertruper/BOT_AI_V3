"""
Генератор торговых сигналов для indicator_strategy
Преобразует результаты анализа индикаторов в конкретные торговые сигналы
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from strategies.base import TradingSignal, SignalType, MarketData

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Генератор торговых сигналов на основе скоринга индикаторов"""
    
    def __init__(self, risk_config: Dict[str, Any], signal_threshold: float = 50):
        """
        Инициализация генератора сигналов
        
        Args:
            risk_config: Конфигурация управления рисками
            signal_threshold: Минимальный порог для генерации сигнала
        """
        self.risk_config = risk_config
        self.signal_threshold = signal_threshold
        
        # Параметры для расчета SL/TP
        self.atr_multiplier_sl = risk_config.get('atr_multiplier_sl', 2.0)
        self.atr_multiplier_tp = risk_config.get('atr_multiplier_tp', 3.0)
        self.fixed_sl_pct = risk_config.get('fixed_sl_pct', 3.0)
        self.fixed_tp_pct = risk_config.get('fixed_tp_pct', 6.0)
        
        # Параметры для multi-level TP
        self.tp_levels = risk_config.get('tp_levels', [1.5, 3.0, 5.0])
        self.partial_close_pcts = risk_config.get('partial_close_pcts', [0.33, 0.33, 0.34])
        
    def generate_signal(self,
                       market_data: MarketData,
                       total_score: float,
                       indicators: Dict[str, Any],
                       market_regime: str) -> Optional[TradingSignal]:
        """
        Генерация торгового сигнала
        
        Args:
            market_data: Текущие рыночные данные
            total_score: Общий скор от -100 до +100
            indicators: Рассчитанные индикаторы
            market_regime: Текущий режим рынка
            
        Returns:
            Торговый сигнал или None
        """
        # Проверка порога
        if abs(total_score) < self.signal_threshold:
            logger.debug(f"Score {total_score} below threshold {self.signal_threshold}")
            return None
            
        # Определение направления
        signal_type = self._determine_signal_type(total_score)
        if signal_type == SignalType.HOLD:
            return None
            
        # Расчет уровней входа, SL и TP
        entry_price = market_data.close
        stop_loss, take_profit = self._calculate_risk_levels(
            signal_type,
            entry_price,
            indicators,
            market_regime
        )
        
        # Расчет размера позиции
        position_size = self._calculate_position_size(
            abs(total_score),
            market_regime,
            indicators
        )
        
        # Оценка ожидаемой длительности
        expected_duration = self._estimate_trade_duration(market_regime, abs(total_score))
        
        # Создание сигнала
        signal = TradingSignal(
            timestamp=market_data.timestamp,
            symbol=market_data.symbol,
            signal_type=signal_type,
            confidence=abs(total_score),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            strategy_name="indicator_strategy",
            timeframe=market_data.timeframe,
            indicators_used=self._get_active_indicators(indicators),
            reasoning=self._generate_reasoning(total_score, indicators, market_regime),
            risk_reward_ratio=abs(take_profit - entry_price) / abs(entry_price - stop_loss),
            expected_duration_hours=expected_duration,
            metadata={
                'market_regime': market_regime,
                'score_breakdown': self._get_score_breakdown(indicators),
                'tp_levels': self._calculate_tp_levels(signal_type, entry_price, take_profit)
            }
        )
        
        return signal
        
    def _determine_signal_type(self, total_score: float) -> SignalType:
        """Определение типа сигнала на основе скора"""
        if total_score >= self.signal_threshold:
            return SignalType.BUY
        elif total_score <= -self.signal_threshold:
            return SignalType.SELL
        else:
            return SignalType.HOLD
            
    def _calculate_risk_levels(self,
                             signal_type: SignalType,
                             entry_price: float,
                             indicators: Dict[str, Any],
                             market_regime: str) -> Tuple[float, float]:
        """
        Расчет уровней Stop Loss и Take Profit
        
        Returns:
            (stop_loss, take_profit)
        """
        # Получение ATR если доступен
        atr_value = None
        if 'volatility' in indicators and 'atr' in indicators['volatility']:
            atr_data = indicators['volatility']['atr']
            if isinstance(atr_data, dict) and 'atr' in atr_data:
                atr_value = atr_data['atr']
                
        # Адаптивный расчет на основе режима рынка
        if market_regime == 'high_volatility' and atr_value:
            # Используем ATR для волатильного рынка
            if signal_type == SignalType.BUY:
                stop_loss = entry_price - (atr_value * self.atr_multiplier_sl)
                take_profit = entry_price + (atr_value * self.atr_multiplier_tp)
            else:
                stop_loss = entry_price + (atr_value * self.atr_multiplier_sl)
                take_profit = entry_price - (atr_value * self.atr_multiplier_tp)
        else:
            # Фиксированные проценты для стабильного рынка
            sl_pct = self.fixed_sl_pct / 100
            tp_pct = self.fixed_tp_pct / 100
            
            if signal_type == SignalType.BUY:
                stop_loss = entry_price * (1 - sl_pct)
                take_profit = entry_price * (1 + tp_pct)
            else:
                stop_loss = entry_price * (1 + sl_pct)
                take_profit = entry_price * (1 - tp_pct)
                
        return stop_loss, take_profit
        
    def _calculate_position_size(self,
                               confidence: float,
                               market_regime: str,
                               indicators: Dict[str, Any]) -> float:
        """
        Расчет размера позиции с учетом уверенности и режима рынка
        
        Returns:
            Размер позиции в процентах от депозита
        """
        # Базовый размер
        max_size = self.risk_config.get('max_position_size', 5.0)
        min_size = self.risk_config.get('min_position_size', 0.5)
        
        # Фактор уверенности (0.5 - 1.0)
        confidence_factor = 0.5 + (confidence / 100) * 0.5
        
        # Фактор режима рынка
        regime_factor = 1.0
        if market_regime == 'high_volatility':
            regime_factor = 0.7  # Уменьшаем размер при высокой волатильности
        elif market_regime == 'trending':
            regime_factor = 1.2  # Увеличиваем при трендовом рынке
            
        # Расчет финального размера
        position_size = max_size * confidence_factor * regime_factor
        
        # Ограничения
        position_size = max(min_size, min(position_size, max_size))
        
        return round(position_size, 2)
        
    def _estimate_trade_duration(self, market_regime: str, confidence: float) -> float:
        """
        Оценка ожидаемой длительности сделки в часах
        
        Returns:
            Ожидаемая длительность в часах
        """
        # Базовая длительность для swing trading (1-7 дней)
        base_duration = 72  # 3 дня в часах
        
        # Корректировка на основе режима рынка
        if market_regime == 'trending':
            # В тренде держим позиции дольше
            duration_multiplier = 1.5
        elif market_regime == 'high_volatility':
            # При высокой волатильности сокращаем время
            duration_multiplier = 0.5
        else:
            duration_multiplier = 1.0
            
        # Корректировка на основе уверенности
        # Чем выше уверенность, тем дольше держим
        confidence_multiplier = 0.7 + (confidence / 100) * 0.6
        
        estimated_duration = base_duration * duration_multiplier * confidence_multiplier
        
        # Ограничения: от 24 часов до 7 дней
        return max(24, min(estimated_duration, 168))
        
    def _calculate_tp_levels(self,
                           signal_type: SignalType,
                           entry_price: float,
                           final_tp: float) -> List[Dict[str, float]]:
        """
        Расчет уровней частичного закрытия позиции
        
        Returns:
            Список уровней с процентами закрытия
        """
        levels = []
        
        # Расстояние до финального TP
        tp_distance = abs(final_tp - entry_price)
        
        for i, (level_multiplier, close_pct) in enumerate(
            zip(self.tp_levels, self.partial_close_pcts)
        ):
            if signal_type == SignalType.BUY:
                tp_price = entry_price + (tp_distance * level_multiplier / max(self.tp_levels))
            else:
                tp_price = entry_price - (tp_distance * level_multiplier / max(self.tp_levels))
                
            levels.append({
                'level': i + 1,
                'price': round(tp_price, 2),
                'close_percent': close_pct * 100,
                'risk_reward': level_multiplier
            })
            
        return levels
        
    def _get_active_indicators(self, indicators: Dict[str, Any]) -> List[str]:
        """Получение списка активных индикаторов"""
        active = []
        
        for category, category_indicators in indicators.items():
            if isinstance(category_indicators, dict):
                for indicator_name, data in category_indicators.items():
                    if isinstance(data, dict) and 'signal' in data:
                        active.append(f"{category}.{indicator_name}")
                        
        return active
        
    def _get_score_breakdown(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Получение разбивки скора по категориям"""
        breakdown = {}
        
        for category, category_indicators in indicators.items():
            if isinstance(category_indicators, dict):
                category_scores = []
                for indicator_name, data in category_indicators.items():
                    if isinstance(data, dict) and 'signal' in data:
                        signal = data['signal']
                        strength = data.get('strength', 50)
                        category_scores.append(signal * strength)
                        
                if category_scores:
                    breakdown[category] = sum(category_scores) / len(category_scores)
                    
        return breakdown
        
    def _generate_reasoning(self,
                          total_score: float,
                          indicators: Dict[str, Any],
                          market_regime: str) -> str:
        """Генерация объяснения для сигнала"""
        direction = "бычий" if total_score > 0 else "медвежий"
        strength = "сильный" if abs(total_score) > 70 else "умеренный"
        
        reasoning = f"{strength} {direction} сигнал (скор: {total_score:.1f}) "
        reasoning += f"в режиме '{market_regime}'. "
        
        # Добавление ключевых факторов
        breakdown = self._get_score_breakdown(indicators)
        if breakdown:
            top_factors = sorted(breakdown.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            factors_str = ", ".join([f"{cat}: {score:.1f}" for cat, score in top_factors])
            reasoning += f"Ключевые факторы: {factors_str}. "
            
        # Рекомендация по времени удержания
        if market_regime == 'trending':
            reasoning += "Рекомендуется удерживать позицию дольше в трендовом рынке."
        elif market_regime == 'high_volatility':
            reasoning += "Рекомендуется более короткое удержание из-за высокой волатильности."
            
        return reasoning