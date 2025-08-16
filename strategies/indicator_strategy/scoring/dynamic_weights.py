"""
Калькулятор динамических весов для адаптации к режимам рынка
Реализует рекомендации Claude из кросс-верификации
"""

import logging

logger = logging.getLogger(__name__)


class DynamicWeightCalculator:
    """
    Расчет динамических весов на основе режима рынка

    Реализует адаптивную систему весов согласно рекомендациям AI:
    - В трендовом рынке: усиление трендовых индикаторов
    - В боковом рынке: усиление осцилляторов
    - При высокой волатильности: усиление индикаторов волатильности
    """

    # Множители по умолчанию из кросс-верификации
    DEFAULT_MULTIPLIERS = {
        "trending": {
            "trend": 1.3,  # Усиление трендовых на 30%
            "momentum": 1.1,  # Небольшое усиление импульса
            "volume": 1.0,  # Без изменений
            "volatility": 0.8,  # Ослабление волатильности
        },
        "ranging": {
            "trend": 0.7,  # Ослабление трендовых
            "momentum": 1.4,  # Сильное усиление осцилляторов
            "volume": 1.1,  # Небольшое усиление объема
            "volatility": 1.2,  # Усиление волатильности
        },
        "high_volatility": {
            "trend": 0.9,  # Небольшое ослабление трендовых
            "momentum": 0.8,  # Ослабление импульса (много ложных сигналов)
            "volume": 1.2,  # Усиление объема
            "volatility": 1.5,  # Сильное усиление волатильности
        },
        "low_volatility": {
            "trend": 1.2,  # Усиление трендовых
            "momentum": 1.3,  # Усиление импульса (прорывы)
            "volume": 0.9,  # Небольшое ослабление объема
            "volatility": 0.7,  # Ослабление волатильности
        },
    }

    def __init__(self, custom_multipliers: dict[str, dict[str, float]] | None = None):
        """
        Инициализация калькулятора

        Args:
            custom_multipliers: Пользовательские множители для режимов
        """
        self.multipliers = custom_multipliers or self.DEFAULT_MULTIPLIERS.copy()
        self._last_regime = None
        self._transition_factor = 1.0

    def calculate_weights(
        self,
        base_weights: dict[str, float],
        market_regime: str,
        smooth_transition: bool = True,
    ) -> dict[str, float]:
        """
        Расчет динамических весов для текущего режима рынка

        Args:
            base_weights: Базовые веса категорий
            market_regime: Текущий режим рынка
            smooth_transition: Использовать плавный переход между режимами

        Returns:
            Адаптированные веса
        """
        if market_regime not in self.multipliers:
            logger.warning(f"Unknown market regime: {market_regime}, using base weights")
            return base_weights.copy()

        # Получение множителей для режима
        regime_multipliers = self.multipliers[market_regime]

        # Применение множителей
        adjusted_weights = {}
        for category, base_weight in base_weights.items():
            multiplier = regime_multipliers.get(category, 1.0)

            # Плавный переход между режимами
            if smooth_transition and self._last_regime and self._last_regime != market_regime:
                # Постепенное изменение множителя
                old_multiplier = self.multipliers.get(self._last_regime, {}).get(category, 1.0)
                multiplier = self._smooth_transition(old_multiplier, multiplier)

            adjusted_weights[category] = base_weight * multiplier

        # Нормализация весов
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            normalized_weights = {k: v / total_weight for k, v in adjusted_weights.items()}
        else:
            normalized_weights = base_weights.copy()

        # Сохранение текущего режима
        self._last_regime = market_regime

        logger.debug(f"Dynamic weights for {market_regime}: {normalized_weights}")

        return normalized_weights

    def _smooth_transition(self, old_value: float, new_value: float) -> float:
        """
        Плавный переход между значениями

        Args:
            old_value: Предыдущее значение
            new_value: Новое значение

        Returns:
            Сглаженное значение
        """
        # Экспоненциальное сглаживание
        alpha = 0.3  # Коэффициент сглаживания
        return old_value * (1 - alpha) + new_value * alpha

    def get_regime_characteristics(self, market_regime: str) -> dict[str, any]:
        """
        Получение характеристик режима рынка

        Args:
            market_regime: Режим рынка

        Returns:
            Характеристики режима
        """
        characteristics = {
            "trending": {
                "description": "Трендовый рынок",
                "best_indicators": ["EMA", "MACD", "ADX"],
                "trading_style": "Следование за трендом",
                "risk_level": "Средний",
                "position_duration": "3-7 дней",
                "tips": [
                    "Увеличивайте позиции в направлении тренда",
                    "Используйте трейлинг-стоп для защиты прибыли",
                    "Избегайте контртрендовых сделок",
                ],
            },
            "ranging": {
                "description": "Боковой/флэтовый рынок",
                "best_indicators": ["RSI", "Stochastic", "Bollinger Bands"],
                "trading_style": "Торговля от границ диапазона",
                "risk_level": "Низкий-Средний",
                "position_duration": "1-3 дня",
                "tips": [
                    "Покупайте у поддержки, продавайте у сопротивления",
                    "Используйте осцилляторы для определения перекупленности",
                    "Ставьте жесткие стоп-лоссы",
                ],
            },
            "high_volatility": {
                "description": "Высокая волатильность",
                "best_indicators": ["ATR", "Bollinger Bands", "Volume"],
                "trading_style": "Осторожная торговля с уменьшенными позициями",
                "risk_level": "Высокий",
                "position_duration": "1-2 дня",
                "tips": [
                    "Уменьшайте размер позиций",
                    "Расширяйте стоп-лоссы с учетом ATR",
                    "Фиксируйте прибыль частями",
                ],
            },
            "low_volatility": {
                "description": "Низкая волатильность (затишье)",
                "best_indicators": ["Volume", "MACD", "RSI"],
                "trading_style": "Ожидание прорыва",
                "risk_level": "Низкий",
                "position_duration": "5-7 дней",
                "tips": [
                    "Готовьтесь к прорыву волатильности",
                    "Накапливайте позиции постепенно",
                    "Следите за объемами для подтверждения",
                ],
            },
        }

        return characteristics.get(
            market_regime,
            {
                "description": "Неизвестный режим",
                "best_indicators": [],
                "trading_style": "Неопределенный",
                "risk_level": "Неизвестный",
                "tips": [],
            },
        )

    def suggest_adjustments(
        self, current_performance: dict[str, float], market_regime: str
    ) -> dict[str, any]:
        """
        Предложение корректировок на основе производительности

        Args:
            current_performance: Текущие показатели по категориям
            market_regime: Текущий режим рынка

        Returns:
            Рекомендации по корректировке
        """
        suggestions = {"adjustments": [], "reasoning": []}

        # Анализ производительности по категориям
        for category, performance in current_performance.items():
            expected_multiplier = self.multipliers.get(market_regime, {}).get(category, 1.0)

            # Если категория работает хуже ожидаемого
            if performance < 0.4 and expected_multiplier > 1.0:
                suggestions["adjustments"].append(
                    {
                        "category": category,
                        "action": "decrease_multiplier",
                        "current": expected_multiplier,
                        "suggested": expected_multiplier * 0.8,
                    }
                )
                suggestions["reasoning"].append(
                    f"{category} показывает низкую производительность в {market_regime} режиме"
                )

            # Если категория работает лучше ожидаемого
            elif performance > 0.7 and expected_multiplier < 1.2:
                suggestions["adjustments"].append(
                    {
                        "category": category,
                        "action": "increase_multiplier",
                        "current": expected_multiplier,
                        "suggested": min(expected_multiplier * 1.2, 1.5),
                    }
                )
                suggestions["reasoning"].append(
                    f"{category} показывает высокую производительность в {market_regime} режиме"
                )

        return suggestions

    def reset_multipliers(self) -> None:
        """Сброс множителей к значениям по умолчанию"""
        self.multipliers = self.DEFAULT_MULTIPLIERS.copy()
        self._last_regime = None
        self._transition_factor = 1.0
        logger.info("Dynamic weight multipliers reset to defaults")
