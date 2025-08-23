"""Модуль RiskManager для управления торговыми рисками.

Определяет и применяет правила управления рисками, включая расчет размера
позиций, проверку лимитов и адаптацию к рыночным условиям и ML-сигналам.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.logger import setup_risk_management_logger


@dataclass
class RiskStatus:
    """Содержит результат проверки рисков.

    Attributes:
        requires_action: True, если требуется немедленное действие (например, пауза).
        action: Предлагаемое действие ('pause', 'reduce_positions').
        message: Сообщение с описанием причины.
    """

    def __init__(
        self,
        requires_action: bool = False,
        action: str | None = None,
        message: str | None = None,
    ):
        self.requires_action = requires_action
        self.action = action
        self.message = message


class RiskManager:
    """Управляет глобальными и локальными торговыми рисками.

    Применяет риск-профили и категории активов для динамического расчета
    размеров позиций и проверки сигналов. Интегрируется с ML-моделями для
    адаптации к качеству предсказаний.
    """

    def __init__(self, config: dict[str, Any], position_manager=None, exchange_registry=None):
        """Инициализирует RiskManager.

        Args:
            config: Словарь с конфигурацией управления рисками.
            position_manager: Экземпляр PositionManager.
            exchange_registry: Экземпляр ExchangeRegistry.
        """
        self.config = config
        self.position_manager = position_manager
        self.exchange_registry = exchange_registry
        self.logger = setup_risk_management_logger()

        # ... (остальные атрибуты)

    def calculate_position_size(
        self,
        signal: dict[str, Any],
        balance: Decimal | None = None,
        profile_name: str | None = None,
    ) -> Decimal:
        """Рассчитывает размер позиции с учетом риск-профиля и ML-сигнала.

        Args:
            signal: Словарь с данными торгового сигнала.
            balance: Текущий баланс счета.
            profile_name: Имя используемого риск-профиля.

        Returns:
            Рекомендуемый размер позиции в USDT.
        """
        # ... (код)

    async def check_signal_risk(self, signal: dict[str, Any]) -> bool:
        """Проверяет, соответствует ли сигнал установленным риск-лимитам.

        Args:
            signal: Словарь с данными торгового сигнала.

        Returns:
            True, если сигнал проходит проверку рисков, иначе False.
        """
        # ... (код)

    async def check_global_risks(self) -> RiskStatus:
        """Проверяет глобальные риски, такие как общий риск портфеля.

        Returns:
            Объект RiskStatus с результатом проверки.
        """
        # ... (код)

    # ... (остальные приватные методы)
