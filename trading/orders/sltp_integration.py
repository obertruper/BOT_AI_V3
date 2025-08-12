#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграция SL/TP с Order Manager
"""

import logging
from typing import Any, Optional

from database.models import Order
from database.models.base_models import OrderSide
from trading.sltp.enhanced_manager import EnhancedSLTPManager


class SLTPIntegration:
    """Интеграция Enhanced SL/TP Manager с системой ордеров"""

    def __init__(self, sltp_manager: Optional[EnhancedSLTPManager] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sltp_manager = sltp_manager

    async def handle_filled_order(self, order: Order, exchange_client: Any) -> bool:
        """
        Обработка исполненного ордера - создание SL/TP

        Args:
            order: Исполненный ордер
            exchange_client: Клиент биржи

        Returns:
            bool: Успешность создания SL/TP
        """
        if not self.sltp_manager:
            self.logger.warning("SL/TP Manager не инициализирован")
            return False

        try:
            # Устанавливаем клиент биржи для текущей операции
            self.sltp_manager.exchange_client = exchange_client

            # Определяем параметры для SL/TP
            position_side = "Buy" if order.side == OrderSide.BUY else "Sell"

            # Создаем временную позицию для SL/TP
            from exchanges.base.models import Position

            temp_position = Position(
                symbol=order.symbol,
                side=position_side,
                size=order.filled_quantity or order.quantity,
                entry_price=order.average_price or order.price,
                mark_price=order.average_price or order.price,
                position_idx=1 if position_side == "Buy" else 2,  # Hedge mode
            )

            # Получаем параметры SL/TP из конфигурации или сигнала
            sl_percentage = (order.extra_data or {}).get("stop_loss_pct", 0.02)
            tp_percentage = (order.extra_data or {}).get("take_profit_pct", 0.04)

            # Рассчитываем абсолютные значения SL/TP
            entry_price = temp_position.entry_price
            if position_side == "Buy":
                sl_price = entry_price * (1 - sl_percentage)
                tp_price = entry_price * (1 + tp_percentage)
            else:  # Sell
                sl_price = entry_price * (1 + sl_percentage)
                tp_price = entry_price * (1 - tp_percentage)

            # Создаем custom config с рассчитанными ценами
            from trading.sltp.models import SLTPConfig

            custom_config = SLTPConfig(stop_loss=sl_price, take_profit=tp_price)

            # Создаем SL/TP ордера
            sl_tp_orders = await self.sltp_manager.create_sltp_orders(
                position=temp_position, custom_config=custom_config
            )

            if sl_tp_orders:
                self.logger.info(
                    f"✅ Созданы SL/TP ордера для {order.symbol}: "
                    f"SL={sl_tp_orders[0].trigger_price if sl_tp_orders else 'N/A'}, "
                    f"TP={sl_tp_orders[1].trigger_price if len(sl_tp_orders) > 1 else 'N/A'}"
                )

                # Сохраняем ID позиции для отслеживания
                order.extra_data = order.extra_data or {}
                # Position из exchanges.base.models не имеет id, используем symbol как идентификатор
                order.extra_data["position_id"] = f"{order.symbol}_{order.order_id}"
                order.extra_data["sltp_created"] = True
                order.extra_data["sl_order_id"] = (
                    sl_tp_orders[0].id if sl_tp_orders else None
                )
                order.extra_data["tp_order_ids"] = (
                    [o.id for o in sl_tp_orders[1:]] if len(sl_tp_orders) > 1 else []
                )

                return True
            else:
                self.logger.warning(
                    f"Не удалось создать SL/TP ордера для {order.symbol}"
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Ошибка при создании SL/TP для ордера {order.order_id}: {e}"
            )
            import traceback

            traceback.print_exc()
            return False

    async def update_position_sltp(
        self, position_id: str, current_price: float
    ) -> bool:
        """
        Обновление SL/TP для позиции (трейлинг стоп, защита прибыли)

        Args:
            position_id: ID позиции
            current_price: Текущая цена

        Returns:
            bool: Успешность обновления
        """
        if not self.sltp_manager:
            return False

        try:
            # Обновляем трейлинг стоп
            updated = await self.sltp_manager.update_trailing_stop(
                position_id, current_price
            )

            if updated:
                self.logger.info(f"✅ Обновлен трейлинг стоп для позиции {position_id}")

            # Проверяем защиту прибыли
            profit_protected = await self.sltp_manager.update_profit_protection(
                position_id, current_price
            )

            if profit_protected:
                self.logger.info(
                    f"✅ Активирована защита прибыли для позиции {position_id}"
                )

            return updated or profit_protected

        except Exception as e:
            self.logger.error(f"Ошибка обновления SL/TP для позиции {position_id}: {e}")
            return False

    async def check_partial_tp(self, position_id: str, current_price: float) -> bool:
        """
        Проверка и выполнение частичного Take Profit

        Args:
            position_id: ID позиции
            current_price: Текущая цена

        Returns:
            bool: Было ли выполнено частичное закрытие
        """
        if not self.sltp_manager:
            return False

        try:
            # Проверяем условия для частичного TP
            executed = await self.sltp_manager.check_and_execute_partial_tp(
                position_id, current_price
            )

            if executed:
                self.logger.info(
                    f"✅ Выполнен частичный Take Profit для позиции {position_id}"
                )

            return executed

        except Exception as e:
            self.logger.error(
                f"Ошибка проверки частичного TP для позиции {position_id}: {e}"
            )
            return False
