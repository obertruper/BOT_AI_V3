#!/usr/bin/env python3
"""
Динамический калькулятор Stop Loss и Take Profit

Рассчитывает оптимальные уровни SL/TP на основе:
- Волатильности (ATR)
- Уверенности ML модели
- RSI и других индикаторов
- Объема торгов
"""

import logging
from datetime import datetime

import numpy as np


class DynamicSLTPCalculator:
    """
    Калькулятор динамических уровней SL/TP

    Математическая модель:
    - SL: 1% - 2% (адаптивно к волатильности)
    - TP: 3.6% - 6% (соотношение risk/reward 1:3+)
    - Точка безубыточности: Win Rate ≥ 22-25%
    """

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        # Базовые параметры (в процентах)
        self.base_sl = 1.0  # Минимальный SL: 1%
        self.max_sl = 2.0  # Максимальный SL: 2%
        self.base_tp = 3.6  # Минимальный TP: 3.6%
        self.max_tp = 6.0  # Максимальный TP: 6%

        # Веса факторов влияния
        self.volatility_weight = 0.5  # Основной фактор
        self.rsi_weight = 0.15  # RSI влияние
        self.volume_weight = 0.15  # Объем
        self.trend_weight = 0.2  # Сила тренда

        # Кеш последних расчетов для анализа
        self._calculation_history: list[dict] = []
        self._max_history = 100

    def calculate_dynamic_levels(
        self,
        symbol: str,
        current_price: float,
        candles: list[dict],
        confidence: float,
        signal_type: str = "LONG",
        extra_indicators: dict | None = None,
    ) -> dict[str, float]:
        """
        Рассчитать динамические уровни SL и TP

        Args:
            symbol: Торговый символ
            current_price: Текущая цена
            candles: Последние свечи для расчета ATR
            confidence: Уверенность ML модели (0-1)
            signal_type: Тип сигнала (LONG/SHORT)
            extra_indicators: Дополнительные индикаторы (RSI, объем и т.д.)

        Returns:
            Dict с уровнями SL, TP и дополнительной информацией
        """
        try:
            # 1. Рассчитываем волатильность через ATR
            atr_value, volatility_factor = self._calculate_atr_volatility(candles, current_price)

            # 2. Получаем дополнительные факторы
            rsi_factor = self._get_rsi_factor(extra_indicators)
            volume_factor = self._get_volume_factor(extra_indicators)
            trend_factor = self._get_trend_factor(candles)

            # 3. Комбинированный множитель (0-1)
            combined_multiplier = (
                volatility_factor * self.volatility_weight
                + rsi_factor * self.rsi_weight
                + volume_factor * self.volume_weight
                + trend_factor * self.trend_weight
            )

            # Ограничиваем множитель
            combined_multiplier = max(0, min(1, combined_multiplier))

            # 4. Базовые динамические уровни
            dynamic_sl_pct = self.base_sl + (self.max_sl - self.base_sl) * combined_multiplier
            dynamic_tp_pct = self.base_tp + (self.max_tp - self.base_tp) * combined_multiplier

            # 5. Корректировка по уверенности ML модели
            dynamic_sl_pct, dynamic_tp_pct = self._adjust_by_confidence(
                dynamic_sl_pct, dynamic_tp_pct, confidence
            )

            # 6. Корректировка по RSI (перекупленность/перепроданность)
            if extra_indicators and "rsi" in extra_indicators:
                rsi = extra_indicators["rsi"]
                if signal_type == "LONG":
                    if rsi > 70:  # Перекупленность - увеличиваем SL
                        dynamic_sl_pct *= 1.1
                        self.logger.debug(f"RSI {rsi:.1f} > 70: увеличен SL для LONG")
                    elif rsi < 30:  # Перепроданность - увеличиваем TP
                        dynamic_tp_pct *= 1.1
                        self.logger.debug(f"RSI {rsi:.1f} < 30: увеличен TP для LONG")
                else:  # SHORT
                    if rsi < 30:  # Перепроданность - увеличиваем SL для SHORT
                        dynamic_sl_pct *= 1.1
                    elif rsi > 70:  # Перекупленность - увеличиваем TP для SHORT
                        dynamic_tp_pct *= 1.1

            # 7. Учет времени торговой сессии
            session_multiplier = self._get_session_multiplier()
            if session_multiplier < 1.0:
                dynamic_sl_pct *= session_multiplier
                dynamic_tp_pct *= session_multiplier
                self.logger.debug(
                    f"Азиатская сессия: уровни уменьшены на {(1-session_multiplier)*100:.0f}%"
                )

            # 8. Рассчитываем абсолютные уровни цен
            if signal_type == "LONG":
                sl_price = current_price * (1 - dynamic_sl_pct / 100)
                tp_price = current_price * (1 + dynamic_tp_pct / 100)
            else:  # SHORT
                sl_price = current_price * (1 + dynamic_sl_pct / 100)
                tp_price = current_price * (1 - dynamic_tp_pct / 100)

            # 9. Рассчитываем уровни для частичного закрытия
            partial_tp_levels = self._calculate_partial_tp_levels(
                current_price, dynamic_tp_pct, signal_type
            )

            # 10. Рассчитываем математическое ожидание
            risk_reward_ratio = dynamic_tp_pct / dynamic_sl_pct
            breakeven_win_rate = 1 / (1 + risk_reward_ratio)
            expected_value = self._calculate_expected_value(
                dynamic_sl_pct, dynamic_tp_pct, confidence
            )

            result = {
                "sl_price": sl_price,
                "tp_price": tp_price,
                "sl_percent": dynamic_sl_pct,
                "tp_percent": dynamic_tp_pct,
                "partial_tp_levels": partial_tp_levels,
                "risk_reward_ratio": risk_reward_ratio,
                "breakeven_win_rate": breakeven_win_rate,
                "expected_value": expected_value,
                "volatility_factor": volatility_factor,
                "combined_multiplier": combined_multiplier,
                "atr": atr_value,
                "calculation_time": datetime.utcnow().isoformat(),
            }

            # Сохраняем в историю
            self._save_to_history(symbol, result)

            # Логирование
            self.logger.info(
                f"📊 {symbol} Динамические уровни: "
                f"SL={dynamic_sl_pct:.2f}% (${sl_price:.4f}), "
                f"TP={dynamic_tp_pct:.2f}% (${tp_price:.4f}), "
                f"R:R=1:{risk_reward_ratio:.1f}, "
                f"EV={expected_value:.3f}%"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка расчета динамических уровней: {e}")
            # Возвращаем базовые уровни при ошибке
            return self._get_fallback_levels(current_price, signal_type)

    def _calculate_atr_volatility(
        self, candles: list[dict], current_price: float, period: int = 14
    ) -> tuple[float, float]:
        """
        Рассчитать ATR и нормализованную волатильность

        Returns:
            (ATR значение, нормализованный фактор 0-1)
        """
        if not candles or len(candles) < period:
            self.logger.warning(f"Недостаточно данных для ATR: {len(candles)} свечей")
            return 0.02 * current_price, 0.5  # Средняя волатильность по умолчанию

        try:
            # Рассчитываем True Range для каждой свечи
            true_ranges = []
            for i in range(1, min(len(candles), period + 1)):
                high = candles[-i].get("high", 0)
                low = candles[-i].get("low", 0)
                prev_close = candles[-i - 1].get("close", 0) if i < len(candles) else current_price

                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                true_ranges.append(tr)

            # ATR = среднее True Range
            atr = np.mean(true_ranges) if true_ranges else 0.02 * current_price

            # Нормализуем волатильность (ATR/Price)
            volatility_ratio = atr / current_price

            # Нормализация к диапазону 0-1
            # Считаем 1% волатильности низкой (0), 3% высокой (1)
            normalized = min(max((volatility_ratio - 0.01) / 0.02, 0), 1)

            self.logger.debug(
                f"ATR={atr:.4f}, Ratio={volatility_ratio:.4f}, " f"Normalized={normalized:.2f}"
            )

            return atr, normalized

        except Exception as e:
            self.logger.error(f"Ошибка расчета ATR: {e}")
            return 0.02 * current_price, 0.5

    def _get_rsi_factor(self, indicators: dict | None) -> float:
        """Получить фактор RSI (0-1)"""
        if not indicators or "rsi" not in indicators:
            return 0.5  # Нейтральное значение

        rsi = indicators["rsi"]

        # Экстремальные значения дают высокий фактор
        if rsi > 80 or rsi < 20:
            return 0.9
        elif rsi > 70 or rsi < 30:
            return 0.7
        elif rsi > 60 or rsi < 40:
            return 0.5
        else:
            return 0.3  # Нейтральная зона

    def _get_volume_factor(self, indicators: dict | None) -> float:
        """Получить фактор объема (0-1)"""
        if not indicators or "volume_ratio" not in indicators:
            return 0.5

        # volume_ratio = текущий объем / средний объем
        ratio = indicators["volume_ratio"]

        if ratio > 2.0:  # Очень высокий объем
            return 0.9
        elif ratio > 1.5:
            return 0.7
        elif ratio > 1.0:
            return 0.5
        else:
            return 0.3  # Низкий объем

    def _get_trend_factor(self, candles: list[dict]) -> float:
        """Получить фактор силы тренда (0-1)"""
        if not candles or len(candles) < 20:
            return 0.5

        try:
            # Простой метод: сравниваем SMA
            closes = [c.get("close", 0) for c in candles[-20:]]
            sma5 = np.mean(closes[-5:])
            sma20 = np.mean(closes)

            # Процент отклонения
            deviation = abs(sma5 - sma20) / sma20

            # Нормализация (0-2% отклонения)
            factor = min(deviation / 0.02, 1.0)

            return factor

        except Exception:
            return 0.5

    def _adjust_by_confidence(
        self, sl_pct: float, tp_pct: float, confidence: float
    ) -> tuple[float, float]:
        """
        Корректировка уровней по уверенности модели

        При низкой уверенности - увеличиваем TP (нужно больше прибыли)
        При высокой уверенности - можем уменьшить SL (меньше риск)
        """
        if confidence < 0.35:
            # Низкая уверенность - увеличиваем TP на 15%
            tp_pct *= 1.15
            self.logger.debug(f"Низкая уверенность {confidence:.2f}: TP увеличен на 15%")
        elif confidence > 0.60:
            # Высокая уверенность - уменьшаем SL на 15%
            sl_pct *= 0.85
            self.logger.debug(f"Высокая уверенность {confidence:.2f}: SL уменьшен на 15%")

        # Ограничиваем финальные значения
        sl_pct = max(self.base_sl, min(self.max_sl, sl_pct))
        tp_pct = max(self.base_tp, min(self.max_tp, tp_pct))

        return sl_pct, tp_pct

    def _get_session_multiplier(self) -> float:
        """
        Получить множитель для торговой сессии

        Азиатская сессия (00:00-08:00 UTC): 0.8 (меньше волатильность)
        Европейская (08:00-16:00 UTC): 1.0
        Американская (14:00-22:00 UTC): 1.0
        """
        current_hour = datetime.utcnow().hour

        if 0 <= current_hour < 8:
            return 0.8  # Азиатская сессия
        else:
            return 1.0  # Европейская/Американская

    def _calculate_partial_tp_levels(
        self, entry_price: float, tp_percent: float, signal_type: str
    ) -> list[dict[str, float]]:
        """
        Рассчитать уровни для частичного закрытия

        Level 1: 30% позиции при 40% от TP
        Level 2: 30% позиции при 70% от TP
        Level 3: 40% позиции при 100% от TP
        """
        levels = []

        # Коэффициенты для уровней
        level_ratios = [0.4, 0.7, 1.0]
        level_percents = [30, 30, 40]

        for i, (ratio, percent) in enumerate(zip(level_ratios, level_percents, strict=False)):
            level_tp_pct = tp_percent * ratio

            if signal_type == "LONG":
                price = entry_price * (1 + level_tp_pct / 100)
            else:  # SHORT
                price = entry_price * (1 - level_tp_pct / 100)

            levels.append(
                {
                    "level": i + 1,
                    "price": price,
                    "percent_of_position": percent,
                    "profit_percent": level_tp_pct,
                }
            )

        return levels

    def _calculate_expected_value(self, sl_pct: float, tp_pct: float, win_rate: float) -> float:
        """
        Рассчитать математическое ожидание сделки

        EV = (TP * WinRate) - (SL * (1 - WinRate))
        """
        # Используем confidence как приближение win_rate
        # Но корректируем, так как confidence обычно 0.3-0.6
        adjusted_win_rate = 0.3 + win_rate * 0.4  # Диапазон 0.3-0.7

        ev = (tp_pct * adjusted_win_rate) - (sl_pct * (1 - adjusted_win_rate))

        return ev

    def _get_fallback_levels(self, current_price: float, signal_type: str) -> dict:
        """Вернуть базовые уровни при ошибке расчета"""
        self.logger.warning("Используем базовые уровни SL/TP")

        if signal_type == "LONG":
            sl_price = current_price * 0.985  # -1.5%
            tp_price = current_price * 1.045  # +4.5%
        else:
            sl_price = current_price * 1.015  # +1.5%
            tp_price = current_price * 0.955  # -4.5%

        return {
            "sl_price": sl_price,
            "tp_price": tp_price,
            "sl_percent": 1.5,
            "tp_percent": 4.5,
            "partial_tp_levels": self._calculate_partial_tp_levels(current_price, 4.5, signal_type),
            "risk_reward_ratio": 3.0,
            "breakeven_win_rate": 0.25,
            "expected_value": 1.0,
            "volatility_factor": 0.5,
            "combined_multiplier": 0.5,
            "atr": 0.02 * current_price,
        }

    def _save_to_history(self, symbol: str, result: dict):
        """Сохранить расчет в историю для анализа"""
        record = {"symbol": symbol, "timestamp": datetime.utcnow().isoformat(), **result}

        self._calculation_history.append(record)

        # Ограничиваем размер истории
        if len(self._calculation_history) > self._max_history:
            self._calculation_history = self._calculation_history[-self._max_history :]

    def get_statistics(self) -> dict:
        """Получить статистику по последним расчетам"""
        if not self._calculation_history:
            return {}

        sl_values = [r["sl_percent"] for r in self._calculation_history]
        tp_values = [r["tp_percent"] for r in self._calculation_history]
        ev_values = [r["expected_value"] for r in self._calculation_history]

        return {
            "calculations_count": len(self._calculation_history),
            "avg_sl": np.mean(sl_values),
            "avg_tp": np.mean(tp_values),
            "avg_risk_reward": np.mean([r["risk_reward_ratio"] for r in self._calculation_history]),
            "avg_expected_value": np.mean(ev_values),
            "positive_ev_rate": sum(1 for ev in ev_values if ev > 0) / len(ev_values) * 100,
        }
