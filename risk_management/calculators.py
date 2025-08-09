"""
Risk Calculator - калькулятор рисков для торговых операций
"""

import logging
from decimal import Decimal
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RiskCalculator:
    """Калькулятор рисков"""

    def __init__(self, config: Dict):
        self.config = config
        self.max_risk_per_trade = Decimal(
            str(config.get("max_risk_per_trade", 0.02))
        )  # 2%
        self.max_position_size = Decimal(str(config.get("max_position_size", 1000)))
        self.min_position_size = Decimal(str(config.get("min_position_size", 10)))

    def calculate_position_size(
        self,
        account_balance: Decimal,
        entry_price: Decimal,
        stop_loss: Decimal,
        risk_percentage: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Рассчитать размер позиции на основе риска

        Args:
            account_balance: Баланс счета
            entry_price: Цена входа
            stop_loss: Уровень стоп-лосса
            risk_percentage: Процент риска на сделку

        Returns:
            Размер позиции
        """
        if risk_percentage is None:
            risk_percentage = self.max_risk_per_trade

        # Риск в долларах
        risk_amount = account_balance * risk_percentage

        # Риск на единицу
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            logger.warning("Риск на единицу равен 0, используем минимальный размер")
            return self.min_position_size

        # Размер позиции
        position_size = risk_amount / risk_per_unit

        # Ограничения
        position_size = min(position_size, self.max_position_size)
        position_size = max(position_size, self.min_position_size)

        return position_size

    def calculate_risk_reward_ratio(
        self, entry_price: Decimal, stop_loss: Decimal, take_profit: Decimal
    ) -> Decimal:
        """
        Рассчитать соотношение риск/прибыль

        Args:
            entry_price: Цена входа
            stop_loss: Уровень стоп-лосса
            take_profit: Уровень тейк-профита

        Returns:
            Соотношение риск/прибыль
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk == 0:
            return Decimal("0")

        return reward / risk

    def validate_risk_parameters(
        self,
        position_size: Decimal,
        entry_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        account_balance: Optional[Decimal] = None,
    ) -> bool:
        """
        Валидировать параметры риска

        Args:
            position_size: Размер позиции
            entry_price: Цена входа
            stop_loss: Уровень стоп-лосса
            account_balance: Баланс счета

        Returns:
            True если параметры валидны
        """
        # Проверка размера позиции
        if position_size < self.min_position_size:
            logger.warning(
                f"Размер позиции {position_size} меньше минимального {self.min_position_size}"
            )
            return False

        if position_size > self.max_position_size:
            logger.warning(
                f"Размер позиции {position_size} больше максимального {self.max_position_size}"
            )
            return False

        # Проверка риска если есть стоп-лосс и баланс
        if stop_loss and account_balance:
            risk = position_size * abs(entry_price - stop_loss)
            max_risk = account_balance * self.max_risk_per_trade

            if risk > max_risk:
                logger.warning(f"Риск {risk} превышает максимальный {max_risk}")
                return False

        return True
