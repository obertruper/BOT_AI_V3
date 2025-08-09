#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Адаптер для преобразования выходов UnifiedPatchTST модели в торговые сигналы
Адаптировано из LLM TRANSFORM для BOT_AI_V3
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

import numpy as np
import torch

from core.logger import setup_logger

logger = setup_logger(__name__)


class ModelOutputAdapter:
    """
    Преобразует 20 выходов UnifiedPatchTST в формат торговых сигналов

    20 выходов модели:
    - [0-3]: future_return_15m, 1h, 4h, 12h
    - [4-7]: direction_15m, 1h, 4h, 12h
    - [8-11]: volatility_15m, 1h, 4h, 12h
    - [12-15]: volume_change_15m, 1h, 4h, 12h
    - [16-19]: price_range_15m, 1h, 4h, 12h
    """

    def __init__(self):
        self.output_mapping = {
            "future_return": slice(0, 4),  # индексы 0-3
            "direction": slice(4, 8),  # индексы 4-7
            "volatility": slice(8, 12),  # индексы 8-11
            "volume_change": slice(12, 16),  # индексы 12-15
            "price_range": slice(16, 20),  # индексы 16-19
        }

        self.timeframes = ["15m", "1h", "4h", "12h"]

    def adapt_model_outputs(
        self,
        raw_outputs: Union[torch.Tensor, np.ndarray],
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Dict]:
        """
        Преобразует сырые выходы модели в структурированный формат

        Args:
            raw_outputs: Тензор или numpy array формы [batch_size, 20] с выходами модели
            symbols: Список символов для каждого элемента в батче (опционально)

        Returns:
            Dict с предсказаниями по символам или по индексам
        """
        # Переводим в numpy для удобства
        if isinstance(raw_outputs, torch.Tensor):
            outputs = raw_outputs.detach().cpu().numpy()
        else:
            outputs = raw_outputs

        # Убеждаемся что это 2D массив
        if len(outputs.shape) == 1:
            outputs = outputs.reshape(1, -1)
        elif len(outputs.shape) == 3:
            # Если получили 3D массив [batch, seq, features], берем последнюю точку
            outputs = outputs[:, -1, :]

        batch_size = outputs.shape[0]

        # Если символы не предоставлены, используем индексы
        if symbols is None:
            symbols = [f"batch_{i}" for i in range(batch_size)]

        # Группируем по символам
        predictions_by_symbol = {}

        for i, symbol in enumerate(symbols):
            symbol_outputs = outputs[i] if batch_size > 1 else outputs[0]
            predictions_by_symbol[symbol] = self._create_signal_format(symbol_outputs)

        return predictions_by_symbol

    def _create_signal_format(self, outputs: np.ndarray) -> Dict:
        """
        Создает структуру предсказаний для торговой системы
        """
        # Извлекаем компоненты
        future_returns = outputs[self.output_mapping["future_return"]]
        directions = outputs[self.output_mapping["direction"]]
        volatilities = outputs[self.output_mapping["volatility"]]
        volume_changes = outputs[self.output_mapping["volume_change"]]
        price_ranges = outputs[self.output_mapping["price_range"]]

        # Интерпретируем направления (0=DOWN, 1=FLAT, 2=UP в модели)
        # Конвертируем в вероятности
        direction_probs = self._softmax_directions(directions)

        # Определяем основное направление
        primary_direction = self._determine_primary_direction(directions)

        # Рассчитываем вероятности прибыли для LONG и SHORT
        long_profit_probs = []
        short_profit_probs = []

        for i, tf in enumerate(self.timeframes):
            # Вероятность прибыли для LONG = вероятность UP
            long_prob = direction_probs[i][2]  # UP
            short_prob = direction_probs[i][0]  # DOWN

            long_profit_probs.append(long_prob)
            short_profit_probs.append(short_prob)

        # Средние значения
        avg_long_prob = np.mean(long_profit_probs)
        avg_short_prob = np.mean(short_profit_probs)

        # Определяем тип сигнала
        if avg_long_prob > 0.6 and avg_long_prob > avg_short_prob:
            signal_type = "LONG"
            confidence = avg_long_prob
        elif avg_short_prob > 0.6 and avg_short_prob > avg_long_prob:
            signal_type = "SHORT"
            confidence = avg_short_prob
        else:
            signal_type = "NEUTRAL"
            confidence = max(avg_long_prob, avg_short_prob)

        # Рассчитываем силу сигнала
        signal_strength = self._calculate_signal_strength(
            directions, future_returns, volatilities
        )

        # Риск метрики
        risk_metrics = self._calculate_risk_metrics(
            future_returns, volatilities, price_ranges
        )

        return {
            "signal_type": signal_type,
            "confidence": float(confidence),
            "signal_strength": float(signal_strength),
            "risk_level": risk_metrics["risk_level"],
            # Детальные предсказания
            "predictions": {
                "future_returns": {
                    tf: float(ret) for tf, ret in zip(self.timeframes, future_returns)
                },
                "directions": {
                    tf: int(dir) for tf, dir in zip(self.timeframes, directions)
                },
                "direction_probabilities": {
                    tf: {
                        "down": float(probs[0]),
                        "flat": float(probs[1]),
                        "up": float(probs[2]),
                    }
                    for tf, probs in zip(self.timeframes, direction_probs)
                },
                "volatilities": {
                    tf: float(vol) for tf, vol in zip(self.timeframes, volatilities)
                },
                "volume_changes": {
                    tf: float(vc) for tf, vc in zip(self.timeframes, volume_changes)
                },
                "price_ranges": {
                    tf: float(pr) for tf, pr in zip(self.timeframes, price_ranges)
                },
            },
            # Вероятности прибыли
            "profit_probabilities": {
                "long": {
                    tf: float(prob)
                    for tf, prob in zip(self.timeframes, long_profit_probs)
                },
                "short": {
                    tf: float(prob)
                    for tf, prob in zip(self.timeframes, short_profit_probs)
                },
            },
            # Риск метрики
            "risk_metrics": risk_metrics,
            # Временная метка
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _softmax_directions(self, directions: np.ndarray) -> np.ndarray:
        """
        Применяет softmax для преобразования направлений в вероятности
        Предполагаем что модель выдает logits для 3 классов
        """
        # Если directions уже нормализованы (0-2), создаем one-hot
        probs = []
        for dir_value in directions:
            # Создаем псевдо-вероятности на основе предсказанного класса
            prob = np.zeros(3)
            if 0 <= dir_value <= 2:
                prob[int(dir_value)] = (
                    0.8  # Высокая вероятность для предсказанного класса
                )
                prob[(int(dir_value) + 1) % 3] = 0.15  # Средняя для соседнего
                prob[(int(dir_value) + 2) % 3] = 0.05  # Низкая для противоположного
            else:
                # Если значение вне диапазона, равномерное распределение
                prob[:] = 1 / 3
            probs.append(prob)

        return np.array(probs)

    def _determine_primary_direction(self, directions: np.ndarray) -> str:
        """
        Определяет основное направление на основе всех временных горизонтов
        """
        # Подсчитываем голоса
        votes = np.bincount(directions.astype(int).clip(0, 2), minlength=3)

        # 0=DOWN, 1=FLAT, 2=UP
        if votes[2] > votes[0] and votes[2] >= votes[1]:
            return "UP"
        elif votes[0] > votes[2] and votes[0] >= votes[1]:
            return "DOWN"
        else:
            return "FLAT"

    def _calculate_signal_strength(
        self, directions: np.ndarray, returns: np.ndarray, volatilities: np.ndarray
    ) -> float:
        """
        Рассчитывает силу сигнала на основе согласованности предсказаний
        """
        # Согласованность направлений
        direction_agreement = 1.0 - (np.std(directions) / 2.0)  # Нормализуем к [0, 1]

        # Сила ожидаемого движения
        avg_return = np.mean(np.abs(returns))
        return_strength = min(avg_return * 10, 1.0)  # Предполагаем returns в долях

        # Учитываем волатильность (низкая волатильность = более надежный сигнал)
        avg_volatility = np.mean(volatilities)
        volatility_factor = 1.0 - min(avg_volatility, 1.0)

        # Комбинируем факторы
        strength = (
            0.4 * direction_agreement + 0.4 * return_strength + 0.2 * volatility_factor
        )

        return np.clip(strength, 0.0, 1.0)

    def _calculate_risk_metrics(
        self, returns: np.ndarray, volatilities: np.ndarray, price_ranges: np.ndarray
    ) -> Dict[str, float]:
        """
        Рассчитывает метрики риска
        """
        # Средняя волатильность
        avg_volatility = np.mean(volatilities)

        # Максимальный потенциальный drawdown
        max_negative_return = np.min(returns)

        # Средний размах цен
        avg_price_range = np.mean(price_ranges)

        # Определяем уровень риска
        if avg_volatility > 0.03 or max_negative_return < -0.02:
            risk_level = "HIGH"
            risk_score = 0.8
        elif avg_volatility > 0.02 or max_negative_return < -0.01:
            risk_level = "MEDIUM"
            risk_score = 0.5
        else:
            risk_level = "LOW"
            risk_score = 0.2

        return {
            "risk_level": risk_level,
            "risk_score": float(risk_score),
            "avg_volatility": float(avg_volatility),
            "max_drawdown": float(abs(max_negative_return)),
            "avg_price_range": float(avg_price_range),
        }

    def calculate_trading_levels(
        self,
        current_price: float,
        predictions: Dict[str, Any],
        risk_tolerance: float = 0.02,
    ) -> Dict[str, float]:
        """
        Рассчитывает уровни stop loss и take profit

        Args:
            current_price: Текущая цена
            predictions: Предсказания модели
            risk_tolerance: Максимальный риск (по умолчанию 2%)

        Returns:
            Словарь с уровнями SL и TP
        """
        risk_metrics = predictions.get("risk_metrics", {})
        future_returns = predictions.get("predictions", {}).get("future_returns", {})
        signal_type = predictions.get("signal_type", "NEUTRAL")

        # Базовый риск
        base_risk = min(risk_tolerance, risk_metrics.get("avg_volatility", 0.02))

        # Take profit на основе ожидаемых returns
        expected_return = np.mean(
            [future_returns.get("1h", 0), future_returns.get("4h", 0)]
        )

        # Risk/reward ratio
        risk_reward_ratio = 2.0 if risk_metrics.get("risk_level") == "LOW" else 1.5

        if signal_type == "LONG":
            stop_loss = current_price * (1 - base_risk)
            take_profit = current_price * (1 + base_risk * risk_reward_ratio)
        elif signal_type == "SHORT":
            stop_loss = current_price * (1 + base_risk)
            take_profit = current_price * (1 - base_risk * risk_reward_ratio)
        else:
            # Нейтральный сигнал
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.02

        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_percentage": base_risk * 100,
            "expected_profit_percentage": base_risk * risk_reward_ratio * 100,
        }
