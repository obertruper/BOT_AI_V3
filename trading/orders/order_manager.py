#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер ордеров

Управляет жизненным циклом ордеров от создания до исполнения.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from database.connections import get_async_db
from database.models.base_models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    SignalType,
)
from database.models.signal import Signal


class OrderManager:
    """
    Менеджер управления ордерами

    Обеспечивает:
    - Создание ордеров из сигналов
    - Отслеживание статусов ордеров
    - Управление stop-loss и take-profit
    - Отмену и модификацию ордеров
    """

    def __init__(self, exchange_registry, logger: Optional[logging.Logger] = None):
        self.exchange_registry = exchange_registry
        self.logger = logger or logging.getLogger(__name__)
        self._active_orders: Dict[str, Order] = {}
        self._order_locks: Dict[str, asyncio.Lock] = {}

    async def create_order_from_signal(
        self, signal: Signal, trader_id: str
    ) -> Optional[Order]:
        """
        Создание ордера из торгового сигнала

        Args:
            signal: Торговый сигнал
            trader_id: ID трейдера

        Returns:
            Order или None если создание не удалось
        """
        try:
            # Определяем тип и сторону ордера
            order_side = self._get_order_side(signal.signal_type)
            if not order_side:
                self.logger.warning(
                    f"Не могу определить сторону ордера для сигнала {signal.signal_type}"
                )
                return None

            # Создаем ордер
            order = Order(
                exchange=signal.exchange,
                symbol=signal.symbol,
                order_id=self._generate_order_id(),
                side=order_side,
                order_type=OrderType.LIMIT
                if signal.suggested_price
                else OrderType.MARKET,
                status=OrderStatus.PENDING,
                price=float(signal.suggested_price) if signal.suggested_price else None,
                quantity=float(signal.suggested_quantity),
                stop_loss=float(signal.suggested_stop_loss)
                if signal.suggested_stop_loss
                else None,
                take_profit=(
                    float(signal.suggested_take_profit)
                    if signal.suggested_take_profit
                    else None
                ),
                strategy_name=signal.strategy_name,
                trader_id=trader_id,
                extra_data={
                    "signal_id": signal.id,
                    "signal_strength": signal.strength,
                    "signal_confidence": signal.confidence,
                },
            )

            # Сохраняем в БД
            async with get_async_db() as db:
                db.add(order)
                await db.commit()
                await db.refresh(order)

            # Добавляем в активные
            self._active_orders[order.order_id] = order
            self._order_locks[order.order_id] = asyncio.Lock()

            self.logger.info(
                f"Создан ордер {order.order_id}: {order.side.value} {order.quantity} "
                f"{order.symbol} на {order.exchange}"
            )

            return order

        except Exception as e:
            self.logger.error(f"Ошибка создания ордера: {e}")
            return None

    async def submit_order(self, order: Order) -> bool:
        """
        Отправка ордера на биржу

        Args:
            order: Ордер для отправки

        Returns:
            bool: Успешность отправки
        """
        async with self._order_locks.get(order.order_id, asyncio.Lock()):
            try:
                # Проверяем, является ли order.side строкой или enum
                side_str = (
                    order.side if isinstance(order.side, str) else order.side.value
                )
                self.logger.info(
                    f"📤 Отправка ордера на биржу: {side_str} {order.quantity} {order.symbol} "
                    f"@ {order.price or 'MARKET'} на {order.exchange}"
                )

                # Получаем объект биржи из реестра подключений
                # exchange_registry должен быть фабрикой или менеджером подключений
                # Временное решение - создаем биржу напрямую
                from exchanges.factory import ExchangeFactory

                factory = ExchangeFactory()

                # Получаем API ключи из окружения
                import os

                if order.exchange.lower() == "bybit":
                    api_key = os.getenv("BYBIT_API_KEY")
                    api_secret = os.getenv("BYBIT_API_SECRET")
                else:
                    self.logger.error(f"❌ Биржа {order.exchange} не поддерживается")
                    return False

                # Создаем подключение к бирже
                exchange = await factory.create_and_connect(
                    exchange_type=order.exchange.lower(),
                    api_key=api_key,
                    api_secret=api_secret,
                    sandbox=False,
                )

                if not exchange:
                    self.logger.error(
                        f"❌ Не удалось создать подключение к {order.exchange}"
                    )
                    return False

                await exchange.initialize()
                self.logger.info(f"🔗 Подключение к бирже {order.exchange} успешно")

                # Отправляем ордер через place_order
                # Создаем OrderRequest для Bybit
                from exchanges.base.order_types import (
                    OrderRequest,
                )
                from exchanges.base.order_types import OrderSide as ExchangeOrderSide
                from exchanges.base.order_types import OrderType as ExchangeOrderType

                # Маппинг типов ордеров
                order_type_map = {
                    "limit": ExchangeOrderType.LIMIT,
                    "market": ExchangeOrderType.MARKET,
                }

                order_side_map = {
                    "buy": ExchangeOrderSide.BUY,
                    "sell": ExchangeOrderSide.SELL,
                }

                order_request = OrderRequest(
                    symbol=order.symbol,
                    side=order_side_map.get(order.side.value, ExchangeOrderSide.BUY),
                    order_type=order_type_map.get(
                        order.order_type.value, ExchangeOrderType.LIMIT
                    ),
                    quantity=order.quantity,
                    price=order.price if order.order_type.value == "limit" else None,
                )

                # Отправляем ордер
                self.logger.info(
                    f"📤 Отправляем OrderRequest: {order_request.symbol} {order_request.side.value} "
                    f"{order_request.quantity} @ {order_request.price}"
                )

                response = await exchange.place_order(order_request)

                if response and response.success:
                    exchange_order_id = response.order_id
                else:
                    self.logger.error(
                        f"❌ Ошибка от биржи: {response.error if response else 'Нет ответа'}"
                    )
                    exchange_order_id = None

                if exchange_order_id:
                    # Обновляем ID ордера от биржи
                    order.order_id = exchange_order_id
                    order.status = OrderStatus.OPEN
                    order.updated_at = datetime.utcnow()

                    # Обновляем в БД
                    await self._update_order_in_db(order)

                    self.logger.info(
                        f"✅ Ордер {order.order_id} успешно отправлен на {order.exchange}"
                    )
                    return True
                else:
                    order.status = OrderStatus.REJECTED
                    await self._update_order_in_db(order)
                    self.logger.error("❌ Биржа вернула пустой ID для ордера")
                    return False

            except Exception as e:
                self.logger.error(f"❌ Ошибка отправки ордера {order.order_id}: {e}")
                import traceback

                traceback.print_exc()
                order.status = OrderStatus.REJECTED
                await self._update_order_in_db(order)
                return False

    async def cancel_order(self, order_id: str) -> bool:
        """Отмена ордера"""
        order = self._active_orders.get(order_id)
        if not order:
            self.logger.warning(f"Ордер {order_id} не найден в активных")
            return False

        async with self._order_locks.get(order_id, asyncio.Lock()):
            try:
                # Отменяем на бирже
                exchange = await self.exchange_registry.get_exchange(order.exchange)
                if exchange:
                    success = await exchange.cancel_order(order.order_id, order.symbol)

                    if success:
                        order.status = OrderStatus.CANCELLED
                        order.updated_at = datetime.utcnow()
                        await self._update_order_in_db(order)

                        # Удаляем из активных
                        self._active_orders.pop(order_id, None)
                        self._order_locks.pop(order_id, None)

                        self.logger.info(f"Ордер {order_id} успешно отменен")
                        return True

                return False

            except Exception as e:
                self.logger.error(f"Ошибка отмены ордера {order_id}: {e}")
                return False

    async def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus,
        filled_quantity: Optional[float] = None,
        average_price: Optional[float] = None,
    ):
        """Обновление статуса ордера"""
        order = self._active_orders.get(order_id)
        if not order:
            return

        async with self._order_locks.get(order_id, asyncio.Lock()):
            order.status = new_status
            order.updated_at = datetime.utcnow()

            if filled_quantity is not None:
                order.filled_quantity = filled_quantity

            if average_price is not None:
                order.average_price = average_price

            if new_status == OrderStatus.FILLED:
                order.filled_at = datetime.utcnow()
                # Удаляем из активных
                self._active_orders.pop(order_id, None)
                self._order_locks.pop(order_id, None)

            await self._update_order_in_db(order)

    async def get_active_orders(
        self, exchange: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[Order]:
        """Получить активные ордера"""
        orders = list(self._active_orders.values())

        if exchange:
            orders = [o for o in orders if o.exchange == exchange]

        if symbol:
            orders = [o for o in orders if o.symbol == symbol]

        return orders

    async def sync_orders_with_exchange(self, exchange_name: str):
        """Синхронизация ордеров с биржей"""
        try:
            exchange = await self.exchange_registry.get_exchange(exchange_name)
            if not exchange:
                return

            # Получаем все открытые ордера с биржи
            exchange_orders = await exchange.get_open_orders()

            # Обновляем статусы наших ордеров
            for order in self._active_orders.values():
                if order.exchange != exchange_name:
                    continue

                # Ищем соответствующий ордер на бирже
                exchange_order = next(
                    (eo for eo in exchange_orders if eo["id"] == order.order_id), None
                )

                if exchange_order:
                    # Обновляем статус
                    status = self._map_exchange_status(exchange_order["status"])
                    await self.update_order_status(
                        order.order_id,
                        status,
                        exchange_order.get("filled"),
                        exchange_order.get("average_price"),
                    )
                else:
                    # Ордер не найден на бирже - возможно исполнен или отменен
                    await self.update_order_status(
                        order.order_id, OrderStatus.CANCELLED
                    )

        except Exception as e:
            self.logger.error(f"Ошибка синхронизации ордеров с {exchange_name}: {e}")

    def _get_order_side(self, signal_type) -> Optional[OrderSide]:
        """Определение стороны ордера по типу сигнала"""
        mapping = {
            SignalType.LONG: OrderSide.BUY,
            SignalType.SHORT: OrderSide.SELL,
            SignalType.CLOSE_LONG: OrderSide.SELL,
            SignalType.CLOSE_SHORT: OrderSide.BUY,
        }
        return mapping.get(signal_type)

    def _generate_order_id(self) -> str:
        """Генерация уникального ID ордера"""
        from uuid import uuid4

        return f"BOT_{uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"

    def _map_exchange_status(self, exchange_status: str) -> OrderStatus:
        """Маппинг статусов биржи на наши статусы"""
        status_map = {
            "new": OrderStatus.OPEN,
            "open": OrderStatus.OPEN,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
        }
        return status_map.get(exchange_status.lower(), OrderStatus.OPEN)

    async def _update_order_in_db(self, order: Order):
        """Обновление ордера в БД"""
        try:
            async with get_async_db() as db:
                await db.merge(order)
                await db.commit()
        except Exception as e:
            self.logger.error(f"Ошибка обновления ордера в БД: {e}")

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return True

    async def start(self):
        """Запуск компонента"""
        self.logger.info("Order Manager запущен")

    async def stop(self):
        """Остановка компонента"""
        self.logger.info("Order Manager остановлен")

    def is_running(self) -> bool:
        """Проверка работы компонента"""
        return True
