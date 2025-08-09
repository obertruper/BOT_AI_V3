"""
Risk Manager для управления рисками торговли
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional


class RiskStatus:
    """Статус проверки рисков"""

    def __init__(
        self,
        requires_action: bool = False,
        action: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.requires_action = requires_action
        self.action = action
        self.message = message


class RiskManager:
    """Менеджер управления рисками"""

    def __init__(
        self, config: Dict[str, Any], position_manager=None, exchange_registry=None
    ):
        self.config = config
        self.position_manager = position_manager
        self.exchange_registry = exchange_registry
        self.logger = logging.getLogger(__name__)

        # Параметры риска из конфигурации
        self.max_risk_per_trade = Decimal(str(config.get("max_risk_per_trade", 0.02)))
        self.max_total_risk = Decimal(str(config.get("max_total_risk", 0.1)))
        self.max_positions = config.get("max_positions", 10)
        self.max_leverage = config.get("max_leverage", 10)

    async def check_signal_risk(self, signal: Dict[str, Any]) -> bool:
        """Проверяет риски для сигнала"""
        try:
            # Базовые проверки
            if not signal:
                return False

            # Проверка размера позиции
            position_size = signal.get("position_size", 0)
            if position_size <= 0:
                self.logger.warning("Invalid position size in signal")
                return False

            # Проверка leverage
            leverage = signal.get("leverage", 1)
            if leverage > self.max_leverage:
                self.logger.warning(
                    f"Leverage {leverage} exceeds max {self.max_leverage}"
                )
                return False

            # Проверка количества открытых позиций
            if self.position_manager:
                positions = await self.position_manager.get_all_positions()
                active_positions = [p for p in positions if p.size != 0]
                if len(active_positions) >= self.max_positions:
                    self.logger.warning(
                        f"Max positions limit reached: {len(active_positions)}/{self.max_positions}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking signal risk: {e}")
            return False

    async def check_global_risks(self) -> RiskStatus:
        """Проверяет глобальные риски системы"""
        try:
            # Проверка общего риска
            if self.position_manager:
                total_risk = await self._calculate_total_risk()
                if total_risk > self.max_total_risk:
                    return RiskStatus(
                        requires_action=True,
                        action="reduce_positions",
                        message=f"Total risk {total_risk:.2%} exceeds limit {self.max_total_risk:.2%}",
                    )

            return RiskStatus(requires_action=False)

        except Exception as e:
            self.logger.error(f"Error checking global risks: {e}")
            return RiskStatus(
                requires_action=True, action="pause", message=f"Risk check error: {e}"
            )

    async def _calculate_total_risk(self) -> Decimal:
        """Вычисляет общий риск по всем позициям"""
        if not self.position_manager:
            return Decimal("0")

        try:
            positions = await self.position_manager.get_all_positions()
            total_risk = Decimal("0")

            for position in positions:
                if position.size != 0:
                    # Простой расчет риска как процент от размера позиции
                    position_risk = abs(position.size) * self.max_risk_per_trade
                    total_risk += position_risk

            return total_risk

        except Exception as e:
            self.logger.error(f"Error calculating total risk: {e}")
            return Decimal("0")

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return True

    def is_running(self) -> bool:
        """Проверка работы компонента"""
        return True
