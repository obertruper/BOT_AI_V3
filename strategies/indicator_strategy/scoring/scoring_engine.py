"""
Главный движок скоринга для indicator_strategy
Реализует матрицу весов и расчет общего скора на основе индикаторов
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from .dynamic_weights import DynamicWeightCalculator
from .weight_manager import WeightManager

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """Результат расчета скоринга"""

    total_score: float  # Общий скор от -100 до +100
    category_scores: dict[str, float]  # Скоры по категориям
    weighted_scores: dict[str, float]  # Взвешенные скоры
    active_weights: dict[str, float]  # Использованные веса
    confidence: float  # Уверенность в сигнале
    details: dict[str, Any]  # Дополнительные детали


class ScoringEngine:
    """
    Движок скоринга для расчета силы торговых сигналов

    Реализует матрицу весов из документации:
    - Трендовые индикаторы: 30%
    - Импульсные индикаторы: 25%
    - Объёмные индикаторы: 25%
    - Индикаторы волатильности: 20%
    """

    def __init__(
        self,
        base_weights: dict[str, float] | None = None,
        regime_multipliers: dict[str, dict[str, float]] | None = None,
        use_dynamic_weights: bool = True,
    ):
        """
        Инициализация движка скоринга

        Args:
            base_weights: Базовые веса категорий
            regime_multipliers: Множители для разных режимов рынка
            use_dynamic_weights: Использовать ли динамические веса
        """
        # Инициализация менеджера весов
        self.weight_manager = WeightManager(base_weights)

        # Инициализация калькулятора динамических весов
        self.dynamic_calculator = (
            DynamicWeightCalculator(regime_multipliers) if use_dynamic_weights else None
        )

        self.use_dynamic_weights = use_dynamic_weights

        # Статистика
        self._calculations_count = 0
        self._avg_score = 0.0

    def calculate_score(
        self, indicators: dict[str, dict[str, Any]], market_regime: str | None = None
    ) -> ScoringResult:
        """
        Расчет общего скора на основе индикаторов

        Args:
            indicators: Словарь с результатами индикаторов по категориям
            market_regime: Текущий режим рынка (для динамических весов)

        Returns:
            Результат скоринга
        """
        if not indicators:
            logger.warning("No indicators provided for scoring")
            return ScoringResult(
                total_score=0.0,
                category_scores={},
                weighted_scores={},
                active_weights=self.weight_manager.get_weights(),
                confidence=0.0,
                details={},
            )

        # Получение активных весов
        if self.use_dynamic_weights and market_regime:
            active_weights = self.dynamic_calculator.calculate_weights(
                self.weight_manager.get_weights(), market_regime
            )
        else:
            active_weights = self.weight_manager.get_weights()

        # Расчет скоров по категориям
        category_scores = self._calculate_category_scores(indicators)

        # Расчет взвешенных скоров
        weighted_scores = {}
        total_score = 0.0
        total_weight = 0.0

        for category, weight in active_weights.items():
            if category in category_scores:
                score = category_scores[category]
                weighted_score = score * weight
                weighted_scores[category] = weighted_score
                total_score += weighted_score
                total_weight += weight

        # Нормализация если веса не равны 1.0
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            total_score = total_score / total_weight

        # Ограничение диапазона
        total_score = max(min(total_score, 100), -100)

        # Расчет уверенности
        confidence = self._calculate_confidence(category_scores, indicators)

        # Обновление статистики
        self._update_statistics(total_score)

        # Создание результата
        result = ScoringResult(
            total_score=total_score,
            category_scores=category_scores,
            weighted_scores=weighted_scores,
            active_weights=active_weights,
            confidence=confidence,
            details={
                "market_regime": market_regime,
                "indicators_count": self._count_active_indicators(indicators),
                "agreement_level": self._calculate_agreement_level(category_scores),
                "signal_quality": self._assess_signal_quality(total_score, confidence),
            },
        )

        logger.debug(f"Scoring result: score={total_score:.2f}, confidence={confidence:.2f}")

        return result

    def _calculate_category_scores(self, indicators: dict[str, dict[str, Any]]) -> dict[str, float]:
        """
        Расчет скоров для каждой категории индикаторов

        Returns:
            Словарь со скорами категорий
        """
        category_scores = {}

        for category, category_indicators in indicators.items():
            if not isinstance(category_indicators, dict):
                continue

            scores = []
            strengths = []

            for indicator_name, indicator_data in category_indicators.items():
                if not isinstance(indicator_data, dict):
                    continue

                # Извлечение сигнала и силы
                if "signal" in indicator_data:
                    signal = indicator_data["signal"]
                    strength = indicator_data.get("strength", 50)

                    # Валидация
                    if -1 <= signal <= 1 and 0 <= strength <= 100:
                        score = signal * strength
                        scores.append(score)
                        strengths.append(strength)
                    else:
                        logger.warning(
                            f"Invalid signal/strength for {category}.{indicator_name}: "
                            f"signal={signal}, strength={strength}"
                        )

            # Расчет среднего скора для категории
            if scores:
                # Взвешенное среднее по силе сигналов
                if sum(strengths) > 0:
                    category_score = sum(
                        s * w for s, w in zip(scores, strengths, strict=False)
                    ) / sum(strengths)
                else:
                    category_score = np.mean(scores)

                category_scores[category] = category_score

        return category_scores

    def _calculate_confidence(
        self, category_scores: dict[str, float], indicators: dict[str, Any]
    ) -> float:
        """
        Расчет уверенности в сигнале

        Факторы:
        - Количество активных индикаторов
        - Согласованность сигналов
        - Сила отдельных сигналов

        Returns:
            Уверенность от 0 до 100
        """
        confidence_factors = []

        # 1. Фактор количества индикаторов
        total_indicators = self._count_active_indicators(indicators)
        min_indicators = 3
        max_indicators = 12

        if total_indicators >= max_indicators:
            indicators_factor = 100
        elif total_indicators >= min_indicators:
            indicators_factor = (
                50 + (total_indicators - min_indicators) / (max_indicators - min_indicators) * 50
            )
        else:
            indicators_factor = total_indicators / min_indicators * 50

        confidence_factors.append(indicators_factor)

        # 2. Фактор согласованности
        if category_scores:
            # Проверяем, все ли категории дают сигналы в одном направлении
            positive_categories = sum(1 for score in category_scores.values() if score > 10)
            negative_categories = sum(1 for score in category_scores.values() if score < -10)
            total_categories = len(category_scores)

            if total_categories > 0:
                agreement_ratio = max(positive_categories, negative_categories) / total_categories
                agreement_factor = agreement_ratio * 100
                confidence_factors.append(agreement_factor)

        # 3. Фактор силы сигналов
        if category_scores:
            avg_strength = np.mean([abs(score) for score in category_scores.values()])
            strength_factor = min(avg_strength, 100)
            confidence_factors.append(strength_factor)

        # Итоговая уверенность
        if confidence_factors:
            confidence = np.mean(confidence_factors)
        else:
            confidence = 0.0

        return min(max(confidence, 0), 100)

    def _count_active_indicators(self, indicators: dict[str, dict[str, Any]]) -> int:
        """Подсчет количества активных индикаторов"""
        count = 0

        for category_indicators in indicators.values():
            if isinstance(category_indicators, dict):
                for indicator_data in category_indicators.values():
                    if isinstance(indicator_data, dict) and "signal" in indicator_data:
                        count += 1

        return count

    def _calculate_agreement_level(self, category_scores: dict[str, float]) -> str:
        """Определение уровня согласованности сигналов"""
        if not category_scores:
            return "none"

        positive = sum(1 for score in category_scores.values() if score > 10)
        negative = sum(1 for score in category_scores.values() if score < -10)
        total = len(category_scores)

        if positive == total or negative == total:
            return "unanimous"
        elif positive >= total * 0.75 or negative >= total * 0.75:
            return "strong"
        elif positive >= total * 0.5 or negative >= total * 0.5:
            return "moderate"
        else:
            return "weak"

    def _assess_signal_quality(self, score: float, confidence: float) -> str:
        """Оценка качества сигнала"""
        abs_score = abs(score)

        if abs_score >= 70 and confidence >= 70:
            return "excellent"
        elif abs_score >= 50 and confidence >= 50:
            return "good"
        elif abs_score >= 30 and confidence >= 30:
            return "fair"
        else:
            return "poor"

    def _update_statistics(self, score: float) -> None:
        """Обновление статистики"""
        self._calculations_count += 1

        # Скользящее среднее
        alpha = 0.1  # Коэффициент сглаживания
        self._avg_score = (1 - alpha) * self._avg_score + alpha * score

    def get_statistics(self) -> dict[str, Any]:
        """Получение статистики работы движка"""
        return {
            "calculations_count": self._calculations_count,
            "average_score": round(self._avg_score, 2),
            "current_weights": self.weight_manager.get_weights(),
            "dynamic_weights_enabled": self.use_dynamic_weights,
        }

    def reset_statistics(self) -> None:
        """Сброс статистики"""
        self._calculations_count = 0
        self._avg_score = 0.0
        logger.info("Scoring engine statistics reset")
