#!/usr/bin/env python3
"""
Enhanced SL/TP Manager для BOT Trading v3

Улучшенный менеджер стоп-лосс и тейк-профит ордеров.
Адаптирован из v2 для асинхронной архитектуры v3.
"""

from datetime import datetime
from typing import Any

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.models import Order
from database.models.signal import Signal
from exchanges.base.models import Position

# Импортируем утилиты из нового модуля
try:
    from .utils import calculate_pnl_percentage, normalize_percentage, round_price, round_qty
except ImportError:
    # Fallback если модуль utils еще не импортирован
    def round_qty(symbol: str, qty: float) -> float:
        """Округляет количество согласно правилам символа"""
        return round(qty, 3)

    def round_price(symbol: str, price: float) -> float:
        """Округляет цену согласно правилам символа"""
        return round(price, 4)

    def normalize_percentage(value: float) -> float:
        """Нормализация процентов"""
        if value < 0.1:
            return value * 100
        return value


# Добавим недостающие функции из V2
def get_last_price(symbol: str) -> float | None:
    """Получает последнюю цену для символа"""
    try:
        # Заглушка - в реальной системе будет запрос к бирже
        logger.warning(f"get_last_price не реализован для {symbol}")
        return None
    except Exception as e:
        logger.error(f"Ошибка получения цены для {symbol}: {e}")
        return None


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


