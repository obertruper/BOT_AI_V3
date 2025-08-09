#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced SL/TP Manager для BOT Trading v3

Улучшенный менеджер стоп-лосс и тейк-профит ордеров.
Адаптирован из v2 для асинхронной архитектуры v3.
"""

from datetime import datetime
from typing import Dict, List, Optional

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.models import Order, Position
from trading.signals.signal import Signal

from .models import (
    PartialTPLevel,
    SLTPConfig,
    SLTPHistory,
    SLTPOrder,
    SLTPStatus,
    TrailingStopConfig,
    TrailingType,
)

logger = setup_logger("enhanced_sltp_manager")


class EnhancedSLTPManager:
    """
    Улучшенный менеджер SL/TP для v3.

    Предоставляет расширенные функции:
    - Трейлинг-стоп с адаптивным шагом
    - Защита прибыли с многоуровневыми правилами
    - Многоуровневый частичный тейк-профит
    - Динамический TP на основе волатильности
    - Временные корректировки SL/TP
    """

    def __init__(self, config_manager: ConfigManager, exchange_client=None):
        """
        Инициализация менеджера.

        Args:
            config_manager: Менеджер конфигурации
            exchange_client: Клиент биржи
        """
        self.config_manager = config_manager
        self.exchange_client = exchange_client

        # Загружаем конфигурацию
        self.config = self._load_config()

        # Кэш активных SL/TP ордеров
        self._active_orders: Dict[str, List[SLTPOrder]] = {}

        # История изменений
        self._history: List[SLTPHistory] = []

        logger.info("Успешно инициализирован EnhancedSLTPManager")

    def _load_config(self) -> SLTPConfig:
        """Загружает конфигурацию из файла"""
        system_config = self.config_manager.get_system_config()
        sltp_settings = system_config.get("enhanced_sltp", {})

        # Создаем SLTPConfig из настроек
        config = SLTPConfig()

        # Трейлинг стоп
        trailing_settings = sltp_settings.get("trailing_stop", {})
        if trailing_settings.get("enabled", False):
            config.trailing_stop = TrailingStopConfig(
                enabled=True,
                type=TrailingType(trailing_settings.get("type", "percentage")),
                step=trailing_settings.get("step", 0.5),
                min_profit=trailing_settings.get("min_profit", 0.3),
                max_distance=trailing_settings.get("max_distance", 2.0),
            )

        # Частичный TP
        partial_tp_settings = sltp_settings.get("partial_take_profit", {})
        if partial_tp_settings.get("enabled", False):
            config.partial_tp_enabled = True
            config.partial_tp_update_sl = partial_tp_settings.get(
                "update_sl_after_partial", True
            )
            levels = partial_tp_settings.get("levels", [])
            for i, level_data in enumerate(levels):
                level = PartialTPLevel(
                    level=i + 1,
                    price=0,  # Будет рассчитано позже
                    quantity=0,  # Будет рассчитано позже
                    percentage=level_data.get(
                        "percent", 0
                    ),  # Используем percent как в конфиге
                )
                # Добавляем close_ratio для совместимости с V2
                level.close_ratio = level_data.get("close_ratio", 0)
                config.partial_tp_levels.append(level)

        # Защита прибыли
        profit_protection = sltp_settings.get("profit_protection", {})
        if profit_protection.get("enabled", False):
            config.profit_protection.enabled = True
            config.profit_protection.breakeven_percent = profit_protection.get(
                "breakeven_percent", 1.0
            )
            config.profit_protection.breakeven_offset = profit_protection.get(
                "breakeven_offset", 0.2
            )
            config.profit_protection.lock_percent = profit_protection.get(
                "lock_percent", []
            )
            config.profit_protection.max_updates = profit_protection.get(
                "max_updates", 5
            )

        # Волатильность
        volatility = sltp_settings.get("volatility_adjustment", {})
        if volatility.get("enabled", False):
            config.volatility_adjustment = True
            config.volatility_multiplier = volatility.get("multiplier", 1.0)

        return config

    async def create_sltp_orders(
        self,
        position: Position,
        signal: Optional[Signal] = None,
        custom_config: Optional[SLTPConfig] = None,
    ) -> List[SLTPOrder]:
        """
        Создает SL/TP ордера для позиции.

        Args:
            position: Позиция для защиты
            signal: Торговый сигнал (опционально)
            custom_config: Пользовательская конфигурация

        Returns:
            Список созданных SL/TP ордеров
        """
        config = custom_config or self.config
        orders = []

        try:
            # Базовые SL/TP
            if config.stop_loss:
                sl_price = self._calculate_sl_price(
                    position.entry_price, position.side, config.stop_loss
                )
                sl_order = await self._create_stop_loss_order(position, sl_price)
                if sl_order:
                    orders.append(sl_order)

            if config.take_profit and not config.partial_tp_enabled:
                tp_price = self._calculate_tp_price(
                    position.entry_price, position.side, config.take_profit
                )
                tp_order = await self._create_take_profit_order(
                    position, tp_price, position.size
                )
                if tp_order:
                    orders.append(tp_order)

            # Частичные TP
            if config.partial_tp_enabled and config.partial_tp_levels:
                partial_orders = await self._create_partial_tp_orders(
                    position, config.partial_tp_levels
                )
                orders.extend(partial_orders)

            # Сохраняем ордера в кэш
            self._active_orders[position.id] = orders

            # Логируем историю
            for order in orders:
                self._add_history(
                    position.id,
                    "create",
                    order.order_type,
                    new_price=order.trigger_price,
                    reason="Initial SL/TP setup",
                )

            logger.info(
                f"Создано {len(orders)} SL/TP ордеров для позиции {position.id}"
            )

        except Exception as e:
            logger.error(f"Ошибка создания SL/TP ордеров: {e}")

        return orders

    async def update_trailing_stop(
        self, position: Position, current_price: float
    ) -> Optional[SLTPOrder]:
        """
        Обновляет трейлинг стоп.

        Args:
            position: Позиция
            current_price: Текущая цена

        Returns:
            Обновленный SL ордер или None
        """
        if not self.config.trailing_stop.enabled:
            return None

        # Проверяем минимальную прибыль
        profit_pct = self._calculate_profit_percentage(
            position.entry_price, current_price, position.side
        )

        if profit_pct < self.config.trailing_stop.min_profit:
            return None

        # Рассчитываем новый SL
        new_sl_price = self._calculate_trailing_stop_price(
            position, current_price, self.config.trailing_stop
        )

        # Получаем текущий SL
        current_sl = self._get_active_stop_loss(position.id)

        # Обновляем только если новый SL лучше
        if current_sl and self._is_better_stop_loss(
            current_sl.trigger_price, new_sl_price, position.side
        ):
            updated_order = await self._update_stop_loss_order(current_sl, new_sl_price)

            if updated_order:
                self._add_history(
                    position.id,
                    "update",
                    "trailing_stop",
                    old_price=current_sl.trigger_price,
                    new_price=new_sl_price,
                    reason=f"Trailing stop update (profit: {profit_pct:.2f}%)",
                )

                logger.info(
                    f"Обновлен trailing stop для {position.id}: "
                    f"{current_sl.trigger_price} -> {new_sl_price}"
                )

            return updated_order

        return None

    async def update_profit_protection(
        self, position: Position, current_price: float
    ) -> Optional[SLTPOrder]:
        """
        Обновляет защиту прибыли.

        Args:
            position: Позиция
            current_price: Текущая цена

        Returns:
            Обновленный SL ордер или None
        """
        if not self.config.profit_protection.enabled:
            return None

        profit_pct = self._calculate_profit_percentage(
            position.entry_price, current_price, position.side
        )

        # Получаем текущий SL
        current_sl = self._get_active_stop_loss(position.id)
        current_sl_price = current_sl.trigger_price if current_sl else 0.0

        new_sl = None

        # Проверяем уровни lock_percent (от большего к меньшему)
        if self.config.profit_protection.lock_percent:
            levels = sorted(
                self.config.profit_protection.lock_percent,
                key=lambda x: x["trigger"],
                reverse=True,
            )

            for level in levels:
                trigger = level["trigger"]
                lock = level["lock"]

                if profit_pct >= trigger:
                    logger.info(
                        f"Активирован уровень защиты: {trigger}% -> фиксация {lock}%"
                    )

                    # Рассчитываем новый SL на основе уровня фиксации
                    if position.side.upper() in ["BUY", "LONG"]:
                        lock_amount = (current_price - position.entry_price) * (
                            lock / profit_pct
                        )
                        new_sl = position.entry_price + lock_amount
                    else:  # SELL/SHORT
                        lock_amount = (position.entry_price - current_price) * (
                            lock / profit_pct
                        )
                        new_sl = position.entry_price - lock_amount

                    break

        # Проверяем условие безубытка, если не нашли уровень защиты
        if (
            new_sl is None
            and profit_pct >= self.config.profit_protection.breakeven_percent
        ):
            logger.info(f"Активирован безубыток (профит: {profit_pct:.2f}%)")

            offset = self.config.profit_protection.breakeven_offset / 100.0

            if position.side.upper() in ["BUY", "LONG"]:
                new_sl = position.entry_price * (1 + offset)
            else:  # SELL/SHORT
                new_sl = position.entry_price * (1 - offset)

        if new_sl is None:
            return None

        # Округляем цену защиты
        protection_price = round(
            new_sl, 6
        )  # Временно, потом заменим на правильное округление

        # Проверяем, улучшает ли новый SL текущий
        if current_sl and self._is_better_stop_loss(
            current_sl_price, protection_price, position.side
        ):
            updated_order = await self._update_stop_loss_order(
                current_sl, protection_price
            )

            if updated_order:
                self._add_history(
                    position.id,
                    "update",
                    "profit_protection",
                    old_price=current_sl_price,
                    new_price=protection_price,
                    reason=f"Profit protection at {profit_pct:.2f}%",
                )

            return updated_order

        return None

    async def check_partial_tp(
        self, position: Position, current_price: Optional[float] = None
    ) -> bool:
        """
        Проверяет и выполняет частичное закрытие позиции при достижении уровней TP.

        Args:
            position: Позиция для проверки
            current_price: Текущая цена (опционально)

        Returns:
            bool: True если было выполнено частичное закрытие
        """
        if not self.config.partial_tp_enabled or not self.config.partial_tp_levels:
            return False

        try:
            # Получаем текущую цену если не передана
            if not current_price:
                from exchanges.bybit.client import get_last_price

                current_price = get_last_price(position.symbol)

            if not current_price or current_price <= 0:
                logger.warning(f"Не удалось получить цену для {position.symbol}")
                return False

            # Рассчитываем текущий профит
            profit_percent = self._calculate_profit_percentage(
                position.entry_price, current_price, position.side
            )

            if profit_percent <= 0:
                return False

            # Получаем историю выполненных уровней
            executed_levels = []
            sltp_order = self._active_orders.get(position.id, [])
            for order in sltp_order:
                if hasattr(order, "extra_data") and order.extra_data:
                    executed = order.extra_data.get("partial_tp_executed", [])
                    executed_levels.extend(
                        [level.get("percent", 0) for level in executed]
                    )

            # Проверяем каждый уровень частичного TP
            for level_config in self.config.partial_tp_levels:
                level_percent = level_config.percentage  # percent из конфига

                # Проверяем, не был ли уровень уже выполнен
                if level_percent in executed_levels:
                    continue

                # Проверяем, достигнут ли уровень
                if profit_percent >= level_percent:
                    logger.info(
                        f"Достигнут уровень partial TP {level_percent}% "
                        f"для {position.symbol} (профит: {profit_percent:.2f}%)"
                    )

                    # Рассчитываем количество для закрытия
                    # Используем close_ratio из конфигурации (как в V2)
                    close_ratio = level_config.close_ratio
                    close_qty = position.size * close_ratio

                    # Создаем запись в истории
                    history_entry = {
                        "trade_id": position.id,
                        "level": level_config.level,
                        "percent": level_percent,
                        "close_ratio": close_ratio,
                        "close_qty": close_qty,
                        "price": current_price,
                        "status": "pending",
                    }

                    history_id = self._create_partial_tp_history(history_entry)

                    # Создаем ордер для частичного закрытия
                    if self.exchange_client:
                        try:
                            # Определяем сторону закрытия
                            close_side = "Sell" if position.side == "Buy" else "Buy"

                            # Округляем количество
                            from exchanges.bybit.utils import round_qty

                            close_qty = round_qty(position.symbol, close_qty)

                            # Создаем reduce-only ордер
                            response = await self.exchange_client.create_order(
                                {
                                    "symbol": position.symbol,
                                    "side": close_side,
                                    "order_type": "Market",
                                    "qty": close_qty,
                                    "reduce_only": True,
                                    "position_idx": self._get_position_idx(
                                        position.side
                                    ),
                                }
                            )

                            if response.success:
                                order_id = response.order_id
                                logger.info(
                                    f"Создан ордер частичного закрытия: {order_id} "
                                    f"для {close_qty} {position.symbol}"
                                )

                                # Обновляем историю
                                history_entry["id"] = history_id
                                history_entry["order_id"] = order_id
                                history_entry["status"] = "executed"
                                self._update_partial_tp_history(history_entry)

                                # Обновляем информацию о выполненных уровнях
                                self._add_history(
                                    position.id,
                                    "trigger",
                                    "partial_tp",
                                    reason=f"Partial TP level {level_percent}% executed",
                                )

                                # Обновляем SL если нужно
                                if self.config.partial_tp_update_sl:
                                    await self._update_sl_after_partial_tp(position)

                                return True
                            else:
                                # Обновляем историю с ошибкой
                                history_entry["id"] = history_id
                                history_entry["status"] = "error"
                                history_entry["error"] = response.error
                                self._update_partial_tp_history(history_entry)

                        except Exception as e:
                            logger.error(f"Ошибка создания частичного TP: {e}")
                            if history_id:
                                history_entry["id"] = history_id
                                history_entry["status"] = "error"
                                history_entry["error"] = str(e)
                                self._update_partial_tp_history(history_entry)

        except Exception as e:
            logger.error(f"Ошибка проверки partial TP: {e}")

        return False

    async def _update_sl_after_partial_tp(self, position: Position) -> bool:
        """Обновляет SL после частичного закрытия позиции"""
        try:
            # Устанавливаем SL в безубыток с небольшим смещением
            offset = 0.001  # 0.1%

            if position.side == "Buy":
                new_sl = position.entry_price * (1 + offset)
            else:
                new_sl = position.entry_price * (1 - offset)

            # Округляем цену
            from exchanges.bybit.utils import round_price

            new_sl = round_price(position.symbol, new_sl)

            # Обновляем SL
            response = await self.exchange_client.set_stop_loss(
                position.symbol, new_sl, position.size
            )

            if response.success:
                logger.info(f"SL обновлен в безубыток после partial TP: {new_sl}")
                self._add_history(
                    position.id,
                    "update",
                    "stop_loss",
                    new_price=new_sl,
                    reason="SL to breakeven after partial TP",
                )
                return True

        except Exception as e:
            logger.error(f"Ошибка обновления SL после partial TP: {e}")

        return False

    async def process_partial_tp_fill(
        self, position: Position, filled_order: Order
    ) -> Optional[List[SLTPOrder]]:
        """
        Обрабатывает частичное закрытие TP.

        Args:
            position: Позиция
            filled_order: Исполненный TP ордер

        Returns:
            Обновленные SL/TP ордера
        """
        updated_orders = []

        try:
            # Находим соответствующий уровень
            level_index = None
            for i, level in enumerate(self.config.partial_tp_levels):
                if level.order_id == filled_order.id:
                    level_index = i
                    level.filled = True
                    level.filled_at = datetime.now()
                    break

            if level_index is None:
                return None

            # Обновляем количество в оставшихся ордерах
            remaining_quantity = position.size - filled_order.filled_quantity

            # Обновляем SL для оставшейся позиции
            current_sl = self._get_active_stop_loss(position.id)
            if current_sl:
                updated_sl = await self._update_sl_quantity(
                    current_sl, remaining_quantity
                )
                if updated_sl:
                    updated_orders.append(updated_sl)

            # Обновляем оставшиеся TP
            for i in range(level_index + 1, len(self.config.partial_tp_levels)):
                level = self.config.partial_tp_levels[i]
                if not level.filled and level.order_id:
                    tp_order = self._get_order_by_id(level.order_id)
                    if tp_order:
                        updated_tp = await self._update_tp_quantity(
                            tp_order, remaining_quantity
                        )
                        if updated_tp:
                            updated_orders.append(updated_tp)

            self._add_history(
                position.id,
                "trigger",
                "partial_tp",
                reason=f"Partial TP level {level_index + 1} filled",
            )

            logger.info(
                f"Обработано частичное закрытие TP уровня "
                f"{level_index + 1} для позиции {position.id}"
            )

        except Exception as e:
            logger.error(f"Ошибка обработки частичного TP: {e}")

        return updated_orders if updated_orders else None

    async def cancel_all_orders(self, position_id: str) -> bool:
        """
        Отменяет все SL/TP ордера для позиции.

        Args:
            position_id: ID позиции

        Returns:
            Успешность отмены
        """
        orders = self._active_orders.get(position_id, [])
        success = True

        for order in orders:
            try:
                if order.status in [SLTPStatus.PENDING, SLTPStatus.ACTIVE]:
                    await self._cancel_order(order)
                    order.status = SLTPStatus.CANCELLED

                    self._add_history(
                        position_id,
                        "cancel",
                        order.order_type,
                        old_price=order.trigger_price,
                        reason="Position closed",
                    )
            except Exception as e:
                logger.error(f"Ошибка отмены ордера {order.id}: {e}")
                success = False

        # Очищаем кэш
        if position_id in self._active_orders:
            del self._active_orders[position_id]

        return success

    # Вспомогательные методы

    def _calculate_sl_price(
        self, entry_price: float, side: str, sl_percent: float
    ) -> float:
        """Рассчитывает цену стоп-лосс"""
        if side.upper() in ["BUY", "LONG"]:
            return entry_price * (1 - sl_percent / 100)
        else:
            return entry_price * (1 + sl_percent / 100)

    def _calculate_tp_price(
        self, entry_price: float, side: str, tp_percent: float
    ) -> float:
        """Рассчитывает цену тейк-профит"""
        if side.upper() in ["BUY", "LONG"]:
            return entry_price * (1 + tp_percent / 100)
        else:
            return entry_price * (1 - tp_percent / 100)

    def _calculate_profit_percentage(
        self, entry_price: float, current_price: float, side: str
    ) -> float:
        """Рассчитывает процент прибыли"""
        if side.upper() in ["BUY", "LONG"]:
            return ((current_price - entry_price) / entry_price) * 100
        else:
            return ((entry_price - current_price) / entry_price) * 100

    def _calculate_trailing_stop_price(
        self, position: Position, current_price: float, config: TrailingStopConfig
    ) -> float:
        """Рассчитывает цену trailing stop"""
        if config.type == TrailingType.PERCENTAGE:
            distance = current_price * (config.step / 100)
        elif config.type == TrailingType.FIXED:
            distance = config.step
        else:
            # ATR или адаптивный - требует дополнительных данных
            distance = current_price * (config.step / 100)

        if position.side.upper() in ["BUY", "LONG"]:
            return current_price - distance
        else:
            return current_price + distance

    def _calculate_protection_price(
        self, entry_price: float, side: str, protection_percent: float
    ) -> float:
        """Рассчитывает цену защиты прибыли"""
        if side.upper() in ["BUY", "LONG"]:
            return entry_price * (1 + protection_percent / 100)
        else:
            return entry_price * (1 - protection_percent / 100)

    def _is_better_stop_loss(self, current_sl: float, new_sl: float, side: str) -> bool:
        """Проверяет, лучше ли новый SL"""
        if side.upper() in ["BUY", "LONG"]:
            return new_sl > current_sl
        else:
            return new_sl < current_sl

    def _get_active_stop_loss(self, position_id: str) -> Optional[SLTPOrder]:
        """Получает активный SL ордер"""
        orders = self._active_orders.get(position_id, [])
        for order in orders:
            if order.order_type == "StopLoss" and order.status in [
                SLTPStatus.PENDING,
                SLTPStatus.ACTIVE,
            ]:
                return order
        return None

    def _get_order_by_id(self, order_id: str) -> Optional[SLTPOrder]:
        """Получает ордер по ID"""
        for orders in self._active_orders.values():
            for order in orders:
                if order.id == order_id:
                    return order
        return None

    def _add_history(
        self,
        position_id: str,
        action: str,
        order_type: str,
        old_price: Optional[float] = None,
        new_price: Optional[float] = None,
        reason: Optional[str] = None,
    ):
        """Добавляет запись в историю"""
        history = SLTPHistory(
            id=f"{position_id}_{datetime.now().timestamp()}",
            position_id=position_id,
            action=action,
            order_type=order_type,
            old_price=old_price,
            new_price=new_price,
            reason=reason,
        )
        self._history.append(history)

        # Ограничиваем размер истории
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    # Методы для работы с биржей

    async def _create_stop_loss_order(
        self, position: Position, sl_price: float
    ) -> Optional[SLTPOrder]:
        """Создает SL ордер на бирже"""
        if not self.exchange_client:
            logger.warning("Нет клиента биржи для создания SL")
            return None

        try:
            response = await self.exchange_client.set_stop_loss(
                position.symbol, sl_price, position.size
            )

            if response.success:
                order = SLTPOrder(
                    id=response.order_id or f"sl_{position.id}",
                    symbol=position.symbol,
                    side="Sell" if position.side == "Buy" else "Buy",
                    order_type="StopLoss",
                    trigger_price=sl_price,
                    quantity=position.size,
                    status=SLTPStatus.ACTIVE,
                    position_id=position.id,
                    exchange_order_id=response.order_id,
                )
                return order

        except Exception as e:
            logger.error(f"Ошибка создания SL: {e}")

        return None

    async def _create_take_profit_order(
        self, position: Position, tp_price: float, quantity: float
    ) -> Optional[SLTPOrder]:
        """Создает TP ордер на бирже"""
        if not self.exchange_client:
            logger.warning("Нет клиента биржи для создания TP")
            return None

        try:
            response = await self.exchange_client.set_take_profit(
                position.symbol, tp_price, quantity
            )

            if response.success:
                order = SLTPOrder(
                    id=response.order_id or f"tp_{position.id}",
                    symbol=position.symbol,
                    side="Sell" if position.side == "Buy" else "Buy",
                    order_type="TakeProfit",
                    trigger_price=tp_price,
                    quantity=quantity,
                    status=SLTPStatus.ACTIVE,
                    position_id=position.id,
                    exchange_order_id=response.order_id,
                )
                return order

        except Exception as e:
            logger.error(f"Ошибка создания TP: {e}")

        return None

    async def _create_partial_tp_orders(
        self, position: Position, levels: List[PartialTPLevel]
    ) -> List[SLTPOrder]:
        """Создает частичные TP ордера"""
        orders = []
        total_quantity = position.size

        for level in levels:
            # Рассчитываем количество
            level.quantity = total_quantity * (level.percentage / 100)

            # Рассчитываем цену TP
            tp_percent = self.config.take_profit * (level.level * 0.3 + 0.7)
            level.price = self._calculate_tp_price(
                position.entry_price, position.side, tp_percent
            )

            # Создаем ордер
            order = await self._create_take_profit_order(
                position, level.price, level.quantity
            )

            if order:
                order.level = level.level
                level.order_id = order.id
                orders.append(order)

        return orders

    async def _update_stop_loss_order(
        self, order: SLTPOrder, new_price: float
    ) -> Optional[SLTPOrder]:
        """Обновляет SL ордер"""
        if not self.exchange_client:
            return None

        try:
            # Отменяем старый и создаем новый
            await self._cancel_order(order)

            # Создаем новый ордер с новой ценой
            position = Position(
                id=order.position_id,
                symbol=order.symbol,
                side="Buy" if order.side == "Sell" else "Sell",
                size=order.quantity,
                entry_price=0,  # Не используется
            )

            new_order = await self._create_stop_loss_order(position, new_price)
            if new_order:
                new_order.position_id = order.position_id

                # Обновляем в кэше
                orders = self._active_orders.get(order.position_id, [])
                for i, o in enumerate(orders):
                    if o.id == order.id:
                        orders[i] = new_order
                        break

            return new_order

        except Exception as e:
            logger.error(f"Ошибка обновления SL: {e}")
            return None

    async def _update_sl_quantity(
        self, order: SLTPOrder, new_quantity: float
    ) -> Optional[SLTPOrder]:
        """Обновляет количество в SL ордере"""
        # Аналогично _update_stop_loss_order, но с той же ценой
        order.quantity = new_quantity
        return await self._update_stop_loss_order(order, order.trigger_price)

    async def _update_tp_quantity(
        self, order: SLTPOrder, new_quantity: float
    ) -> Optional[SLTPOrder]:
        """Обновляет количество в TP ордере"""
        # Пересчитываем количество для уровня
        if order.level:
            level = self.config.partial_tp_levels[order.level - 1]
            order.quantity = new_quantity * (level.percentage / 100)
        else:
            order.quantity = new_quantity

        # Пересоздаем ордер
        await self._cancel_order(order)

        position = Position(
            id=order.position_id,
            symbol=order.symbol,
            side="Buy" if order.side == "Sell" else "Sell",
            size=order.quantity,
            entry_price=0,
        )

        new_order = await self._create_take_profit_order(
            position, order.trigger_price, order.quantity
        )

        if new_order and order.level:
            new_order.level = order.level

        return new_order

    async def _cancel_order(self, order: SLTPOrder) -> bool:
        """Отменяет ордер на бирже"""
        if not self.exchange_client or not order.exchange_order_id:
            return False

        try:
            response = await self.exchange_client.cancel_order(
                order.symbol, order.exchange_order_id
            )
            return response.success
        except Exception as e:
            logger.error(f"Ошибка отмены ордера: {e}")
            return False

    def get_history(self, position_id: Optional[str] = None) -> List[SLTPHistory]:
        """Получает историю изменений"""
        if position_id:
            return [h for h in self._history if h.position_id == position_id]
        return self._history.copy()

    def get_active_orders(
        self, position_id: Optional[str] = None
    ) -> Dict[str, List[SLTPOrder]]:
        """Получает активные ордера"""
        if position_id:
            return {position_id: self._active_orders.get(position_id, [])}
        return self._active_orders.copy()

    # Методы для работы с partial_tp_history
    def _create_partial_tp_history(
        self, history_entry: Dict[str, Any]
    ) -> Optional[int]:
        """Создает запись в таблице partial_tp_history"""
        try:
            from database.connections.postgres import get_db_connection

            query = """
                INSERT INTO partial_tp_history
                (trade_id, level, percent, close_ratio, close_qty, price, order_id, status, error, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        query,
                        (
                            history_entry.get("trade_id"),
                            history_entry.get("level"),
                            history_entry.get("percent"),
                            history_entry.get("close_ratio"),
                            history_entry.get("close_qty"),
                            history_entry.get("price"),
                            history_entry.get("order_id"),
                            history_entry.get("status", "pending"),
                            history_entry.get("error"),
                        ),
                    )
                    result = cur.fetchone()
                    conn.commit()
                    return result[0] if result else None

        except Exception as e:
            logger.error(f"Ошибка создания записи partial_tp_history: {e}")
            return None

    def _update_partial_tp_history(self, history_entry: Dict[str, Any]) -> bool:
        """Обновляет запись в таблице partial_tp_history"""
        try:
            from database.connections.postgres import get_db_connection

            if "id" not in history_entry:
                logger.error("Нет ID для обновления partial_tp_history")
                return False

            query = """
                UPDATE partial_tp_history
                SET status = %s, order_id = %s, error = %s, close_qty = %s, updated_at = NOW()
                WHERE id = %s
            """

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        query,
                        (
                            history_entry.get("status"),
                            history_entry.get("order_id"),
                            history_entry.get("error"),
                            history_entry.get("close_qty"),
                            history_entry.get("id"),
                        ),
                    )
                    conn.commit()
                    return cur.rowcount > 0

        except Exception as e:
            logger.error(f"Ошибка обновления partial_tp_history: {e}")
            return False

    def _get_position_idx(self, side: str) -> int:
        """Определяет правильный positionIdx для hedge/one-way режима"""
        try:
            system_config = self.config_manager.get_system_config()
            trading_config = system_config.get("trading", {})
            hedge_mode = trading_config.get("hedge_mode", True)

            if hedge_mode:
                # В hedge режиме: 1=Long/Buy, 2=Short/Sell
                return 1 if side.upper() in ["BUY", "LONG"] else 2
            else:
                # В one-way режиме: всегда 0
                return 0
        except Exception as e:
            logger.error(f"Ошибка определения positionIdx: {e}")
            return 0
