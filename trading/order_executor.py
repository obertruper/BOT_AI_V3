#!/usr/bin/env python3
"""
Order Executor - обработчик исполнения ордеров
Исправляет проблему REJECTED ордеров
"""

import os
from datetime import datetime
from typing import Any

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from database.models.base_models import Order, OrderStatus
from exchanges.factory import ExchangeFactory

logger = setup_logger("order_executor")


class OrderExecutor:
    """
    Исполнитель ордеров

    Обеспечивает корректное создание и исполнение ордеров на бирже
    """

    def __init__(self, exchange_factory: ExchangeFactory = None):
        self.exchange_factory = exchange_factory or ExchangeFactory()
        self.exchanges = {}
        self.executed_count = 0
        self.rejected_count = 0

    async def initialize(self):
        """Инициализация подключений к биржам"""
        try:
            # Пробуем подключить Bybit
            exchange_names = ["bybit"]  # Можно расширить список

            for exchange_name in exchange_names:
                try:
                    exchange = self.exchange_factory.create_client(
                        exchange_name,
                        api_key=os.getenv("BYBIT_API_KEY"),
                        api_secret=os.getenv("BYBIT_API_SECRET"),
                        sandbox=False,
                    )
                    if exchange:
                        self.exchanges[exchange_name] = exchange
                        logger.info(f"✅ Подключена биржа: {exchange_name}")
                except Exception as e:
                    logger.error(f"❌ Не удалось подключить {exchange_name}: {e}")

        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")

    async def execute_order(self, order: Order) -> bool:
        """
        Исполняет ордер на бирже

        Returns:
            bool: True если успешно, False если отклонен
        """
        try:
            logger.info(
                f"Исполнение ордера: {order.symbol} {order.side} {order.quantity} @ {order.price}"
            )

            # 1. Проверка наличия биржи
            exchange = self.exchanges.get(order.exchange)
            if not exchange:
                await self._reject_order(order, f"Биржа {order.exchange} не подключена")
                return False

            # 2. Валидация параметров ордера
            validation_error = await self._validate_order(order, exchange)
            if validation_error:
                await self._reject_order(order, validation_error)
                return False

            # 3. Проверка баланса
            has_balance = await self._check_balance(order, exchange)
            if not has_balance:
                await self._reject_order(order, "Недостаточно средств")
                return False

            # 4. Создание ордера на бирже
            try:
                # Подготовка параметров
                order_params = {
                    "symbol": order.symbol,
                    "type": order.order_type.value.lower(),
                    "side": order.side.value.lower(),
                    "amount": float(order.quantity),
                    "price": float(order.price) if order.price else None,
                }

                # Отправка ордера
                exchange_order = await exchange.create_order(**order_params)

                if exchange_order:
                    # Обновляем статус в БД
                    await self._update_order_status(
                        order.id,
                        OrderStatus.OPEN,
                        {"exchange_order_id": exchange_order.get("id")},
                    )

                    self.executed_count += 1
                    logger.info(f"✅ Ордер исполнен: {exchange_order.get('id')}")

                    # Устанавливаем SL/TP сразу после создания ордера
                    if order.stop_loss or order.take_profit:
                        try:
                            await self._set_sltp_for_order(order, exchange)
                        except Exception as e:
                            logger.error(f"Ошибка установки SL/TP: {e}")

                    return True
                else:
                    await self._reject_order(order, "Биржа не вернула ID ордера")
                    return False

            except Exception as e:
                await self._reject_order(order, f"Ошибка биржи: {e!s}")
                return False

        except Exception as e:
            logger.error(f"Критическая ошибка исполнения ордера: {e}")
            await self._reject_order(order, f"Системная ошибка: {e!s}")
            return False

    async def _validate_order(self, order: Order, exchange) -> str | None:
        """Валидация параметров ордера"""
        try:
            # Проверка символа
            markets = await exchange.load_markets()
            if order.symbol not in markets:
                return f"Символ {order.symbol} не поддерживается биржей"

            market = markets[order.symbol]

            # Проверка минимального размера
            min_amount = market.get("limits", {}).get("amount", {}).get("min", 0)
            if order.quantity < min_amount:
                return f"Размер {order.quantity} меньше минимального {min_amount}"

            # Проверка точности цены
            if order.price:
                price_precision = market.get("precision", {}).get("price", 8)
                price_str = f"{order.price:.{price_precision}f}"

            # Проверка точности количества
            amount_precision = market.get("precision", {}).get("amount", 8)
            amount_str = f"{order.quantity:.{amount_precision}f}"

            return None

        except Exception as e:
            return f"Ошибка валидации: {e!s}"

    async def _check_balance(self, order: Order, exchange) -> bool:
        """Проверка достаточности баланса"""
        try:
            balance = await exchange.fetch_balance()

            if order.side.value == "BUY":
                # Для покупки нужна базовая валюта (например USDT)
                quote_currency = order.symbol.replace("USDT", "")  # Упрощенно
                required = order.quantity * order.price
                available = balance.get("USDT", {}).get("free", 0)

                if available < required:
                    logger.warning(f"Недостаточно USDT: нужно {required}, есть {available}")
                    return False
            else:
                # Для продажи нужна торгуемая валюта
                base_currency = order.symbol.replace("USDT", "")
                available = balance.get(base_currency, {}).get("free", 0)

                if available < order.quantity:
                    logger.warning(
                        f"Недостаточно {base_currency}: нужно {order.quantity}, есть {available}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Ошибка проверки баланса: {e}")
            return False

    async def _set_sltp_for_order(self, order: Order, exchange):
        """Установка SL/TP для созданного ордера"""
        try:
            logger.info(
                f"Устанавливаем SL/TP для {order.symbol}: SL={order.stop_loss}, TP={order.take_profit}"
            )

            # Получаем клиент биржи напрямую
            if hasattr(exchange, "client"):
                client = exchange.client
            else:
                client = exchange

            # Определяем positionIdx в зависимости от режима
            position_idx = 0  # One-way mode по умолчанию

            # Проверяем hedge mode из конфигурации
            if hasattr(client, "trading_config"):
                hedge_mode = client.trading_config.get("hedge_mode", False)
                if hedge_mode:
                    position_idx = 1 if order.side.value.upper() == "BUY" else 2

            params = {
                "category": "linear",
                "symbol": order.symbol,
                "tpslMode": "Full",
                "positionIdx": position_idx,
            }

            if order.stop_loss:
                params["stopLoss"] = str(order.stop_loss)

            if order.take_profit:
                params["takeProfit"] = str(order.take_profit)

            logger.info(f"Отправляем запрос set_trading_stop с параметрами: {params}")

            # Делаем прямой API запрос
            response = await client._make_request(
                "POST", "/v5/position/trading-stop", params, auth=True
            )

            if response.get("retCode") == 0:
                logger.info(f"✅ SL/TP успешно установлены для {order.symbol}")
            else:
                logger.error(f"❌ Ошибка установки SL/TP: {response.get('retMsg')}")

        except Exception as e:
            logger.error(f"Ошибка при установке SL/TP: {e}")
            import traceback

            logger.error(traceback.format_exc())

    async def _reject_order(self, order: Order, reason: str):
        """Отклоняет ордер с указанием причины"""
        self.rejected_count += 1
        logger.warning(f"❌ Ордер отклонен: {reason}")

        await self._update_order_status(
            order.id,
            OrderStatus.REJECTED,
            {"error_message": reason, "rejected_at": datetime.now()},
        )

    async def _update_order_status(
        self, order_id: int, status: OrderStatus, metadata: dict[str, Any] = None
    ):
        """Обновляет статус ордера в БД"""
        try:
            query = """
            UPDATE orders
            SET status = $2, metadata = COALESCE(metadata, '{}') || $3
            WHERE id = $1
            """

            await AsyncPGPool.execute(query, order_id, status.value, metadata or {})

        except Exception as e:
            logger.error(f"Ошибка обновления статуса ордера: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику исполнителя"""
        return {
            "executed_count": self.executed_count,
            "rejected_count": self.rejected_count,
            "success_rate": (
                (self.executed_count / (self.executed_count + self.rejected_count) * 100)
                if (self.executed_count + self.rejected_count) > 0
                else 0
            ),
            "connected_exchanges": list(self.exchanges.keys()),
        }
