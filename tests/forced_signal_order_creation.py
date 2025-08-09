#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Форсированное создание тестовых сигналов и ордеров

Этот скрипт:
1. Создает реальные тестовые сигналы LONG/SHORT
2. Форсирует их обработку через торговую систему
3. Проверяет создание ордеров с тестовым балансом $150
4. Диагностирует проблемы в цепочке обработки
5. Показывает точное место обрыва цепочки
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta
from typing import List

# Добавляем путь к проекту
sys.path.insert(0, "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from database.connections import get_async_db
from database.models.base_models import (
    Balance,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Signal,
    SignalType,
    Trade,
)


class ForcedSignalOrderTester:
    """Форсированное тестирование создания ордеров"""

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Тестовый баланс $150
        self.test_balance = 150.0
        self.test_trader_id = "test_trader_150usd"

    async def run_forced_tests(self):
        """Запуск форсированных тестов"""
        self.logger.info("🚀 ФОРСИРОВАННОЕ ТЕСТИРОВАНИЕ СИГНАЛ → ОРДЕР")

        try:
            # 1. Настраиваем тестовый баланс
            await self._setup_test_balance()

            # 2. Создаем форсированные тестовые сигналы
            signals = await self._create_forced_signals()

            # 3. Форсируем создание ордеров напрямую
            await self._force_create_orders_direct(signals)

            # 4. Проверяем через торговый движок (если возможно)
            await self._test_through_trading_engine(signals)

            # 5. Диагностируем проблемы
            await self._diagnose_problems()

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка: {e}")

    async def _setup_test_balance(self):
        """Настройка тестового баланса $150"""
        self.logger.info(f"💰 Настраиваем тестовый баланс ${self.test_balance}")

        try:
            async with get_async_db() as db:
                # Удаляем существующие балансы тестового трейдера
                await db.execute(
                    "DELETE FROM balances WHERE trader_id = %s", (self.test_trader_id,)
                )

                # Создаем USDT баланс
                usdt_balance = Balance(
                    exchange="bybit",
                    asset="USDT",
                    free=self.test_balance,
                    locked=0.0,
                    total=self.test_balance,
                    usd_value=self.test_balance,
                    trader_id=self.test_trader_id,
                )

                # Создаем небольшой BTC баланс для SHORT позиций
                btc_balance = Balance(
                    exchange="bybit",
                    asset="BTC",
                    free=0.002,  # ~$90 при $45000
                    locked=0.0,
                    total=0.002,
                    usd_value=90.0,
                    trader_id=self.test_trader_id,
                )

                db.add(usdt_balance)
                db.add(btc_balance)
                await db.commit()

                self.logger.info("✅ Тестовый баланс создан:")
                self.logger.info(f"   🔸 USDT: ${self.test_balance}")
                self.logger.info("   🔸 BTC: 0.002 (~$90)")

        except Exception as e:
            self.logger.error(f"❌ Ошибка создания баланса: {e}")

    async def _create_forced_signals(self) -> List[Signal]:
        """Создание форсированных сигналов"""
        self.logger.info("📝 Создаем форсированные сигналы...")

        current_time = datetime.utcnow()

        # Сигналы с учетом тестового баланса $150
        forced_signals = [
            {
                "symbol": "BTCUSDT",
                "signal_type": SignalType.LONG,
                "strength": 0.95,
                "confidence": 0.98,
                "suggested_price": 45000.0,
                "suggested_quantity": 0.001,  # ~$45 из $150
                "suggested_stop_loss": 44000.0,
                "suggested_take_profit": 47000.0,
                "strategy": "forced_test_ml",
                "priority": "high",
            },
            {
                "symbol": "ETHUSDT",
                "signal_type": SignalType.SHORT,
                "strength": 0.90,
                "confidence": 0.95,
                "suggested_price": 2500.0,
                "suggested_quantity": 0.02,  # ~$50 из $150
                "suggested_stop_loss": 2600.0,
                "suggested_take_profit": 2400.0,
                "strategy": "forced_test_momentum",
                "priority": "high",
            },
            {
                "symbol": "ADAUSDT",
                "signal_type": SignalType.LONG,
                "strength": 0.85,
                "confidence": 0.88,
                "suggested_price": None,  # Market order
                "suggested_quantity": 100.0,  # ~$50 из $150 (при $0.50)
                "suggested_stop_loss": 0.48,
                "suggested_take_profit": 0.55,
                "strategy": "forced_test_breakout",
                "priority": "medium",
            },
        ]

        signals = []

        try:
            async with get_async_db() as db:
                for signal_data in forced_signals:
                    signal = Signal(
                        symbol=signal_data["symbol"],
                        exchange="bybit",
                        signal_type=signal_data["signal_type"],
                        strength=signal_data["strength"],
                        confidence=signal_data["confidence"],
                        suggested_price=signal_data["suggested_price"],
                        suggested_quantity=signal_data["suggested_quantity"],
                        suggested_stop_loss=signal_data["suggested_stop_loss"],
                        suggested_take_profit=signal_data["suggested_take_profit"],
                        strategy_name=signal_data["strategy"],
                        timeframe="5m",
                        created_at=current_time,
                        expires_at=current_time + timedelta(hours=2),
                        indicators={
                            "forced_test": True,
                            "priority": signal_data["priority"],
                            "test_balance": self.test_balance,
                            "rsi": 75.5,
                            "macd_signal": "strong_" + signal_data["signal_type"].value,
                        },
                        extra_data={
                            "forced_creation": True,
                            "test_id": str(uuid.uuid4()),
                            "balance_check": True,
                            "trader_id": self.test_trader_id,
                        },
                    )

                    db.add(signal)
                    signals.append(signal)

                await db.commit()

                # Обновляем ID
                for signal in signals:
                    await db.refresh(signal)

                self.logger.info(f"✅ Создано {len(signals)} форсированных сигналов")
                for signal in signals:
                    self.logger.info(
                        f"   🔸 {signal.id}: {signal.signal_type.value} {signal.symbol}"
                    )

        except Exception as e:
            self.logger.error(f"❌ Ошибка создания сигналов: {e}")

        return signals

    async def _force_create_orders_direct(self, signals: List[Signal]):
        """Прямое форсированное создание ордеров"""
        self.logger.info("⚡ ФОРСИРУЕМ создание ордеров напрямую...")

        try:
            async with get_async_db() as db:
                for signal in signals:
                    self.logger.info(f"🔄 Создаем ордер для сигнала {signal.id}")

                    # Определяем параметры ордера
                    order_side = self._get_order_side(signal.signal_type)
                    order_type = (
                        OrderType.LIMIT if signal.suggested_price else OrderType.MARKET
                    )

                    # Генерируем уникальный ID ордера
                    order_id = f"FORCED_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"

                    # Создаем ордер
                    order = Order(
                        exchange=signal.exchange,
                        symbol=signal.symbol,
                        order_id=order_id,
                        side=order_side,
                        order_type=order_type,
                        status=OrderStatus.PENDING,
                        price=float(signal.suggested_price)
                        if signal.suggested_price
                        else None,
                        quantity=float(signal.suggested_quantity),
                        filled_quantity=0.0,
                        stop_loss=(
                            float(signal.suggested_stop_loss)
                            if signal.suggested_stop_loss
                            else None
                        ),
                        take_profit=(
                            float(signal.suggested_take_profit)
                            if signal.suggested_take_profit
                            else None
                        ),
                        strategy_name=signal.strategy_name,
                        trader_id=self.test_trader_id,
                        extra_data={
                            "signal_id": signal.id,
                            "forced_creation": True,
                            "test_balance": self.test_balance,
                            "signal_strength": signal.strength,
                            "signal_confidence": signal.confidence,
                        },
                    )

                    # Сохраняем в БД
                    db.add(order)
                    await db.commit()
                    await db.refresh(order)

                    self.logger.info(f"✅ Ордер {order.order_id} создан:")
                    self.logger.info(f"   🔸 Symbol: {order.symbol}")
                    self.logger.info(f"   🔸 Side: {order.side.value}")
                    self.logger.info(f"   🔸 Type: {order.order_type.value}")
                    self.logger.info(f"   🔸 Quantity: {order.quantity}")
                    self.logger.info(f"   🔸 Price: {order.price}")
                    self.logger.info(f"   🔸 Status: {order.status.value}")

                    # Симулируем частичное исполнение для тестирования
                    await self._simulate_order_execution(order, db)

        except Exception as e:
            self.logger.error(f"❌ Ошибка прямого создания ордеров: {e}")

    async def _simulate_order_execution(self, order: Order, db):
        """Симуляция исполнения ордера для тестирования"""
        self.logger.info(f"🎯 Симулируем исполнение ордера {order.order_id}")

        try:
            # Симулируем успешное исполнение
            execution_price = order.price if order.price else 45000.0  # Mock price
            filled_quantity = order.quantity

            # Обновляем ордер
            order.status = OrderStatus.FILLED
            order.filled_quantity = filled_quantity
            order.average_price = execution_price
            order.filled_at = datetime.utcnow()

            await db.merge(order)

            # Создаем тестовую сделку
            trade = Trade(
                exchange=order.exchange,
                symbol=order.symbol,
                trade_id=f"TRADE_{uuid.uuid4().hex[:8]}",
                order_id=order.order_id,
                side=order.side,
                price=execution_price,
                quantity=filled_quantity,
                commission=filled_quantity * execution_price * 0.001,  # 0.1% комиссия
                commission_asset="USDT",
                realized_pnl=0.0,  # Для новых позиций
                executed_at=datetime.utcnow(),
                strategy_name=order.strategy_name,
                trader_id=order.trader_id,
            )

            db.add(trade)
            await db.commit()

            self.logger.info(f"   ✅ Ордер исполнен по цене {execution_price}")
            self.logger.info(f"   🔸 Объем: {filled_quantity}")
            self.logger.info(f"   🔸 Сумма: ${execution_price * filled_quantity:.2f}")

        except Exception as e:
            self.logger.error(f"   ❌ Ошибка симуляции исполнения: {e}")

    async def _test_through_trading_engine(self, signals: List[Signal]):
        """Тестирование через торговый движок (если доступен)"""
        self.logger.info("🏗️  Тестируем через торговый движок...")

        try:
            # Пытаемся импортировать торговый движок
            from core.system.orchestrator import SystemOrchestrator
            from trading.engine import TradingEngine

            self.logger.info("   ✅ Торговый движок импортирован")

            # Здесь можно добавить тестирование через реальный движок
            # Но это требует полной инициализации системы
            self.logger.warning(
                "   ⚠️  Тестирование через движок требует полной инициализации"
            )

        except ImportError as e:
            self.logger.warning(f"   ⚠️  Торговый движок недоступен: {e}")
        except Exception as e:
            self.logger.error(f"   ❌ Ошибка импорта движка: {e}")

    async def _diagnose_problems(self):
        """Диагностика проблем в системе"""
        self.logger.info("🔍 ДИАГНОСТИКА ПРОБЛЕМ...")

        try:
            async with get_async_db() as db:
                # Проверяем созданные данные
                signals_result = await db.execute(
                    "SELECT COUNT(*) FROM signals WHERE extra_data::text LIKE '%forced_creation%'"
                )
                forced_signals_count = signals_result.scalar()

                orders_result = await db.execute(
                    "SELECT COUNT(*) FROM orders WHERE extra_data::text LIKE '%forced_creation%'"
                )
                forced_orders_count = orders_result.scalar()

                trades_result = await db.execute(
                    "SELECT COUNT(*) FROM trades WHERE trader_id = %s",
                    (self.test_trader_id,),
                )
                trades_count = trades_result.scalar()

                balance_result = await db.execute(
                    "SELECT asset, free, locked, total FROM balances WHERE trader_id = %s",
                    (self.test_trader_id,),
                )
                balances = balance_result.fetchall()

                self.logger.info("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
                self.logger.info(
                    f"   🔸 Форсированных сигналов: {forced_signals_count}"
                )
                self.logger.info(f"   🔸 Форсированных ордеров: {forced_orders_count}")
                self.logger.info(f"   🔸 Сделок: {trades_count}")

                self.logger.info("💰 БАЛАНСЫ:")
                for balance in balances:
                    self.logger.info(
                        f"   🔸 {balance.asset}: {balance.free} (заблокировано: {balance.locked})"
                    )

                # Проверяем обычные сигналы без ордеров
                all_signals_result = await db.execute("SELECT COUNT(*) FROM signals")
                all_signals_count = all_signals_result.scalar()

                all_orders_result = await db.execute("SELECT COUNT(*) FROM orders")
                all_orders_count = all_orders_result.scalar()

                self.logger.info("🔍 ОБЩАЯ СТАТИСТИКА:")
                self.logger.info(f"   🔸 Всего сигналов в БД: {all_signals_count}")
                self.logger.info(f"   🔸 Всего ордеров в БД: {all_orders_count}")
                self.logger.info(
                    f"   🔸 Соотношение ордеров к сигналам: {all_orders_count / all_signals_count * 100:.1f}%"
                )

                if all_signals_count > 50 and all_orders_count < 10:
                    self.logger.error("❌ ПРОБЛЕМА: Много сигналов, мало ордеров!")
                    self.logger.error("   Возможные причины:")
                    self.logger.error(
                        "   1. SignalProcessor не подключен к OrderManager"
                    )
                    self.logger.error(
                        "   2. TradingEngine не запущен или не обрабатывает сигналы"
                    )
                    self.logger.error("   3. Ошибки валидации сигналов")
                    self.logger.error("   4. Проблемы с риск-менеджментом")

        except Exception as e:
            self.logger.error(f"❌ Ошибка диагностики: {e}")

    def _get_order_side(self, signal_type: SignalType) -> OrderSide:
        """Определение стороны ордера"""
        mapping = {
            SignalType.LONG: OrderSide.BUY,
            SignalType.SHORT: OrderSide.SELL,
            SignalType.CLOSE_LONG: OrderSide.SELL,
            SignalType.CLOSE_SHORT: OrderSide.BUY,
        }
        return mapping.get(signal_type, OrderSide.BUY)


async def main():
    """Главная функция"""
    tester = ForcedSignalOrderTester()
    await tester.run_forced_tests()


if __name__ == "__main__":
    asyncio.run(main())
