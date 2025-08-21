#!/usr/bin/env python3
"""
Signal Quality Analyzer для ML торговых сигналов
Анализирует качество сигналов на основе согласованности таймфреймов и уверенности модели
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np

from core.logger import setup_logger

logger = setup_logger(__name__)


class FilterStrategy(Enum):
    """Стратегии фильтрации сигналов"""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class QualityMetrics:
    """Метрики качества сигнала"""

    quality_score: float
    agreement_score: float
    confidence_score: float
    return_score: float
    risk_score: float


@dataclass
class FilterResult:
    """Результат фильтрации сигнала"""

    passed: bool
    signal_type: str
    strategy_used: FilterStrategy
    quality_metrics: QualityMetrics
    rejection_reasons: list[str]


class SignalQualityAnalyzer:
    """
    Анализатор качества ML сигналов
    Оценивает согласованность таймфреймов и уверенность предсказаний
    """

    def __init__(self, config: dict = None):
        """
        Инициализация анализатора

        Args:
            config: Конфигурация из ml_config.yaml
        """
        self.config = config or {}

        # Извлекаем конфигурацию фильтрации
        filter_config = self.config.get("signal_filtering", {})

        # Устанавливаем активную стратегию
        strategy_name = filter_config.get("strategy", "moderate")
        self.active_strategy = FilterStrategy(strategy_name)

        # Веса таймфреймов (из конфигурации или defaults)
        timeframe_weights_list = filter_config.get("timeframe_weights", [0.25, 0.25, 0.35, 0.15])
        self.timeframe_weights = np.array(timeframe_weights_list)

        # Индекс основного таймфрейма (обычно 4h = индекс 2)
        self.main_timeframe_index = filter_config.get("main_timeframe_index", 2)

        # Веса для расчета качества
        quality_weights = filter_config.get("quality_weights", {})
        self.quality_weights = {
            "agreement": quality_weights.get("agreement", 0.35),
            "confidence": quality_weights.get("confidence", 0.30),
            "return_expectation": quality_weights.get("return_expectation", 0.20),
            "risk_adjustment": quality_weights.get("risk_adjustment", 0.15),
        }

        # Параметры стратегий - ОПТИМИЗИРОВАНО для реальной торговли
        self.strategy_params = {
            FilterStrategy.CONSERVATIVE: filter_config.get(
                "conservative",
                {
                    "min_timeframe_agreement": 2,  # Снижено с 3
                    "required_confidence_per_timeframe": 0.50,  # Снижено с 0.65
                    "main_timeframe_required_confidence": 0.55,  # Снижено с 0.70
                    "min_expected_return_pct": 0.002,  # Снижено с 0.008
                    "min_signal_strength": 0.45,  # Снижено с 0.7
                    "max_risk_level": "HIGH",  # Изменено с MEDIUM
                    "min_quality_score": 0.40,  # Снижено с 0.75
                },
            ),
            FilterStrategy.MODERATE: filter_config.get(
                "moderate",
                {
                    "min_timeframe_agreement": 3,  # ОПТИМАЛЬНО: 3 из 4 таймфреймов (меньше ложных)
                    "required_confidence_per_timeframe": 0.38,  # РЕАЛИСТИЧНО: чуть выше среднего
                    "main_timeframe_required_confidence": 0.40,  # РЕАЛИСТИЧНО: 4h важен
                    "alternative_main_plus_one": True,
                    "alternative_confidence_threshold": 0.42,  # РЕАЛИСТИЧНО: альтернативный порог
                    "min_expected_return_pct": 0.0010,  # РЕАЛИСТИЧНО: 0.10% достаточно для крипто
                    "min_signal_strength": 0.40,  # УМЕРЕННО: фильтруем только очень слабые
                    "max_risk_level": "MEDIUM",  # УМЕРЕННО: допускаем средний риск
                    "min_quality_score": 0.45,  # УМЕРЕННО: баланс качества и частоты
                },
            ),
            FilterStrategy.AGGRESSIVE: filter_config.get(
                "aggressive",
                {
                    "min_timeframe_agreement": 1,
                    "required_confidence_per_timeframe": 0.40,  # Повышено с 0.30
                    "main_timeframe_required_confidence": 0.42,  # Повышено с 0.35
                    "min_expected_return_pct": 0.0008,  # Повышено с 0.0005 - минимум 0.08%
                    "min_signal_strength": 0.32,  # Повышено с 0.25
                    "max_risk_level": "HIGH",
                    "min_quality_score": 0.35,  # Повышено с 0.25
                },
            ),
        }

        # Пороги для оценки качества (legacy для совместимости)
        self.quality_thresholds = {"excellent": 0.75, "good": 0.60, "moderate": 0.45, "poor": 0.30}

        # Статистика для мониторинга
        self.stats = {
            "total_analyzed": 0,
            "high_quality": 0,
            "medium_quality": 0,
            "low_quality": 0,
            "rejected": 0,
        }

        # Статистика по стратегиям
        self.strategy_stats = {
            strategy: {
                "analyzed": 0,
                "passed": 0,
                "rejected": 0,
                "avg_quality": 0.0,
                "rejection_reasons": {},
            }
            for strategy in FilterStrategy
        }

        logger.info(
            f"SignalQualityAnalyzer инициализирован с стратегией: {self.active_strategy.value}"
        )

    def analyze_signal_quality(
        self,
        directions: np.ndarray,
        direction_probs: list[np.ndarray],
        future_returns: np.ndarray,
        risk_metrics: np.ndarray,
        weighted_direction: float,
    ) -> FilterResult:
        """
        Анализирует качество сигнала с учетом активной стратегии фильтрации.

        Args:
            directions: Массив направлений [15m, 1h, 4h, 12h]
            direction_probs: Список вероятностей для каждого таймфрейма
            future_returns: Предсказанные доходности
            risk_metrics: Метрики риска
            weighted_direction: Взвешенное направление

        Returns:
            FilterResult с результатом анализа
        """
        # Обновляем статистику
        self.strategy_stats[self.active_strategy]["analyzed"] += 1
        self.stats["total_analyzed"] += 1

        # Получаем параметры активной стратегии
        params = self.strategy_params[self.active_strategy]

        # Рассчитываем метрики качества
        quality_metrics = self._calculate_quality_metrics(
            directions, direction_probs, future_returns, risk_metrics
        )

        # Определяем доминирующий сигнал
        signal_type = self._determine_signal_type(directions, weighted_direction)

        # Проверяем критерии фильтрации
        rejection_reasons = []
        passed = self._check_filtering_criteria(
            directions,
            direction_probs,
            future_returns,
            risk_metrics,
            quality_metrics,
            params,
            rejection_reasons,
        )

        # Обновляем статистику
        if passed:
            self.strategy_stats[self.active_strategy]["passed"] += 1
            # Обновляем среднее качество
            stats = self.strategy_stats[self.active_strategy]
            stats["avg_quality"] = (
                (stats["avg_quality"] * (stats["passed"] - 1)) + quality_metrics.quality_score
            ) / stats["passed"]
        else:
            self.strategy_stats[self.active_strategy]["rejected"] += 1
            # Подсчитываем причины отклонения
            for reason in rejection_reasons:
                reason_stats = self.strategy_stats[self.active_strategy]["rejection_reasons"]
                reason_stats[reason] = reason_stats.get(reason, 0) + 1

        # Создаем результат
        result = FilterResult(
            passed=passed,
            signal_type=signal_type,
            strategy_used=self.active_strategy,
            quality_metrics=quality_metrics,
            rejection_reasons=rejection_reasons,
        )

        # Логирование результата
        status = "✅ ПРИНЯТ" if passed else "❌ ОТКЛОНЕН"
        logger.info(
            f"{status} сигнал {signal_type} (стратегия: {self.active_strategy.value}, качество: {quality_metrics.quality_score:.3f})"
        )

        if not passed and rejection_reasons:
            logger.debug(f"Причины отклонения: {'; '.join(rejection_reasons)}")

        return result

    def _calculate_quality_metrics(
        self,
        directions: np.ndarray,
        direction_probs: list[np.ndarray],
        future_returns: np.ndarray,
        risk_metrics: np.ndarray,
    ) -> QualityMetrics:
        """Рассчитывает все метрики качества сигнала"""

        # 1. Agreement Score - согласованность таймфреймов
        agreement_score = self._calculate_agreement_score_weighted(directions)

        # 2. Confidence Score - уверенность модели
        confidence_score = self._calculate_confidence_score_enhanced(direction_probs)

        # 3. Return Score - ожидаемая доходность
        return_score = self._calculate_return_score_enhanced(future_returns)

        # 4. Risk Score - оценка риска
        risk_score = self._calculate_risk_score(risk_metrics)

        # 5. Overall Quality Score
        quality_score = (
            self.quality_weights["agreement"] * agreement_score
            + self.quality_weights["confidence"] * confidence_score
            + self.quality_weights["return_expectation"] * return_score
            + self.quality_weights["risk_adjustment"] * (1.0 - risk_score)  # Инвертируем риск
        )

        return QualityMetrics(
            quality_score=quality_score,
            agreement_score=agreement_score,
            confidence_score=confidence_score,
            return_score=return_score,
            risk_score=risk_score,
        )

    def _calculate_agreement_score_weighted(self, directions: np.ndarray) -> float:
        """Рассчитывает взвешенную согласованность таймфреймов"""
        # Находим доминирующее направление
        unique, counts = np.unique(directions, return_counts=True)
        dominant_direction = unique[np.argmax(counts)]

        # Создаем маску согласных таймфреймов
        agreement_mask = (directions == dominant_direction).astype(float)

        # Рассчитываем взвешенный score
        weighted_score = np.sum(agreement_mask * self.timeframe_weights)

        return float(weighted_score)

    def _calculate_confidence_score_enhanced(self, direction_probs: list[np.ndarray]) -> float:
        """Улучшенный расчет уверенности с учетом энтропии"""
        confidences = np.array([np.max(probs) for probs in direction_probs])

        # Взвешенная средняя уверенность
        weighted_confidence = np.sum(confidences * self.timeframe_weights)

        # Энтропийная составляющая
        entropies = []
        for probs in direction_probs:
            probs_safe = np.clip(probs, 1e-10, 1.0)
            entropy = -np.sum(probs_safe * np.log(probs_safe))
            entropies.append(entropy)

        avg_entropy = np.mean(entropies)
        max_entropy = np.log(3)  # Для 3 классов
        entropy_score = 1.0 - (avg_entropy / max_entropy)

        # Комбинированный score
        final_score = 0.7 * weighted_confidence + 0.3 * entropy_score

        return float(final_score)

    def _calculate_return_score_enhanced(self, future_returns: np.ndarray) -> float:
        """Улучшенный расчет score доходности"""
        # Взвешенная ожидаемая доходность
        weighted_return = np.sum(np.abs(future_returns) * self.timeframe_weights)

        # Нормализация относительно хорошего сигнала (1.5%)
        normalized_score = min(weighted_return / 0.015, 1.0)

        # Бонус за консистентность знаков
        non_zero_returns = future_returns[np.abs(future_returns) > 0.001]
        if len(non_zero_returns) > 0:
            sign_consistency = len(np.unique(np.sign(non_zero_returns))) == 1
            consistency_bonus = 0.1 if sign_consistency else 0
        else:
            consistency_bonus = 0

        final_score = min(normalized_score + consistency_bonus, 1.0)

        return float(final_score)

    def _calculate_risk_score(self, risk_metrics: np.ndarray) -> float:
        """Рассчитывает оценку риска (0 = низкий риск, 1 = высокий риск)"""
        if len(risk_metrics) == 0:
            return 0.5

        # Средний риск с учетом весов
        if len(risk_metrics) >= len(self.timeframe_weights):
            weighted_risk = np.sum(
                risk_metrics[: len(self.timeframe_weights)] * self.timeframe_weights
            )
        else:
            weighted_risk = np.mean(risk_metrics)

        # Нормализуем в диапазон [0, 1]
        risk_score = np.clip(weighted_risk, 0.0, 1.0)

        return float(risk_score)

    def _determine_signal_type(self, directions: np.ndarray, weighted_direction: float) -> str:
        """Определяет тип сигнала на основе направлений"""
        # Подсчитываем количество каждого направления
        unique, counts = np.unique(directions, return_counts=True)
        direction_counts = dict(zip(unique, counts, strict=False))

        # Маппинг направлений
        direction_map = {0: "LONG", 1: "SHORT", 2: "NEUTRAL"}

        # Определяем доминирующее направление
        dominant_idx = np.argmax(counts)
        dominant_direction = unique[dominant_idx]
        dominant_count = counts[dominant_idx]

        # Если есть явное большинство
        if dominant_count >= 3:
            return direction_map[dominant_direction]

        # Если нет явного большинства, используем взвешенное направление
        if weighted_direction < 0.8:  # Ближе к LONG (0)
            return "LONG"
        elif weighted_direction > 1.2:  # Ближе к SHORT (1)
            return "SHORT"
        else:  # Между LONG и SHORT или близко к NEUTRAL (2)
            return "NEUTRAL"

    def _check_filtering_criteria(
        self,
        directions: np.ndarray,
        direction_probs: list[np.ndarray],
        future_returns: np.ndarray,
        risk_metrics: np.ndarray,
        quality_metrics: QualityMetrics,
        params: dict,
        rejection_reasons: list[str],
    ) -> bool:
        """Проверяет все критерии фильтрации для активной стратегии"""

        passed = True

        # 1. Проверка согласованности таймфреймов
        unique, counts = np.unique(directions, return_counts=True)
        max_agreement = np.max(counts)

        if max_agreement < params["min_timeframe_agreement"]:
            rejection_reasons.append(
                f"Недостаточная согласованность ТФ: {max_agreement} < {params['min_timeframe_agreement']}"
            )
            passed = False

        # 2. Проверка уверенности
        confidences = np.array([np.max(probs) for probs in direction_probs])

        # Общая проверка уверенности
        min_conf_threshold = params["required_confidence_per_timeframe"]
        low_confidence_count = np.sum(confidences < min_conf_threshold)

        # ОПТИМИЗИРОВАНО: Разрешаем больше ТФ с низкой уверенностью
        max_low_confidence_allowed = 3  # Увеличено с 2 до 3
        if low_confidence_count > max_low_confidence_allowed:
            rejection_reasons.append(
                f"Слишком много ТФ с низкой уверенностью: {low_confidence_count} > {max_low_confidence_allowed}"
            )
            passed = False

        # Проверка основного таймфрейма
        main_tf_confidence = confidences[self.main_timeframe_index]
        main_tf_threshold = params["main_timeframe_required_confidence"]

        if main_tf_confidence < main_tf_threshold:
            # Проверяем альтернативный критерий для moderate стратегии
            if self.active_strategy == FilterStrategy.MODERATE and params.get(
                "alternative_main_plus_one", False
            ):

                alt_threshold = params.get("alternative_confidence_threshold", 0.75)
                high_conf_count = np.sum(confidences >= alt_threshold)

                if high_conf_count < 2:
                    rejection_reasons.append(
                        f"Основной ТФ: {main_tf_confidence:.3f} < {main_tf_threshold:.3f}, альтернатива не выполнена"
                    )
                    passed = False
            else:
                rejection_reasons.append(
                    f"Основной ТФ: {main_tf_confidence:.3f} < {main_tf_threshold:.3f}"
                )
                passed = False

        # 3. Проверка ожидаемой доходности
        max_return = np.max(np.abs(future_returns))
        min_return_threshold = params["min_expected_return_pct"]

        if max_return < min_return_threshold:
            rejection_reasons.append(
                f"Низкая ожидаемая доходность: {max_return:.4f} < {min_return_threshold:.4f}"
            )
            passed = False

        # 4. Проверка общего качества
        if quality_metrics.quality_score < params["min_quality_score"]:
            rejection_reasons.append(
                f"Низкое качество: {quality_metrics.quality_score:.3f} < {params['min_quality_score']:.3f}"
            )
            passed = False

        # 5. Проверка силы сигнала
        signal_strength = (
            0.6 * quality_metrics.quality_score + 0.4 * quality_metrics.confidence_score
        )
        if signal_strength < params["min_signal_strength"]:
            rejection_reasons.append(
                f"Слабый сигнал: {signal_strength:.3f} < {params['min_signal_strength']:.3f}"
            )
            passed = False

        # 6. Проверка уровня риска
        risk_level = (
            "LOW"
            if quality_metrics.risk_score < 0.3
            else "MEDIUM" if quality_metrics.risk_score < 0.7 else "HIGH"
        )
        max_risk_level = params["max_risk_level"]

        risk_hierarchy = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        if risk_hierarchy[risk_level] > risk_hierarchy[max_risk_level]:
            rejection_reasons.append(f"Высокий риск: {risk_level} > {max_risk_level}")
            passed = False

        return passed

    def switch_strategy(self, strategy: str) -> bool:
        """Переключает активную стратегию фильтрации"""
        try:
            new_strategy = FilterStrategy(strategy)
            self.active_strategy = new_strategy
            logger.info(f"Стратегия переключена на: {strategy}")
            return True
        except ValueError:
            logger.error(f"Неизвестная стратегия: {strategy}")
            return False

    def get_strategy_statistics(self) -> dict:
        """Возвращает статистику по всем стратегиям"""
        stats = {}

        for strategy, data in self.strategy_stats.items():
            strategy_name = strategy.value
            analyzed = data["analyzed"]

            if analyzed > 0:
                stats[f"{strategy_name}_analyzed"] = analyzed
                stats[f"{strategy_name}_passed"] = data["passed"]
                stats[f"{strategy_name}_rejected"] = data["rejected"]
                stats[f"{strategy_name}_pass_rate"] = (data["passed"] / analyzed) * 100
                stats[f"{strategy_name}_avg_quality"] = data["avg_quality"]
                stats[f"{strategy_name}_top_rejection_reasons"] = dict(
                    sorted(data["rejection_reasons"].items(), key=lambda x: x[1], reverse=True)[:3]
                )
            else:
                stats[f"{strategy_name}_analyzed"] = 0

        stats["active_strategy"] = self.active_strategy.value
        return stats

    def analyze_signal(
        self,
        directions: np.ndarray,
        confidences: np.ndarray,
        returns: np.ndarray,
        direction_probs: list[np.ndarray],
    ) -> dict:
        """
        Комплексный анализ качества сигнала

        Args:
            directions: Предсказанные направления [15m, 1h, 4h, 12h]
            confidences: Уверенность для каждого таймфрейма
            returns: Предсказанные доходности
            direction_probs: Вероятности для каждого класса

        Returns:
            Dict с метриками качества и рекомендацией
        """
        self.stats["total_analyzed"] += 1

        # 1. Agreement Score - согласованность таймфреймов
        agreement_score = self._calculate_agreement_score(directions)

        # 2. Confidence Score - уверенность модели
        confidence_score = self._calculate_confidence_score(confidences, direction_probs)

        # 3. Return Score - ожидаемая доходность
        return_score = self._calculate_return_score(returns)

        # 4. Directional Consistency - согласованность направления с returns
        consistency_score = self._calculate_consistency_score(directions, returns)

        # 5. Overall Quality Score
        quality_score = self._calculate_overall_quality(
            agreement_score, confidence_score, return_score, consistency_score
        )

        # Определяем качество сигнала
        quality_level = self._determine_quality_level(quality_score)

        # Обновляем статистику
        self._update_statistics(quality_level)

        # Рекомендация по сигналу
        recommendation = self._generate_recommendation(
            quality_score, agreement_score, confidence_score, directions
        )

        result = {
            "quality_score": quality_score,
            "quality_level": quality_level,
            "agreement_score": agreement_score,
            "confidence_score": confidence_score,
            "return_score": return_score,
            "consistency_score": consistency_score,
            "recommendation": recommendation,
            "details": {
                "timeframe_agreement": self._get_timeframe_agreement_details(directions),
                "confidence_distribution": self._get_confidence_distribution(confidences),
                "expected_return": float(np.mean(returns)),
                "signal_strength": self._calculate_signal_strength(quality_score, confidence_score),
            },
        }

        logger.info(f"📊 Signal Quality Analysis: {quality_level} (score: {quality_score:.3f})")
        logger.debug(
            f"   Agreement: {agreement_score:.3f}, Confidence: {confidence_score:.3f}, "
            f"Return: {return_score:.3f}, Consistency: {consistency_score:.3f}"
        )

        return result

    def _calculate_agreement_score(self, directions: np.ndarray) -> float:
        """
        Рассчитывает согласованность таймфреймов с учетом весов

        Returns:
            Score от 0 до 1, где 1 = полное согласие
        """
        # Подсчитываем частоту каждого направления
        unique, counts = np.unique(directions, return_counts=True)

        # Находим доминирующее направление
        dominant_direction = unique[np.argmax(counts)]
        dominant_count = np.max(counts)

        # Базовый score на основе количества согласных
        base_score = dominant_count / len(directions)

        # Учитываем веса таймфреймов
        weights = self.timeframe_weights

        # Взвешенный score для согласных таймфреймов
        agreement_mask = (directions == dominant_direction).astype(float)
        weighted_score = np.sum(agreement_mask * weights)

        # Комбинированный score
        final_score = 0.6 * base_score + 0.4 * weighted_score

        return float(final_score)

    def _calculate_confidence_score(
        self, confidences: np.ndarray, direction_probs: list[np.ndarray]
    ) -> float:
        """
        Рассчитывает общую уверенность модели
        """
        # Средняя уверенность
        avg_confidence = np.mean(confidences)

        # Энтропия распределения вероятностей (низкая энтропия = высокая уверенность)
        entropies = []
        for probs in direction_probs:
            # Избегаем log(0)
            probs_safe = np.clip(probs, 1e-10, 1.0)
            entropy = -np.sum(probs_safe * np.log(probs_safe))
            entropies.append(entropy)

        avg_entropy = np.mean(entropies)
        max_entropy = np.log(3)  # Максимальная энтропия для 3 классов

        # Нормализованная энтропия (0 = высокая уверенность, 1 = низкая)
        normalized_entropy = avg_entropy / max_entropy
        entropy_score = 1.0 - normalized_entropy

        # Комбинированный score
        final_score = 0.7 * avg_confidence + 0.3 * entropy_score

        return float(final_score)

    def _calculate_return_score(self, returns: np.ndarray) -> float:
        """
        Оценивает ожидаемую доходность
        """
        # Средний return с учетом весов таймфреймов
        weights = self.timeframe_weights
        weighted_return = np.sum(np.abs(returns) * weights)

        # Нормализация (предполагаем, что 2% return = отличный сигнал)
        normalized_score = min(weighted_return / 0.02, 1.0)

        # Проверяем консистентность знаков returns
        sign_consistency = len(np.unique(np.sign(returns[returns != 0]))) == 1
        consistency_bonus = 0.1 if sign_consistency else 0

        final_score = min(normalized_score + consistency_bonus, 1.0)

        return float(final_score)

    def _calculate_consistency_score(self, directions: np.ndarray, returns: np.ndarray) -> float:
        """
        Проверяет согласованность направлений с предсказанными returns
        """
        consistency_checks = []

        for i, (direction, ret) in enumerate(zip(directions, returns, strict=False)):
            # LONG (0) должен иметь положительный return
            # SHORT (1) должен иметь отрицательный return
            # NEUTRAL (2) должен иметь малый return

            if direction == 0:  # LONG
                consistency_checks.append(ret > 0.001)
            elif direction == 1:  # SHORT
                consistency_checks.append(ret < -0.001)
            else:  # NEUTRAL
                consistency_checks.append(abs(ret) < 0.003)

        consistency_score = np.mean(consistency_checks)
        return float(consistency_score)

    def _calculate_overall_quality(
        self, agreement: float, confidence: float, returns: float, consistency: float
    ) -> float:
        """
        Рассчитывает общее качество сигнала
        """
        # Веса для разных компонентов
        weights = {"agreement": 0.35, "confidence": 0.30, "returns": 0.20, "consistency": 0.15}

        quality_score = (
            weights["agreement"] * agreement
            + weights["confidence"] * confidence
            + weights["returns"] * returns
            + weights["consistency"] * consistency
        )

        return float(quality_score)

    def _determine_quality_level(self, quality_score: float) -> str:
        """
        Определяет уровень качества сигнала
        """
        if quality_score >= self.quality_thresholds["excellent"]:
            return "EXCELLENT"
        elif quality_score >= self.quality_thresholds["good"]:
            return "GOOD"
        elif quality_score >= self.quality_thresholds["moderate"]:
            return "MODERATE"
        elif quality_score >= self.quality_thresholds["poor"]:
            return "POOR"
        else:
            return "REJECT"

    def _generate_recommendation(
        self,
        quality_score: float,
        agreement_score: float,
        confidence_score: float,
        directions: np.ndarray,
    ) -> dict:
        """
        Генерирует рекомендацию по торговле
        """
        # Определяем доминирующее направление
        unique, counts = np.unique(directions, return_counts=True)
        dominant_idx = np.argmax(counts)
        dominant_direction = unique[dominant_idx]
        dominant_count = counts[dominant_idx]

        # Маппинг направлений
        direction_map = {0: "LONG", 1: "SHORT", 2: "NEUTRAL"}
        signal_type = direction_map[dominant_direction]

        # Определяем силу рекомендации
        if quality_score >= 0.75 and dominant_count >= 3:
            action = "STRONG_SIGNAL"
            position_size = 1.0
        elif quality_score >= 0.60 and dominant_count >= 2:
            action = "MODERATE_SIGNAL"
            position_size = 0.7
        elif quality_score >= 0.45:
            action = "WEAK_SIGNAL"
            position_size = 0.4
        else:
            action = "NO_TRADE"
            position_size = 0.0

        return {
            "action": action,
            "signal_type": signal_type,
            "position_size_multiplier": position_size,
            "reasons": self._get_recommendation_reasons(
                quality_score, agreement_score, confidence_score, dominant_count
            ),
        }

    def _get_recommendation_reasons(
        self,
        quality_score: float,
        agreement_score: float,
        confidence_score: float,
        dominant_count: int,
    ) -> list[str]:
        """
        Генерирует список причин для рекомендации
        """
        reasons = []

        if quality_score >= 0.75:
            reasons.append("✅ Высокое качество сигнала")
        elif quality_score < 0.45:
            reasons.append("❌ Низкое качество сигнала")

        if agreement_score >= 0.75:
            reasons.append("✅ Высокая согласованность таймфреймов")
        elif agreement_score < 0.50:
            reasons.append("⚠️ Низкая согласованность таймфреймов")

        if confidence_score >= 0.70:
            reasons.append("✅ Высокая уверенность модели")
        elif confidence_score < 0.50:
            reasons.append("⚠️ Низкая уверенность модели")

        if dominant_count >= 3:
            reasons.append(f"✅ {dominant_count}/4 таймфреймов согласны")
        elif dominant_count < 2:
            reasons.append("❌ Недостаточное согласие таймфреймов")

        return reasons

    def _get_timeframe_agreement_details(self, directions: np.ndarray) -> dict:
        """
        Детали согласованности таймфреймов
        """
        timeframes = ["15m", "1h", "4h", "12h"]
        direction_map = {0: "LONG", 1: "SHORT", 2: "NEUTRAL"}

        details = {}
        for i, (tf, direction) in enumerate(zip(timeframes, directions, strict=False)):
            details[tf] = direction_map[direction]

        # Добавляем статистику
        unique, counts = np.unique(directions, return_counts=True)
        for dir_idx, count in zip(unique, counts, strict=False):
            details[f"{direction_map[dir_idx]}_count"] = int(count)

        return details

    def _get_confidence_distribution(self, confidences: np.ndarray) -> dict:
        """
        Распределение уверенности по таймфреймам
        """
        timeframes = ["15m", "1h", "4h", "12h"]
        distribution = {}

        for tf, conf in zip(timeframes, confidences, strict=False):
            distribution[tf] = float(conf)

        distribution["average"] = float(np.mean(confidences))
        distribution["std"] = float(np.std(confidences))

        return distribution

    def _calculate_signal_strength(self, quality_score: float, confidence_score: float) -> float:
        """
        Рассчитывает силу торгового сигнала
        """
        # Комбинация качества и уверенности
        strength = 0.6 * quality_score + 0.4 * confidence_score

        # Применяем сигмоиду для сглаживания
        strength = 1 / (1 + np.exp(-10 * (strength - 0.5)))

        return float(strength)

    def _update_statistics(self, quality_level: str):
        """
        Обновляет статистику анализатора
        """
        if quality_level in ["EXCELLENT", "GOOD"]:
            self.stats["high_quality"] += 1
        elif quality_level == "MODERATE":
            self.stats["medium_quality"] += 1
        elif quality_level == "POOR":
            self.stats["low_quality"] += 1
        else:
            self.stats["rejected"] += 1

    def get_statistics(self) -> dict:
        """
        Возвращает статистику работы анализатора
        """
        total = self.stats["total_analyzed"]
        if total == 0:
            return self.stats

        stats_with_percentages = self.stats.copy()
        stats_with_percentages["high_quality_pct"] = (self.stats["high_quality"] / total) * 100
        stats_with_percentages["medium_quality_pct"] = (self.stats["medium_quality"] / total) * 100
        stats_with_percentages["low_quality_pct"] = (self.stats["low_quality"] / total) * 100
        stats_with_percentages["rejected_pct"] = (self.stats["rejected"] / total) * 100

        return stats_with_percentages

    def reset_statistics(self):
        """
        Сброс статистики
        """
        self.stats = {
            "total_analyzed": 0,
            "high_quality": 0,
            "medium_quality": 0,
            "low_quality": 0,
            "rejected": 0,
        }
        logger.info("📊 Статистика анализатора качества сброшена")
