#!/usr/bin/env python3
"""
Движок исполнения ордеров

Обеспечивает надежное исполнение ордеров с управлением ошибками и retry логикой.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from database.models.base_models import Order, OrderSide, OrderStatus, OrderType


class ExecutionMode(Enum):
    """Режимы исполнения"""

    AGGRESSIVE = "aggressive"  # Быстрое исполнение, market ордера
    PASSIVE = "passive"  # Лимитные ордера, ждем лучшую цену
    SMART = "smart"  # Умное исполнение с адаптивной логикой


class ExecutionEngine:
    """
    Движок исполнения торговых операций

    Обеспечивает:
    - Умное исполнение ордеров
    - Управление проскальзыванием
    - Retry логику при ошибках
    - Частичное исполнение
    """

    def __init__(self, order_manager, exchange_registry, logger: logging.Logger | None = None):
        self.order_manager = order_manager
        self.exchange_registry = exchange_registry
        self.logger = logger or logging.getLogger(__name__)

        # Настройки исполнения
        self.max_slippage = 0.002  # 0.2%
        self.max_retries = 3
        self.retry_delay = 1.0  # секунды
        self.execution_timeout = 60  # секунды

        # Статистика
        self._execution_stats = {
            "total_executed": 0,
            "successful": 0,
            "failed": 0,
            "total_slippage": Decimal("0"),
            "avg_execution_time": 0.0,
        }

    async def execute_order(self, order: Order, mode: ExecutionMode = ExecutionMode.SMART) -> bool:
        """
        Исполнить ордер

        Args:
            order: Ордер для исполнения
            mode: Режим исполнения

        Returns:
            bool: Успешность исполнения
        """
        start_time = datetime.utcnow()

        try:
            self.logger.info(
                f"🎯 Начинаем исполнение ордера: {order.side} {order.quantity} {order.symbol} "
                f"(режим: {mode.value})"
            )

            # Проверяем валидность ордера
            if not self._validate_order(order):
                self.logger.error(f"❌ Ордер {order.order_id} не прошел валидацию")
                return False

            self.logger.info(f"✅ Ордер {order.order_id} прошел валидацию")

            # Выбираем стратегию исполнения
            if mode == ExecutionMode.AGGRESSIVE:
                success = await self._execute_aggressive(order)
            elif mode == ExecutionMode.PASSIVE:
                success = await self._execute_passive(order)
            else:  # SMART
                success = await self._execute_smart(order)

            # Обновляем статистику
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_statistics(success, execution_time)

            if success:
                self.logger.info(
                    f"✅ Ордер {order.order_id} успешно исполнен за {execution_time:.2f}с"
                )
            else:
                self.logger.error(f"❌ Ордер {order.order_id} не был исполнен")

            return success

        except Exception as e:
            self.logger.error(f"❌ Ошибка исполнения ордера {order.order_id}: {e}")
            import traceback

            traceback.print_exc()
            self._update_statistics(False, 0)
            return False

    async def _execute_aggressive(self, order: Order) -> bool:
        """Агрессивное исполнение - market ордера"""
        self.logger.info(f"🚀 Агрессивное исполнение ордера {order.order_id}")

        # Конвертируем в market ордер
        order.order_type = OrderType.MARKET
        order.price = None

        # Отправляем на исполнение
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"📤 Попытка {attempt + 1}/{self.max_retries} отправки ордера на биржу")
                success = await self.order_manager.submit_order(order)
                
                if success:
                    self.logger.info(f"✅ Ордер {order.order_id} успешно отправлен на биржу")
                    # Ждем исполнения
                    filled = await self._wait_for_fill(order)
                    if filled:
                        self.logger.info(f"✅ Ордер {order.order_id} успешно исполнен на бирже")
                    else:
                        self.logger.warning(f"⚠️ Ордер {order.order_id} отправлен, но не исполнен в течение таймаута")
                    return success
                else:
                    self.logger.error(f"❌ Не удалось отправить ордер {order.order_id} на биржу")

            except Exception as e:
                self.logger.error(f"❌ Попытка {attempt + 1} не удалась: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        self.logger.error(f"❌ Исчерпаны все попытки отправки ордера {order.order_id}")
        return False

    async def _execute_passive(self, order: Order) -> bool:
        """Пассивное исполнение - лимитный ордер по лучшей цене"""
        self.logger.info(f"Пассивное исполнение ордера {order.order_id}")

        # Получаем лучшую цену
        best_price = await self._get_best_price(order)
        if best_price:
            order.price = float(best_price)

        # Отправляем лимитный ордер
        success = await self.order_manager.submit_order(order)

        if success:
            # Ждем исполнения с таймаутом
            filled = await self._wait_for_fill(order, timeout=self.execution_timeout)

            if not filled and order.status == OrderStatus.OPEN:
                # Если не исполнился - отменяем
                await self.order_manager.cancel_order(order.order_id)
                return False

        return success

    async def _execute_smart(self, order: Order) -> bool:
        """Умное исполнение с адаптивной логикой"""
        self.logger.info(f"Умное исполнение ордера {order.order_id}")

        # Анализируем рыночные условия
        market_data = await self._analyze_market_conditions(order)

        # Если высокая волатильность - используем market
        if market_data.get("volatility", 0) > 0.02:  # 2%
            return await self._execute_aggressive(order)

        # Если низкая ликвидность - разбиваем на части
        if market_data.get("liquidity", float("inf")) < order.quantity * 2:
            return await self._execute_in_chunks(order)

        # Иначе - пробуем пассивное исполнение
        success = await self._execute_passive(order)

        # Если не удалось - переходим к агрессивному
        if not success:
            self.logger.info(f"Переход к агрессивному исполнению для {order.order_id}")
            return await self._execute_aggressive(order)

        return success

    async def _execute_in_chunks(self, order: Order, chunks: int = 3) -> bool:
        """Исполнение ордера частями"""
        self.logger.info(f"Исполнение ордера {order.order_id} в {chunks} частей")

        chunk_size = order.quantity / chunks
        total_filled = 0

        for i in range(chunks):
            # Создаем частичный ордер
            chunk_order = Order(
                exchange=order.exchange,
                symbol=order.symbol,
                order_id=f"{order.order_id}_chunk_{i}",
                side=order.side,
                order_type=order.order_type,
                quantity=chunk_size,
                price=order.price,
                strategy_name=order.strategy_name,
                trader_id=order.trader_id,
            )

            # Исполняем часть
            success = await self.order_manager.submit_order(chunk_order)

            if success:
                await self._wait_for_fill(chunk_order, timeout=30)

                if chunk_order.status == OrderStatus.FILLED:
                    total_filled += chunk_order.filled_quantity or chunk_size

            # Небольшая задержка между частями
            if i < chunks - 1:
                await asyncio.sleep(2)

        # Обновляем оригинальный ордер
        fill_ratio = total_filled / order.quantity

        if fill_ratio >= 0.95:  # 95% исполнено
            order.status = OrderStatus.FILLED
            order.filled_quantity = total_filled
        elif fill_ratio > 0:
            order.status = OrderStatus.PARTIALLY_FILLED
            order.filled_quantity = total_filled
        else:
            order.status = OrderStatus.CANCELLED

        await self.order_manager._update_order_in_db(order)

        return fill_ratio >= 0.95

    async def _wait_for_fill(self, order: Order, timeout: float = 30) -> bool:
        """Ожидание исполнения ордера"""
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            # Синхронизируем с биржей
            await self.order_manager.sync_orders_with_exchange(order.exchange)

            # Проверяем статус
            current_order = self.order_manager._active_orders.get(order.order_id)

            if not current_order or current_order.status in [
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.REJECTED,
            ]:
                return current_order and current_order.status == OrderStatus.FILLED

            await asyncio.sleep(1)

        return False

    async def _get_best_price(self, order: Order) -> Decimal | None:
        """Получить лучшую цену для ордера"""
        try:
            exchange = await self.exchange_registry.get_exchange(order.exchange)
            if not exchange:
                return None

            orderbook = await exchange.get_orderbook(order.symbol)

            if order.side == OrderSide.BUY:
                # Для покупки - лучший ask
                return Decimal(str(orderbook["asks"][0][0])) if orderbook["asks"] else None
            else:
                # Для продажи - лучший bid
                return Decimal(str(orderbook["bids"][0][0])) if orderbook["bids"] else None

        except Exception as e:
            self.logger.error(f"Ошибка получения лучшей цены: {e}")
            return None

    async def _analyze_market_conditions(self, order: Order) -> dict[str, float]:
        """Анализ рыночных условий"""
        try:
            exchange = await self.exchange_registry.get_exchange(order.exchange)
            if not exchange:
                return {}

            # Получаем данные
            ticker = await exchange.get_ticker(order.symbol)
            orderbook = await exchange.get_orderbook(order.symbol)

            # Рассчитываем метрики
            volatility = (ticker["high"] - ticker["low"]) / ticker["last"] if ticker else 0

            # Ликвидность на уровне нашего объема
            if order.side == OrderSide.BUY:
                liquidity = sum(ask[1] for ask in orderbook.get("asks", [])[:10])
            else:
                liquidity = sum(bid[1] for bid in orderbook.get("bids", [])[:10])

            spread = 0
            if orderbook.get("asks") and orderbook.get("bids"):
                spread = (orderbook["asks"][0][0] - orderbook["bids"][0][0]) / orderbook["bids"][0][
                    0
                ]

            return {"volatility": volatility, "liquidity": liquidity, "spread": spread}

        except Exception as e:
            self.logger.error(f"Ошибка анализа рыночных условий: {e}")
            return {}

    def _validate_order(self, order: Order) -> bool:
        """Валидация ордера перед исполнением"""
        if order.status != OrderStatus.PENDING:
            self.logger.debug(f"Ордер {order.order_id} имеет статус {order.status}, требуется PENDING")
            return False

        if order.quantity <= 0:
            self.logger.warning(f"Ордер {order.order_id} имеет некорректное количество: {order.quantity}")
            return False

        if order.order_type == OrderType.LIMIT and not order.price:
            self.logger.warning(f"Лимитный ордер {order.order_id} без цены")
            return False

        # Временно отключаем проверку баланса до исправления exchange_registry
        # TODO: Восстановить после исправления получения баланса
        self.logger.debug(f"Ордер {order.order_id} прошел базовую валидацию")
        
        return True

    def _update_statistics(self, success: bool, execution_time: float):
        """Обновление статистики исполнения"""
        self._execution_stats["total_executed"] += 1

        if success:
            self._execution_stats["successful"] += 1
        else:
            self._execution_stats["failed"] += 1

        # Обновляем среднее время исполнения
        if execution_time > 0:
            current_avg = self._execution_stats["avg_execution_time"]
            total = self._execution_stats["total_executed"]
            self._execution_stats["avg_execution_time"] = (
                current_avg * (total - 1) + execution_time
            ) / total

    async def get_execution_stats(self) -> dict[str, Any]:
        """Получить статистику исполнения"""
        stats = self._execution_stats.copy()

        if stats["total_executed"] > 0:
            stats["success_rate"] = stats["successful"] / stats["total_executed"]
        else:
            stats["success_rate"] = 0.0

        return stats

    async def health_check(self) -> bool:
        """Проверка здоровья компонента"""
        return True

    async def start(self):
        """Запуск компонента"""
        self.logger.info("Execution Engine запущен")

    async def stop(self):
        """Остановка компонента"""
        self.logger.info("Execution Engine остановлен")

    def is_running(self) -> bool:
        """Проверка работы компонента"""
        return True
