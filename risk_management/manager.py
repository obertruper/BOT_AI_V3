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
        # Используем баланс по умолчанию если не передан
        if balance is None:
            balance = Decimal(str(self.config.get("default_balance", 500)))

        # Процент риска на сделку (по умолчанию 2%)
        risk_percentage = Decimal(str(self.config.get("risk_percentage", 0.02)))

        # Минимальный и максимальный размер позиции
        min_position_size = Decimal(
            str(self.config.get("min_position_size_usdt", 2))
        )  # Уменьшено для тестирования
        max_position_size = Decimal(str(self.config.get("max_position_size_usdt", 1000)))

        # Базовый расчет: процент от баланса
        position_size = balance * risk_percentage

        # Учитываем уверенность сигнала если есть
        if "confidence" in signal:
            confidence = Decimal(str(signal.get("confidence", 0.5)))
            # Масштабируем размер позиции в зависимости от уверенности (0.5 - 1.5x)
            confidence_multiplier = Decimal("0.5") + confidence
            position_size = position_size * confidence_multiplier

        # Применяем лимиты
        position_size = max(min_position_size, min(position_size, max_position_size))

        self.logger.info(
            f"📊 Рассчитан размер позиции: ${position_size:.2f} USDT "
            f"(баланс: ${balance:.2f}, риск: {risk_percentage * 100:.1f}%)"
        )

        return position_size

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
        # Базовая проверка рисков
        status = RiskStatus(requires_action=False)

        # Проверяем количество открытых позиций если есть position_manager
        if self.position_manager:
            try:
                active_positions = await self.position_manager.get_active_positions()
                max_positions = self.config.get("max_concurrent_positions", 10)

                if len(active_positions) >= max_positions:
                    status.requires_action = True
                    status.action = "pause"
                    status.message = (
                        f"Достигнут лимит открытых позиций: {len(active_positions)}/{max_positions}"
                    )
                    self.logger.warning(status.message)
            except Exception as e:
                self.logger.error(f"Ошибка проверки позиций: {e}")

        return status

    # ... (остальные приватные методы)