class PositionAdapter:
    """Адаптер для унификации работы с различными типами Position"""

    def __init__(self, position):
        self._position = position

    @property
    def id(self) -> str:
        """Получить ID позиции"""
        if hasattr(self._position, "id"):
            return str(self._position.id) if self._position.id else ""
        # Если нет id, создаем из symbol и side
        if hasattr(self._position, "symbol") and hasattr(self._position, "side"):
            return f"{self._position.symbol}_{self._position.side}"
        return ""

    @property
    def symbol(self) -> str:
        """Получить символ"""
        return getattr(self._position, "symbol", "")

    @property
    def side(self) -> str:
        """Получить сторону позиции"""
        return getattr(self._position, "side", "")

    @property
    def size(self) -> float:
        """Получить размер позиции"""
        # Пробуем разные атрибуты для размера
        for attr in ["size", "quantity", "qty"]:
            if hasattr(self._position, attr):
                val = getattr(self._position, attr)
                # Проверяем что атрибут не None
                if val is not None:
                    return float(val)
        return 0.0

    @property
    def entry_price(self) -> float:
        """Получить цену входа"""
        # Пробуем разные атрибуты для цены входа
        for attr in ["entry_price", "average_price", "avg_price"]:
            if hasattr(self._position, attr):
                val = getattr(self._position, attr)
                if val is not None:
                    return float(val)
        return 0.0

    def __getattr__(self, name):
        """Прокси для доступа к другим атрибутам"""
        return getattr(self._position, name)


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
        self._active_orders: dict[str, list[SLTPOrder]] = {}

        # История изменений
        self._history: list[SLTPHistory] = []

        logger.info("Успешно инициализирован EnhancedSLTPManager")

        # Добавим дополнительные настройки из V2
        self.max_sltp_attempts = 3  # Максимальное количество попыток установки SL/TP
        self._creation_lock = {}  # Блокировки для создания ордеров по позициям

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
            config.partial_tp_update_sl = partial_tp_settings.get("update_sl_after_partial", True)
            levels = partial_tp_settings.get("levels", [])
            for i, level_data in enumerate(levels):
                level = PartialTPLevel(
                    level=i + 1,
                    price=0,  # Будет рассчитано позже
                    quantity=0,  # Будет рассчитано позже
                    percentage=level_data.get("percent", 0),  # Используем percent как в конфиге
                )
                # Нормализуем проценты (конвертируем 0.012 в 1.2)
                level.percentage = normalize_percentage(level.percentage)
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
            config.profit_protection.lock_percent = profit_protection.get("lock_percent", [])
            config.profit_protection.max_updates = profit_protection.get("max_updates", 5)

        # Волатильность
        volatility = sltp_settings.get("volatility_adjustment", {})
        if volatility.get("enabled", False):
            config.volatility_adjustment = True
            config.volatility_multiplier = volatility.get("multiplier", 1.0)

        return config

    async def create_sltp_orders(
        self,
        position,  # Union[Position, TradingPosition, любой объект с атрибутами позиции]
        signal: Signal | None = None,
        custom_config: SLTPConfig | None = None,
    ) -> list[SLTPOrder]:
        """
        Создает SL/TP ордера для позиции.

        Args:
            position: Позиция для защиты
            signal: Торговый сигнал (опционально)
            custom_config: Пользовательская конфигурация

        Returns:
            Список созданных SL/TP ордеров
        """
        # Используем адаптер для унификации работы с позицией
        position = PositionAdapter(position)
        config = custom_config or self.config
        orders = []

        try:
            # Базовые SL/TP
            if config.stop_loss and config.stop_loss > 0:
                # Проверяем, передана ли абсолютная цена или процент
                if config.stop_loss > 1:  # Вероятно абсолютная цена
                    sl_price = config.stop_loss
                else:  # Процент
                    sl_price = self._calculate_sl_price(
                        position.entry_price, position.side, config.stop_loss * 100
                    )
                sl_order = await self._create_stop_loss_order(position, sl_price)
                if sl_order:
                    orders.append(sl_order)

            if config.take_profit and config.take_profit > 0 and not config.partial_tp_enabled:
                # Проверяем, передана ли абсолютная цена или процент
                if config.take_profit > 1:  # Вероятно абсолютная цена
                    tp_price = config.take_profit
                else:  # Процент
                    tp_price = self._calculate_tp_price(
                        position.entry_price, position.side, config.take_profit * 100
                    )
                tp_order = await self._create_take_profit_order(position, tp_price, position.size)
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

            logger.info(f"Создано {len(orders)} SL/TP ордеров для позиции {position.id}")

        except Exception as e:
            logger.error(f"Ошибка создания SL/TP ордеров: {e}")

        return orders

    async def update_trailing_stop(self, position, current_price: float) -> SLTPOrder | None:
        """
        Обновляет трейлинг стоп.

        Args:
            position: Позиция
            current_price: Текущая цена

        Returns:
            Обновленный SL ордер или None
        """
        position = PositionAdapter(position)

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

    async def update_profit_protection(self, position, current_price: float) -> SLTPOrder | None:
        """
        Обновляет защиту прибыли.

        Args:
            position: Позиция
            current_price: Текущая цена

        Returns:
            Обновленный SL ордер или None
        """
        position = PositionAdapter(position)

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
                    logger.info(f"Активирован уровень защиты: {trigger}% -> фиксация {lock}%")

                    # Рассчитываем новый SL на основе уровня фиксации
                    if position.side.upper() in ["BUY", "LONG"]:
                        lock_amount = (current_price - position.entry_price) * (lock / profit_pct)
                        new_sl = position.entry_price + lock_amount
                    else:  # SELL/SHORT
                        lock_amount = (position.entry_price - current_price) * (lock / profit_pct)
                        new_sl = position.entry_price - lock_amount

                    break

        # Проверяем условие безубытка, если не нашли уровень защиты
        if new_sl is None and profit_pct >= self.config.profit_protection.breakeven_percent:
            logger.info(f"Активирован безубыток (профит: {profit_pct:.2f}%)")

            offset = self.config.profit_protection.breakeven_offset / 100.0

            if position.side.upper() in ["BUY", "LONG"]:
                new_sl = position.entry_price * (1 + offset)
            else:  # SELL/SHORT
                new_sl = position.entry_price * (1 - offset)

        if new_sl is None:
            return None

        # Округляем цену защиты
        protection_price = round(new_sl, 6)  # Временно, потом заменим на правильное округление

        # Проверяем, улучшает ли новый SL текущий
        if current_sl and self._is_better_stop_loss(
            current_sl_price, protection_price, position.side
        ):
            updated_order = await self._update_stop_loss_order(current_sl, protection_price)

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

    async def check_partial_tp(self, position, current_price: float | None = None) -> bool:
        """
        Проверяет и выполняет частичное закрытие позиции при достижении уровней TP.

        Args:
            position: Позиция для проверки
            current_price: Текущая цена (опционально)

        Returns:
            bool: True если было выполнено частичное закрытие
        """
        position = PositionAdapter(position)

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
                    executed_levels.extend([level.get("percent", 0) for level in executed])

            # Проверяем каждый уровень частичного TP
            for level_config in self.config.partial_tp_levels:
                # Нормализуем процент на случай если в конфиге указано как доля (0.01 = 1%)
                level_percent = normalize_percentage(level_config.percentage)

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

                            # Округляем количество с помощью локальной функции
                            close_qty = round_qty(position.symbol, close_qty)

                            # Создаем reduce-only ордер
                            response = await self.exchange_client.create_order(
                                {
                                    "symbol": position.symbol,
                                    "side": close_side,
                                    "order_type": "Market",
                                    "qty": close_qty,
                                    "reduce_only": True,
                                    "position_idx": self._get_position_idx(position.side),
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

                                # Сохраняем информацию о выполненном уровне
                                for order in self._active_orders.get(position.id, []):
                                    if not hasattr(order, "extra_data"):
                                        order.extra_data = {}
                                    if "partial_tp_executed" not in order.extra_data:
                                        order.extra_data["partial_tp_executed"] = []
                                    order.extra_data["partial_tp_executed"].append(
                                        {
                                            "percent": level_percent,
                                            "qty": close_qty,
                                            "price": current_price,
                                            "timestamp": datetime.now().isoformat(),
                                        }
                                    )

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

    async def _update_sl_after_partial_tp(self, position) -> bool:
        """Обновляет SL после частичного закрытия позиции"""
        position = PositionAdapter(position)

        try:
            # Проверяем наличие exchange_client
            if not self.exchange_client:
                logger.warning("Нет exchange_client для обновления SL")
                return False

            # Устанавливаем SL в безубыток с небольшим смещением
            offset = 0.001  # 0.1%

            if position.side.upper() in ["BUY", "LONG"]:
                new_sl = position.entry_price * (1 + offset)
            else:
                new_sl = position.entry_price * (1 - offset)

            # Округляем цену с помощью локальной функции
            new_sl = round_price(position.symbol, new_sl)

            # Обновляем SL через создание ордера стоп-лосс
            # Определяем position_idx
            position_idx = self._get_position_idx(position.side)

            response = await self.exchange_client.create_order(
                {
                    "symbol": position.symbol,
                    "side": "Sell" if position.side.upper() in ["BUY", "LONG"] else "Buy",
                    "order_type": "Market",
                    "qty": position.size,  # Используем оставшееся количество
                    "trigger_price": new_sl,
                    "trigger_by": "LastPrice",
                    "order_link_id": f"SL_{position.symbol}_{datetime.now().timestamp()}",
                    "position_idx": position_idx,
                    "reduce_only": True,
                }
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
        self, position, filled_order: Order
    ) -> list[SLTPOrder] | None:
        """
        Обрабатывает частичное закрытие TP.

        Args:
            position: Позиция
            filled_order: Исполненный TP ордер

        Returns:
            Обновленные SL/TP ордера
        """
        position = PositionAdapter(position)
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
                updated_sl = await self._update_sl_quantity(current_sl, remaining_quantity)
                if updated_sl:
                    updated_orders.append(updated_sl)

            # Обновляем оставшиеся TP
            for i in range(level_index + 1, len(self.config.partial_tp_levels)):
                level = self.config.partial_tp_levels[i]
                if not level.filled and level.order_id:
                    tp_order = self._get_order_by_id(level.order_id)
                    if tp_order:
                        updated_tp = await self._update_tp_quantity(tp_order, remaining_quantity)
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

    async def register_sltp_orders(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        trade_qty: float | None = None,
    ) -> dict[str, Any]:
        """
        Регистрирует SL/TP ордера для сделки (совместимость с V2).

        Args:
            trade_id: ID сделки
            symbol: Символ торговой пары
            side: Сторона сделки (BUY/SELL)
            entry_price: Цена входа
            stop_loss: Цена стоп-лосс
            take_profit: Цена тейк-профит
            trade_qty: Количество в сделке

        Returns:
            Dict[str, Any]: Результат регистрации SL/TP ордеров
        """
        logger.info(
            f"[register_sltp_orders] => Регистрация SL/TP для trade_id={trade_id}, "
            f"symbol={symbol}, side={side}, entry_price={entry_price}"
        )

        # Создаем временную позицию для использования существующей логики
        temp_position = Position(
            symbol=symbol,
            side=side,
            size=trade_qty or 1.0,
            entry_price=entry_price,
            mark_price=entry_price,
        )

        # Создаем конфигурацию
        config = SLTPConfig(stop_loss=stop_loss, take_profit=take_profit)

        try:
            orders = await self.create_sltp_orders(temp_position, None, config)

            result = {
                "success": len(orders) > 0,
                "message": f"Создано {len(orders)} SL/TP ордеров",
                "sl_order_id": None,
                "tp_order_id": None,
            }

            # Извлекаем ID ордеров
            for order in orders:
                if order.order_type == "StopLoss":
                    result["sl_order_id"] = order.exchange_order_id
                elif order.order_type == "TakeProfit":
                    result["tp_order_id"] = order.exchange_order_id

            return result

        except Exception as e:
            logger.error(f"[register_sltp_orders] => Ошибка: {e}")
            return {
                "success": False,
                "message": f"Ошибка: {e!s}",
                "sl_order_id": None,
                "tp_order_id": None,
            }

    async def check_and_fix_sltp(self, trade_id: str) -> dict[str, Any]:
        """
        Проверяет и исправляет SL/TP ордера для сделки (совместимость с V2).

        Args:
            trade_id: ID сделки

        Returns:
            Dict[str, Any]: Результат проверки и исправления
        """
        logger.info(f"[check_and_fix_sltp] => Проверка SL/TP для trade_id={trade_id}")

        try:
            # Получаем активные ордера для позиции
            orders = self._active_orders.get(trade_id, [])

            if not orders:
                return {
                    "success": False,
                    "message": "Нет активных SL/TP ордеров",
                    "fixed": False,
                }

            # Проверяем статус ордеров (заглушка - в реальной системе проверяется через exchange_client)
            active_orders = [
                o for o in orders if o.status in [SLTPStatus.PENDING, SLTPStatus.ACTIVE]
            ]

            return {
                "success": True,
                "message": f"Найдено {len(active_orders)} активных SL/TP ордеров",
                "fixed": False,
                "orders_count": len(active_orders),
            }

        except Exception as e:
            logger.error(f"[check_and_fix_sltp] => Ошибка: {e}")
            return {"success": False, "message": f"Ошибка: {e!s}", "fixed": False}

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

    def _calculate_sl_price(self, entry_price: float, side: str, sl_percent: float) -> float:
        """Рассчитывает цену стоп-лосс"""
        if side.upper() in ["BUY", "LONG"]:
            return entry_price * (1 - sl_percent / 100)
        else:
            return entry_price * (1 + sl_percent / 100)

    def _calculate_tp_price(self, entry_price: float, side: str, tp_percent: float) -> float:
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
        self, position, current_price: float, config: TrailingStopConfig
    ) -> float:
        """Рассчитывает цену trailing stop"""
        position = PositionAdapter(position)

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

    def _get_active_stop_loss(self, position_id: str) -> SLTPOrder | None:
        """Получает активный SL ордер"""
        orders = self._active_orders.get(position_id, [])
        for order in orders:
            if order.order_type == "StopLoss" and order.status in [
                SLTPStatus.PENDING,
                SLTPStatus.ACTIVE,
            ]:
                return order
        return None

    def _get_order_by_id(self, order_id: str) -> SLTPOrder | None:
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
        old_price: float | None = None,
        new_price: float | None = None,
        reason: str | None = None,
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

    async def _create_stop_loss_order(self, position, sl_price: float) -> SLTPOrder | None:
        """Создает SL ордер на бирже"""
        position = PositionAdapter(position)

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
        self, position, tp_price: float, quantity: float
    ) -> SLTPOrder | None:
        """Создает TP ордер на бирже"""
        position = PositionAdapter(position)

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
        self, position, levels: list[PartialTPLevel]
    ) -> list[SLTPOrder]:
        """Создает частичные TP ордера"""
        position = PositionAdapter(position)
        orders = []
        total_quantity = position.size

        for level in levels:
            # Рассчитываем количество
            level.quantity = total_quantity * (level.percentage / 100)

            # Рассчитываем цену TP
            tp_percent = self.config.take_profit * (level.level * 0.3 + 0.7)
            level.price = self._calculate_tp_price(position.entry_price, position.side, tp_percent)

            # Создаем ордер
            order = await self._create_take_profit_order(position, level.price, level.quantity)

            if order:
                order.level = level.level
                level.order_id = order.id
                orders.append(order)

        return orders

    async def _update_stop_loss_order(self, order: SLTPOrder, new_price: float) -> SLTPOrder | None:
        """Обновляет SL ордер"""
        if not self.exchange_client:
            return None

        try:
            # Отменяем старый и создаем новый
            await self._cancel_order(order)

            # Создаем временный объект позиции для создания нового ордера
            temp_position = Position(
                symbol=order.symbol,
                side="Buy" if order.side == "Sell" else "Sell",
                size=order.quantity,
                entry_price=0.0,  # Не используется для SL
                mark_price=0.0,  # Требуется для модели
            )
            # Добавляем id если доступен
            if hasattr(temp_position, "id"):
                temp_position.id = order.position_id

            new_order = await self._create_stop_loss_order(temp_position, new_price)
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

    async def _update_sl_quantity(self, order: SLTPOrder, new_quantity: float) -> SLTPOrder | None:
        """Обновляет количество в SL ордере"""
        # Аналогично _update_stop_loss_order, но с той же ценой
        order.quantity = new_quantity
        return await self._update_stop_loss_order(order, order.trigger_price)

    async def _update_tp_quantity(self, order: SLTPOrder, new_quantity: float) -> SLTPOrder | None:
        """Обновляет количество в TP ордере"""
        # Пересчитываем количество для уровня
        if order.level:
            level = self.config.partial_tp_levels[order.level - 1]
            order.quantity = new_quantity * (level.percentage / 100)
        else:
            order.quantity = new_quantity

        # Пересоздаем ордер
        await self._cancel_order(order)

        temp_position = Position(
            symbol=order.symbol,
            side="Buy" if order.side == "Sell" else "Sell",
            size=order.quantity,
            entry_price=0.0,
            mark_price=0.0,
        )
        # Добавляем id если доступен
        if hasattr(temp_position, "id"):
            temp_position.id = order.position_id

        new_order = await self._create_take_profit_order(
            temp_position, order.trigger_price, order.quantity
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

    def get_history(self, position_id: str | None = None) -> list[SLTPHistory]:
        """Получает историю изменений"""
        if position_id:
            return [h for h in self._history if h.position_id == position_id]
        return self._history.copy()

    def get_active_orders(self, position_id: str | None = None) -> dict[str, list[SLTPOrder]]:
        """Получает активные ордера"""
        if position_id:
            return {position_id: self._active_orders.get(position_id, [])}
        return self._active_orders.copy()

    # Методы для работы с partial_tp_history
    def _create_partial_tp_history(self, history_entry: dict[str, Any]) -> int | None:
        """Создает запись в таблице partial_tp_history"""
        try:
            # Пока что заглушка - в реальной системе будет работать с БД
            logger.info(f"Создание partial_tp_history записи: {history_entry}")
            return 1  # Возвращаем фейковый ID

        except Exception as e:
            logger.error(f"Ошибка создания записи partial_tp_history: {e}")
            return None

    def _update_partial_tp_history(self, history_entry: dict[str, Any]) -> bool:
        """Обновляет запись в таблице partial_tp_history"""
        try:
            # Пока что заглушка - в реальной системе будет работать с БД
            logger.info(f"Обновление partial_tp_history записи: {history_entry}")
            return True

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
