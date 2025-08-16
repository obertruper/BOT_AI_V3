"""
Менеджер весов для системы скоринга
Управляет базовыми весами категорий индикаторов
"""

import logging

logger = logging.getLogger(__name__)


class WeightManager:
    """
    Управление весами категорий индикаторов

    Базовые веса из документации:
    - trend (трендовые): 30%
    - momentum (импульсные): 25%
    - volume (объёмные): 25%
    - volatility (волатильность): 20%
    """

    # Веса по умолчанию согласно документации
    DEFAULT_WEIGHTS = {
        "trend": 0.30,  # Трендовые индикаторы: 30%
        "momentum": 0.25,  # Импульсные индикаторы: 25%
        "volume": 0.25,  # Объёмные индикаторы: 25%
        "volatility": 0.20,  # Индикаторы волатильности: 20%
    }

    # Детализация весов внутри категорий
    CATEGORY_WEIGHTS = {
        "trend": {
            "ema_crossover": 0.40,  # 40% от веса категории
            "macd": 0.35,  # 35% от веса категории
            "sma_trend": 0.25,  # 25% от веса категории
        },
        "momentum": {
            "rsi": 0.40,  # 40% от веса категории
            "stochastic": 0.35,  # 35% от веса категории
            "williams_r": 0.25,  # 25% от веса категории
        },
        "volume": {
            "obv": 0.40,  # 40% от веса категории
            "vwap": 0.35,  # 35% от веса категории
            "volume_profile": 0.25,  # 25% от веса категории
        },
        "volatility": {
            "bollinger": 0.50,  # 50% от веса категории
            "atr": 0.30,  # 30% от веса категории
            "vix_crypto": 0.20,  # 20% от веса категории
        },
    }

    def __init__(self, custom_weights: dict[str, float] | None = None):
        """
        Инициализация менеджера весов

        Args:
            custom_weights: Пользовательские веса категорий (должны суммироваться в 1.0)
        """
        if custom_weights:
            self._validate_and_set_weights(custom_weights)
        else:
            self.weights = self.DEFAULT_WEIGHTS.copy()

        logger.info(f"WeightManager initialized with weights: {self.weights}")

    def _validate_and_set_weights(self, weights: dict[str, float]) -> None:
        """Валидация и установка весов"""
        # Проверка наличия всех категорий
        required_categories = set(self.DEFAULT_WEIGHTS.keys())
        provided_categories = set(weights.keys())

        if provided_categories != required_categories:
            missing = required_categories - provided_categories
            extra = provided_categories - required_categories
            raise ValueError(f"Invalid weight categories. Missing: {missing}, Extra: {extra}")

        # Проверка диапазона весов
        for category, weight in weights.items():
            if not 0 <= weight <= 1:
                raise ValueError(f"Weight for {category} must be between 0 and 1, got {weight}")

        # Проверка суммы весов
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, normalizing to 1.0")
            # Нормализация весов
            weights = {k: v / total_weight for k, v in weights.items()}

        self.weights = weights

    def get_weights(self) -> dict[str, float]:
        """Получение текущих весов категорий"""
        return self.weights.copy()

    def get_category_weight(self, category: str) -> float:
        """
        Получение веса конкретной категории

        Args:
            category: Название категории

        Returns:
            Вес категории или 0 если категория не найдена
        """
        return self.weights.get(category, 0.0)

    def get_indicator_weight(self, category: str, indicator: str) -> float:
        """
        Получение полного веса индикатора с учетом веса категории

        Args:
            category: Название категории
            indicator: Название индикатора

        Returns:
            Полный вес индикатора
        """
        category_weight = self.get_category_weight(category)

        if category in self.CATEGORY_WEIGHTS:
            indicator_weight = self.CATEGORY_WEIGHTS[category].get(indicator, 0.0)
            return category_weight * indicator_weight
        else:
            # Если детализация не определена, распределяем вес равномерно
            return category_weight

    def update_weights(self, new_weights: dict[str, float]) -> None:
        """
        Обновление весов категорий

        Args:
            new_weights: Новые веса категорий
        """
        self._validate_and_set_weights(new_weights)
        logger.info(f"Weights updated: {self.weights}")

    def adjust_weight(self, category: str, adjustment: float) -> None:
        """
        Корректировка веса категории с автоматической нормализацией

        Args:
            category: Название категории
            adjustment: Величина корректировки (может быть отрицательной)
        """
        if category not in self.weights:
            raise ValueError(f"Unknown category: {category}")

        # Применение корректировки
        old_weight = self.weights[category]
        new_weight = max(0, min(1, old_weight + adjustment))

        # Расчет изменения
        weight_change = new_weight - old_weight

        # Распределение изменения на другие категории
        other_categories = [c for c in self.weights if c != category]
        if other_categories and weight_change != 0:
            adjustment_per_category = -weight_change / len(other_categories)

            for other_cat in other_categories:
                self.weights[other_cat] = max(
                    0, min(1, self.weights[other_cat] + adjustment_per_category)
                )

        self.weights[category] = new_weight

        # Финальная нормализация
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

        logger.info(f"Adjusted {category} weight by {adjustment}, new weights: {self.weights}")

    def reset_to_defaults(self) -> None:
        """Сброс весов к значениям по умолчанию"""
        self.weights = self.DEFAULT_WEIGHTS.copy()
        logger.info("Weights reset to defaults")

    def get_weight_summary(self) -> dict[str, any]:
        """Получение полной информации о весах"""
        summary = {
            "category_weights": self.weights,
            "total_weight": sum(self.weights.values()),
            "indicator_weights": {},
        }

        # Расчет полных весов индикаторов
        for category, indicators in self.CATEGORY_WEIGHTS.items():
            category_weight = self.get_category_weight(category)
            summary["indicator_weights"][category] = {
                indicator: category_weight * weight for indicator, weight in indicators.items()
            }

        return summary

    def validate_weights(self) -> bool:
        """
        Проверка корректности текущих весов

        Returns:
            True если веса корректны
        """
        # Проверка суммы
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            return False

        # Проверка диапазона
        for weight in self.weights.values():
            if not 0 <= weight <= 1:
                return False

        return True
