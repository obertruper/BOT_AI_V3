"""
Обработчик торговых сигналов v2 - правильная архитектура

Принимает сигналы и создает ордера для исполнения.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from database.models.base_models import Order, OrderSide, OrderType, SignalType
from database.models.signal import Signal


class SignalProcessor:
    """
    Процессор торговых сигналов

    Обеспечивает:
    - Валидацию сигналов
    - Создание ордеров из сигналов
    - Управление риском на уровне ордеров
    """

    def __init__(
        self, config: Dict[str, Any], exchange_registry: Any, order_manager: Any = None
    ):
        self.config = config
        self.exchange_registry = exchange_registry
        self.order_manager = order_manager
        self.logger = logging.getLogger(__name__)

        # Состояние
        self._running = False
        self._processed_signals = set()

        # Параметры риск-менеджмента
        self.default_position_size = Decimal(
            str(config.get("default_position_size", 100))
        )
        self.max_position_size = Decimal(str(config.get("max_position_size", 1000)))
        self.default_leverage = config.get("default_leverage", 1)

    async def process_signal(self, signal: Signal) -> List[Order]:
        """
        Обработка торгового сигнала и создание ордеров

        Args:
            signal: Торговый сигнал для обработки

        Returns:
            List[Order]: Список созданных ордеров
        """
        try:
            self.logger.info(
                f"📊 Обработка сигнала: {signal.symbol} {signal.signal_type.value} "
                f"(сила: {signal.strength:.2f})"
            )

            # Валидация сигнала
            if not await self.validate_signal(signal):
                self.logger.warning(f"❌ Невалидный сигнал: {signal.symbol}")
                return []

            # Проверка дубликатов
            signal_key = (
                f"{signal.symbol}_{signal.signal_type.value}_{signal.created_at}"
            )
            if signal_key in self._processed_signals:
                self.logger.debug(f"Дубликат сигнала пропущен: {signal_key}")
                return []

            # Нейтральные сигналы не создают ордера
            if signal.signal_type == SignalType.NEUTRAL:
                self.logger.info("📊 Нейтральный сигнал, ордера не создаются")
                self._processed_signals.add(signal_key)
                return []

            # Создание ордеров
            orders = await self._create_orders_from_signal(signal)

            if orders:
                self._processed_signals.add(signal_key)
                self.logger.info(
                    f"✅ Создано {len(orders)} ордеров для сигнала {signal.symbol}"
                )
            else:
                self.logger.warning(
                    f"⚠️ Не удалось создать ордера для сигнала {signal.symbol}"
                )

            return orders

        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки сигнала: {e}")
            return []

    async def validate_signal(self, signal: Signal) -> bool:
        """Валидация торгового сигнала"""
        try:
            # Базовые проверки
            if not signal.symbol or not signal.exchange:
                self.logger.warning("Сигнал без символа или биржи")
                return False

            # Проверка силы и уверенности
            if signal.strength is not None:
                if not 0 <= signal.strength <= 1:
                    self.logger.warning(f"Некорректная сила сигнала: {signal.strength}")
                    return False

            if signal.confidence is not None:
                if not 0 <= signal.confidence <= 1:
                    self.logger.warning(
                        f"Некорректная уверенность: {signal.confidence}"
                    )
                    return False

            # Проверка доступности символа на бирже
            if self.exchange_registry:
                # TODO: проверить поддержку символа на бирже
                pass

            return True

        except Exception as e:
            self.logger.error(f"Ошибка валидации сигнала: {e}")
            return False

    async def _create_orders_from_signal(self, signal: Signal) -> List[Order]:
        """Создание ордеров из сигнала"""
        orders = []

        try:
            # Определяем сторону ордера
            if signal.signal_type == SignalType.LONG:
                side = OrderSide.BUY
            elif signal.signal_type == SignalType.SHORT:
                side = OrderSide.SELL
            else:
                return []

            # Рассчитываем размер позиции
            position_size = await self._calculate_position_size(signal)
            if position_size <= 0:
                self.logger.warning("Размер позиции <= 0, ордер не создается")
                return []

            # Получаем текущую цену если не указана
            entry_price = signal.suggested_price
            if not entry_price:
                # TODO: получить текущую цену с биржи
                self.logger.warning("Нет цены входа в сигнале")
                return []

            # Рассчитываем количество в базовой валюте
            # position_size - это размер в долларах, нужно конвертировать в количество актива
            if hasattr(signal, "suggested_quantity") and signal.suggested_quantity:
                quantity = Decimal(str(signal.suggested_quantity))
            else:
                # Конвертируем доллары в количество актива
                quantity = position_size / entry_price

            # Минимальные требования Bybit для BTC: 0.001 (~$100)
            # Для других активов будут другие минимумы, но используем общий подход
            min_quantity = Decimal("0.001")  # Минимум для BTC

            # Если количество меньше минимального, увеличиваем до минимума
            if quantity < min_quantity:
                self.logger.warning(
                    f"Количество {quantity} меньше минимального {min_quantity}, "
                    f"увеличиваем до минимума"
                )
                quantity = min_quantity
                # Пересчитываем размер позиции в долларах
                position_size = quantity * entry_price

            # Округляем количество до разумной точности (0.00001 BTC)
            quantity = quantity.quantize(Decimal("0.00001"))

            # Создаем основной ордер
            main_order = Order(
                symbol=signal.symbol,
                exchange=signal.exchange,
                side=side,
                order_type=OrderType.LIMIT,  # Используем лимитные ордера по умолчанию
                quantity=float(quantity),  # Количество в базовой валюте (BTC)
                price=float(entry_price),
                # Генерируем уникальный order_id
                order_id=f"SP_{signal.exchange}_{signal.symbol}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                # Добавляем дополнительную информацию
                strategy_name=signal.strategy_name,
                trader_id="signal_processor",
                extra_data={
                    "signal_id": signal.id,
                    "signal_type": signal.signal_type.value,
                    "signal_strength": signal.strength,
                    "signal_confidence": signal.confidence,
                    "position_size_usd": str(
                        position_size
                    ),  # Сохраняем размер в долларах
                    "leverage": self.default_leverage,
                },
            )

            # Устанавливаем SL/TP если указаны
            if signal.suggested_stop_loss:
                main_order.stop_loss = signal.suggested_stop_loss
            if signal.suggested_take_profit:
                main_order.take_profit = signal.suggested_take_profit

            orders.append(main_order)

            self.logger.info(
                f"📋 Создан ордер: {side.value} {quantity} {signal.symbol} "
                f"@ {entry_price} (${position_size} USD) "
                f"(SL: {main_order.stop_loss}, TP: {main_order.take_profit})"
            )

            return orders

        except Exception as e:
            self.logger.error(f"Ошибка создания ордеров: {e}")
            return []

    async def _calculate_position_size(self, signal: Signal) -> Decimal:
        """Расчет размера позиции на основе сигнала и риск-менеджмента"""
        try:
            # Если размер указан в сигнале - используем его
            if signal.suggested_position_size and signal.suggested_position_size > 0:
                size = Decimal(str(signal.suggested_position_size))
            else:
                # Иначе используем дефолтный размер с учетом силы сигнала
                base_size = self.default_position_size

                # Корректируем размер на основе силы сигнала
                if signal.strength:
                    size = base_size * Decimal(str(signal.strength))
                else:
                    size = base_size

            # Ограничиваем максимальным размером
            size = min(size, self.max_position_size)

            # Округляем до разумной точности
            size = size.quantize(Decimal("0.001"))

            return size

        except Exception as e:
            self.logger.error(f"Ошибка расчета размера позиции: {e}")
            return Decimal("0")

    async def start(self):
        """Запуск процессора"""
        self._running = True
        self.logger.info("✅ Signal Processor запущен")

    async def stop(self):
        """Остановка процессора"""
        self._running = False
        self._processed_signals.clear()
        self.logger.info("🛑 Signal Processor остановлен")

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return self._running

    def is_running(self) -> bool:
        """Проверка работы компонента"""
        return self._running
