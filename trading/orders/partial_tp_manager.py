#!/usr/bin/env python3
"""
Менеджер частичного закрытия позиций (Partial Take Profit)

Портирован из BOT_AI_V2 для обеспечения частичной фиксации прибыли.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from database.models.base_models import OrderSide, OrderType


class PartialTPManager:
    """
    Менеджер частичного закрытия позиций

    Обеспечивает:
    - Многоуровневое частичное закрытие
    - Защиту прибыли через трейлинг стоп
    - Адаптивное управление уровнями TP
    """

    def __init__(self, exchange_registry, logger: logging.Logger = None):
        self.exchange_registry = exchange_registry
        self.logger = logger or logging.getLogger(__name__)

        # Конфигурация частичного закрытия по умолчанию
        self.default_config = {
            "enabled": True,
            "levels": [
                {"percent": 30, "price_ratio": 1.01},  # 30% при +1%
                {"percent": 30, "price_ratio": 1.02},  # 30% при +2%
                {"percent": 40, "price_ratio": 1.03},  # 40% при +3%
            ],
            "trailing_stop": {
                "enabled": True,
                "activation_profit": 0.015,  # Активация при +1.5%
                "trailing_distance": 0.005,  # Трейлинг на 0.5%
            },
            "profit_protection": {
                "enabled": True,
                "breakeven_at": 0.01,  # Перенос SL в безубыток при +1%
                "lock_profit_at": 0.02,  # Защита 50% прибыли при +2%
                "lock_profit_percent": 0.5,
            },
        }

        # Отслеживание активных частичных закрытий
        self._active_partials: dict[str, dict] = {}
        self._partial_locks: dict[str, asyncio.Lock] = {}

    async def setup_partial_tp(self, position: dict[str, Any], config: dict | None = None) -> bool:
        """
        Настройка частичного закрытия для позиции

        Args:
            position: Информация о позиции
            config: Конфигурация частичного закрытия

        Returns:
            bool: Успешность настройки
        """
        try:
            symbol = position["symbol"]
            side = position["side"]
            quantity = Decimal(str(position["quantity"]))
            entry_price = Decimal(str(position["entry_price"]))

            # Используем переданную конфигурацию или по умолчанию
            tp_config = config or self.default_config

            if not tp_config.get("enabled", False):
                self.logger.info(f"Частичное закрытие отключено для {symbol}")
                return False

            levels = tp_config.get("levels", self.default_config["levels"])

            # Создаем уровни частичного закрытия
            partial_orders = []
            remaining_qty = quantity

            for i, level in enumerate(levels):
                # Рассчитываем количество для закрытия
                close_percent = Decimal(str(level["percent"])) / Decimal("100")
                close_qty = quantity * close_percent

                # Рассчитываем цену закрытия
                if side == "long":
                    tp_price = entry_price * Decimal(str(level["price_ratio"]))
                else:  # short
                    tp_price = entry_price / Decimal(str(level["price_ratio"]))

                # Создаем ордер частичного закрытия
                partial_order = {
                    "symbol": symbol,
                    "side": OrderSide.SELL if side == "long" else OrderSide.BUY,
                    "quantity": float(close_qty),
                    "price": float(tp_price),
                    "type": OrderType.LIMIT,
                    "level": i + 1,
                    "percent": level["percent"],
                }

                partial_orders.append(partial_order)
                remaining_qty -= close_qty

                self.logger.info(
                    f"📊 Уровень TP{i + 1} для {symbol}: "
                    f"закрыть {level['percent']}% ({close_qty:.4f}) при {tp_price:.4f}"
                )

            # Сохраняем информацию о частичных закрытиях
            position_key = f"{symbol}_{side}"
            self._active_partials[position_key] = {
                "symbol": symbol,
                "side": side,
                "entry_price": float(entry_price),
                "original_quantity": float(quantity),
                "remaining_quantity": float(quantity),
                "levels": partial_orders,
                "executed_levels": [],
                "created_at": datetime.utcnow(),
            }

            # Отправляем ордера на биржу
            success_count = 0
            for partial_order in partial_orders:
                if await self._place_partial_order(partial_order):
                    success_count += 1

            self.logger.info(
                f"✅ Настроено {success_count}/{len(partial_orders)} "
                f"уровней частичного закрытия для {symbol}"
            )

            # Запускаем мониторинг трейлинг стопа если включен
            if tp_config.get("trailing_stop", {}).get("enabled", False):
                asyncio.create_task(self._monitor_trailing_stop(position_key, tp_config))

            return success_count > 0

        except Exception as e:
            self.logger.error(f"❌ Ошибка настройки частичного TP: {e}")
            return False

    async def _place_partial_order(self, order_data: dict) -> bool:
        """Размещение ордера частичного закрытия на бирже"""
        try:
            # Получаем биржу
            exchange = await self.exchange_registry.get_exchange("bybit")
            if not exchange:
                self.logger.error("❌ Не удалось получить подключение к бирже")
                return False

            # Создаем запрос ордера
            from exchanges.base.order_types import (
                OrderRequest,
            )
            from exchanges.base.order_types import OrderSide as ExchangeOrderSide
            from exchanges.base.order_types import OrderType as ExchangeOrderType

            order_request = OrderRequest(
                symbol=order_data["symbol"],
                side=(
                    ExchangeOrderSide.SELL
                    if order_data["side"] == OrderSide.SELL
                    else ExchangeOrderSide.BUY
                ),
                order_type=ExchangeOrderType.LIMIT,
                quantity=order_data["quantity"],
                price=order_data["price"],
                reduce_only=True,  # Важно: только для закрытия позиции
            )

            # Отправляем ордер
            response = await exchange.place_order(order_request)

            if response and response.success:
                self.logger.info(
                    f"✅ Ордер частичного TP размещен: "
                    f"{order_data['symbol']} уровень {order_data.get('level', 'N/A')}"
                )
                return True
            else:
                self.logger.error(
                    f"❌ Ошибка размещения частичного TP: "
                    f"{response.error if response else 'Нет ответа'}"
                )
                return False

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки частичного ордера: {e}")
            return False

    async def _monitor_trailing_stop(self, position_key: str, config: dict):
        """Мониторинг и управление трейлинг стопом"""
        try:
            trailing_config = config.get("trailing_stop", {})
            activation_profit = Decimal(str(trailing_config.get("activation_profit", 0.015)))
            trailing_distance = Decimal(str(trailing_config.get("trailing_distance", 0.005)))

            position_data = self._active_partials.get(position_key)
            if not position_data:
                return

            symbol = position_data["symbol"]
            side = position_data["side"]
            entry_price = Decimal(str(position_data["entry_price"]))

            highest_price = entry_price
            lowest_price = entry_price
            trailing_stop_price = None

            self.logger.info(f"🔄 Запущен мониторинг трейлинг стопа для {symbol}")

            while position_key in self._active_partials:
                try:
                    # Получаем текущую цену
                    exchange = await self.exchange_registry.get_exchange("bybit")
                    if not exchange:
                        await asyncio.sleep(5)
                        continue

                    ticker = await exchange.get_ticker(symbol)
                    if not ticker:
                        await asyncio.sleep(5)
                        continue

                    current_price = Decimal(str(ticker["last"]))

                    # Для LONG позиций
                    if side == "long":
                        # Обновляем максимальную цену
                        if current_price > highest_price:
                            highest_price = current_price

                        # Проверяем активацию трейлинга
                        profit_ratio = (highest_price - entry_price) / entry_price

                        if profit_ratio >= activation_profit:
                            # Рассчитываем новый уровень стопа
                            new_stop = highest_price * (Decimal("1") - trailing_distance)

                            if trailing_stop_price is None or new_stop > trailing_stop_price:
                                trailing_stop_price = new_stop

                                # Обновляем стоп-лосс на бирже
                                await self._update_stop_loss(
                                    symbol, side, float(trailing_stop_price)
                                )

                                self.logger.info(
                                    f"📈 Трейлинг стоп обновлен для {symbol}: "
                                    f"SL={trailing_stop_price:.4f} (макс цена={highest_price:.4f})"
                                )

                    # Для SHORT позиций
                    else:
                        # Обновляем минимальную цену
                        if current_price < lowest_price:
                            lowest_price = current_price

                        # Проверяем активацию трейлинга
                        profit_ratio = (entry_price - lowest_price) / entry_price

                        if profit_ratio >= activation_profit:
                            # Рассчитываем новый уровень стопа
                            new_stop = lowest_price * (Decimal("1") + trailing_distance)

                            if trailing_stop_price is None or new_stop < trailing_stop_price:
                                trailing_stop_price = new_stop

                                # Обновляем стоп-лосс на бирже
                                await self._update_stop_loss(
                                    symbol, side, float(trailing_stop_price)
                                )

                                self.logger.info(
                                    f"📉 Трейлинг стоп обновлен для {symbol}: "
                                    f"SL={trailing_stop_price:.4f} (мин цена={lowest_price:.4f})"
                                )

                    # Задержка между проверками
                    await asyncio.sleep(10)

                except Exception as e:
                    self.logger.error(f"Ошибка в мониторинге трейлинг стопа: {e}")
                    await asyncio.sleep(30)

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка трейлинг стопа: {e}")

    async def _update_stop_loss(self, symbol: str, side: str, stop_price: float) -> bool:
        """Обновление стоп-лосса на бирже"""
        try:
            exchange = await self.exchange_registry.get_exchange("bybit")
            if not exchange:
                return False

            # Используем метод биржи для обновления SL
            # Это зависит от конкретной реализации биржи
            result = await exchange.modify_position_sl_tp(
                symbol=symbol,
                stop_loss=stop_price,
                take_profit=None,  # Не меняем TP
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления SL: {e}")
            return False

    async def check_partial_execution(self, symbol: str, side: str) -> dict | None:
        """
        Проверка исполнения частичных ордеров

        Returns:
            Dict с информацией об исполненных уровнях
        """
        position_key = f"{symbol}_{side}"
        return self._active_partials.get(position_key)

    async def cancel_partial_orders(self, symbol: str, side: str) -> bool:
        """Отмена всех частичных ордеров для позиции"""
        try:
            position_key = f"{symbol}_{side}"
            position_data = self._active_partials.get(position_key)

            if not position_data:
                return True

            # Здесь должна быть логика отмены ордеров на бирже
            # ...

            # Удаляем из отслеживания
            del self._active_partials[position_key]

            self.logger.info(f"✅ Частичные ордера отменены для {symbol}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка отмены частичных ордеров: {e}")
            return False
