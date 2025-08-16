#!/usr/bin/env python3
"""
ML Signal Strategy - интеграция ML сигналов с торговой системой
Использует сигналы от SignalScheduler для автоматической торговли
"""

from datetime import datetime, timedelta
from typing import Any

from core.logger import setup_logger
from core.shared_context import shared_context
from database.models.base_models import SignalType
from database.models.signal import Signal
from strategies.base.strategy_abc import StrategyABC

logger = setup_logger(__name__)


class MLSignalStrategy(StrategyABC):
    """
    Торговая стратегия на основе ML сигналов

    Особенности:
    - Получает готовые сигналы от ML системы
    - Применяет дополнительные фильтры
    - Управляет позициями на основе ML предсказаний
    - Адаптивное управление рисками
    """

    def __init__(self, config: dict[str, Any]):
        """
        Инициализация ML Signal Strategy

        Args:
            config: Конфигурация стратегии
        """
        super().__init__(config)

        # ML параметры
        self.min_confidence = self.config.get("min_confidence", 0.6)
        self.min_signal_strength = self.config.get("min_signal_strength", 0.4)
        self.signal_timeout_minutes = self.config.get("signal_timeout_minutes", 15)

        # Управление позициями
        self.position_size_percent = self.config.get("position_size_percent", 0.02)  # 2% от баланса
        self.max_positions = self.config.get("max_positions", 1)

        # Risk management
        self.use_ml_stop_loss = self.config.get("use_ml_stop_loss", True)
        self.use_ml_take_profit = self.config.get("use_ml_take_profit", True)
        self.default_stop_loss_pct = self.config.get("default_stop_loss_pct", 0.02)
        self.default_take_profit_pct = self.config.get("default_take_profit_pct", 0.04)

        # Состояние
        self.last_signal_time = None
        self.current_ml_signal = None
        self.signal_history = []

        logger.info(f"MLSignalStrategy инициализирована для {symbol} на {exchange}")

    async def initialize(self) -> bool:
        """Инициализация стратегии"""
        try:
            await super().initialize()

            # Получаем доступ к SignalScheduler через shared context
            orchestrator = shared_context.get_orchestrator()
            if orchestrator and hasattr(orchestrator, "signal_scheduler"):
                self.signal_scheduler = orchestrator.signal_scheduler
                logger.info("✅ Подключен к ML SignalScheduler")
            else:
                logger.warning("⚠️ SignalScheduler не найден в orchestrator")
                self.signal_scheduler = None

            logger.info(f"✅ MLSignalStrategy инициализирована для {self.symbol}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации MLSignalStrategy: {e}")
            return False

    async def should_enter_long(self, data: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
        """
        Проверка условий для открытия LONG позиции

        Args:
            data: Рыночные данные

        Returns:
            (should_enter, signal_data)
        """
        try:
            # Получаем последний ML сигнал
            ml_signal = await self._get_latest_ml_signal()

            if not ml_signal:
                return False, None

            # Проверяем что это LONG сигнал
            if ml_signal.signal_type != SignalType.LONG:
                return False, None

            # Проверяем качество сигнала
            if not self._validate_signal_quality(ml_signal):
                return False, None

            # Проверяем тайминг сигнала
            if not self._check_signal_timing(ml_signal):
                return False, None

            # Формируем данные сигнала
            signal_data = {
                "ml_signal": ml_signal,
                "confidence": ml_signal.confidence,
                "strength": ml_signal.strength,
                "entry_price": data.get("close", ml_signal.suggested_price),
                "stop_loss": ml_signal.suggested_stop_loss if self.use_ml_stop_loss else None,
                "take_profit": ml_signal.suggested_take_profit if self.use_ml_take_profit else None,
                "ml_indicators": ml_signal.indicators,
                "timestamp": datetime.utcnow(),
            }

            logger.info(
                f"🚀 LONG сигнал для {self.symbol}: "
                f"confidence={ml_signal.confidence:.1%}, strength={ml_signal.strength:.2f}"
            )

            return True, signal_data

        except Exception as e:
            logger.error(f"Ошибка проверки LONG условий: {e}")
            return False, None

    async def should_enter_short(self, data: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
        """
        Проверка условий для открытия SHORT позиции

        Args:
            data: Рыночные данные

        Returns:
            (should_enter, signal_data)
        """
        try:
            # Получаем последний ML сигнал
            ml_signal = await self._get_latest_ml_signal()

            if not ml_signal:
                return False, None

            # Проверяем что это SHORT сигнал
            if ml_signal.signal_type != SignalType.SHORT:
                return False, None

            # Проверяем качество сигнала
            if not self._validate_signal_quality(ml_signal):
                return False, None

            # Проверяем тайминг сигнала
            if not self._check_signal_timing(ml_signal):
                return False, None

            # Формируем данные сигнала
            signal_data = {
                "ml_signal": ml_signal,
                "confidence": ml_signal.confidence,
                "strength": ml_signal.strength,
                "entry_price": data.get("close", ml_signal.suggested_price),
                "stop_loss": ml_signal.suggested_stop_loss if self.use_ml_stop_loss else None,
                "take_profit": ml_signal.suggested_take_profit if self.use_ml_take_profit else None,
                "ml_indicators": ml_signal.indicators,
                "timestamp": datetime.utcnow(),
            }

            logger.info(
                f"🔻 SHORT сигнал для {self.symbol}: "
                f"confidence={ml_signal.confidence:.1%}, strength={ml_signal.strength:.2f}"
            )

            return True, signal_data

        except Exception as e:
            logger.error(f"Ошибка проверки SHORT условий: {e}")
            return False, None

    async def should_exit_position(self, position_data: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Проверка условий для закрытия позиции

        Args:
            position_data: Данные о позиции

        Returns:
            (should_exit, reason)
        """
        try:
            # Получаем новый ML сигнал
            ml_signal = await self._get_latest_ml_signal()

            if ml_signal:
                # Проверяем смену направления
                current_position_type = position_data.get("side", "").upper()
                new_signal_type = ml_signal.signal_type.value.upper()

                # Если ML модель сменила направление - закрываем позицию
                if (current_position_type == "LONG" and new_signal_type == "SHORT") or (
                    current_position_type == "SHORT" and new_signal_type == "LONG"
                ):
                    logger.info(
                        f"🔄 Смена ML сигнала: {current_position_type} → {new_signal_type}, "
                        f"закрываем позицию для {self.symbol}"
                    )
                    return (
                        True,
                        f"ML signal changed: {current_position_type} → {new_signal_type}",
                    )

            # Проверяем стандартные условия выхода (SL/TP)
            return await super().should_exit_position(position_data)

        except Exception as e:
            logger.error(f"Ошибка проверки условий выхода: {e}")
            return False, None

    async def calculate_position_size(self, signal_data: dict[str, Any], balance: float) -> float:
        """
        Расчет размера позиции на основе ML предсказаний

        Args:
            signal_data: Данные сигнала
            balance: Доступный баланс

        Returns:
            Размер позиции в USDT
        """
        try:
            # Базовый размер позиции
            base_size = balance * self.position_size_percent

            # Корректировка по уверенности ML модели
            confidence = signal_data.get("confidence", 0.5)
            confidence_multiplier = min(confidence * 1.5, 1.2)  # Максимум 20% увеличение

            # Корректировка по силе сигнала
            strength = signal_data.get("strength", 0.5)
            strength_multiplier = min(strength * 1.3, 1.1)  # Максимум 10% увеличение

            # Итоговый размер позиции
            position_size = base_size * confidence_multiplier * strength_multiplier

            # Ограничиваем максимальным размером
            max_position = balance * 0.1  # Не более 10% от баланса
            position_size = min(position_size, max_position)

            logger.info(
                f"💰 Размер позиции для {self.symbol}: {position_size:.2f} USDT "
                f"(base: {base_size:.2f}, conf: {confidence:.1%}, strength: {strength:.2f})"
            )

            return position_size

        except Exception as e:
            logger.error(f"Ошибка расчета размера позиции: {e}")
            return balance * self.position_size_percent

    async def _get_latest_ml_signal(self) -> Signal | None:
        """Получение последнего ML сигнала для символа"""
        try:
            if not self.signal_scheduler:
                return None

            # Получаем статус планировщика
            status = await self.signal_scheduler.get_status()

            # Ищем последний сигнал для нашего символа
            symbol_status = status.get("symbols", {}).get(self.symbol, {})
            last_signal_data = symbol_status.get("last_signal", {})

            if last_signal_data and last_signal_data.get("success"):
                signal = last_signal_data.get("signal")
                if signal:
                    # Сохраняем ссылку для быстрого доступа
                    self.current_ml_signal = signal
                    self.last_signal_time = last_signal_data.get("timestamp")
                    return signal

            return None

        except Exception as e:
            logger.error(f"Ошибка получения ML сигнала: {e}")
            return None

    def _validate_signal_quality(self, signal: Signal) -> bool:
        """Валидация качества ML сигнала"""
        try:
            # Проверяем минимальную уверенность
            if signal.confidence < self.min_confidence:
                logger.debug(
                    f"Низкая уверенность: {signal.confidence:.1%} < {self.min_confidence:.1%}"
                )
                return False

            # Проверяем минимальную силу сигнала
            if signal.strength < self.min_signal_strength:
                logger.debug(
                    f"Слабый сигнал: {signal.strength:.2f} < {self.min_signal_strength:.2f}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Ошибка валидации сигнала: {e}")
            return False

    def _check_signal_timing(self, signal: Signal) -> bool:
        """Проверка актуальности сигнала по времени"""
        try:
            if not signal.created_at:
                return False

            # Проверяем что сигнал не слишком старый
            signal_age = datetime.utcnow() - signal.created_at
            max_age = timedelta(minutes=self.signal_timeout_minutes)

            if signal_age > max_age:
                logger.debug(
                    f"Устаревший сигнал: возраст {signal_age.total_seconds():.0f}с > "
                    f"{max_age.total_seconds():.0f}с"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Ошибка проверки времени сигнала: {e}")
            return False

    async def get_strategy_info(self) -> dict[str, Any]:
        """Информация о стратегии"""
        info = await super().get_strategy_info()

        info.update(
            {
                "type": "ML_Signal_Strategy",
                "ml_parameters": {
                    "min_confidence": self.min_confidence,
                    "min_signal_strength": self.min_signal_strength,
                    "signal_timeout_minutes": self.signal_timeout_minutes,
                    "position_size_percent": self.position_size_percent,
                },
                "ml_status": {
                    "signal_scheduler_connected": self.signal_scheduler is not None,
                    "last_signal_time": (
                        self.last_signal_time.isoformat() if self.last_signal_time else None
                    ),
                    "current_signal_type": (
                        self.current_ml_signal.signal_type.value if self.current_ml_signal else None
                    ),
                },
            }
        )

        return info

    async def cleanup(self):
        """Очистка ресурсов стратегии"""
        try:
            self.signal_scheduler = None
            self.current_ml_signal = None
            self.signal_history.clear()

            await super().cleanup()
            logger.info(f"✅ MLSignalStrategy очищена для {self.symbol}")

        except Exception as e:
            logger.error(f"Ошибка очистки MLSignalStrategy: {e}")


# Регистрируем стратегию в реестре
from strategies.registry import register_strategy


@register_strategy(
    "MLSignalStrategy",
    description="ML стратегия на основе сигналов от UnifiedPatchTST модели",
    version="1.0.0",
    author="BOT_Trading_v3",
    tags=["ml", "neural_network", "patchtst", "real_time"],
)
class RegisteredMLSignalStrategy(MLSignalStrategy):
    """Зарегистрированная версия MLSignalStrategy"""

    pass
