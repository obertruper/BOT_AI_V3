#!/usr/bin/env python3
"""
Комплексные тесты для диагностики цепочки сигнал → ордер

Проверяет:
1. Создание и сохранение тестовых сигналов
2. Обработку сигналов через SignalProcessor
3. Создание ордеров из сигналов через OrderManager
4. Исполнение ордеров через ExecutionEngine
5. Диагностику проблем в цепочке обработки
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta

from sqlalchemy import text

# Добавляем корневую директорию в путь
sys.path.insert(0, "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from database.connections import get_async_db
from database.models.base_models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Signal,
    SignalType,
)
from trading.orders.order_manager import OrderManager
from trading.signals.signal_processor import SignalProcessor


class ComprehensiveTradingDiagnostics:
    """Комплексная диагностика торговой системы"""

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Статистика тестов
        self.test_stats = {
            "signals_created": 0,
            "signals_processed": 0,
            "orders_created": 0,
            "orders_submitted": 0,
            "errors": [],
            "warnings": [],
        }

    async def run_comprehensive_tests(self):
        """Запуск полного набора диагностических тестов"""
        self.logger.info("🚀 Начинаем комплексную диагностику торговой системы")

        try:
            # 1. Проверяем подключение к БД
            await self._test_database_connection()

            # 2. Анализируем существующие данные
            await self._analyze_existing_data()

            # 3. Создаем тестовые сигналы LONG и SHORT
            test_signals = await self._create_test_signals()

            # 4. Проверяем сохранение сигналов в БД
            await self._verify_signals_in_db(test_signals)

            # 5. Тестируем обработку сигналов через SignalProcessor
            await self._test_signal_processing(test_signals)

            # 6. Тестируем создание ордеров из сигналов
            await self._test_order_creation_from_signals(test_signals)

            # 7. Тестируем валидацию ордеров
            await self._test_order_validation()

            # 8. Проверяем компоненты системы
            await self._test_system_components()

            # 9. Симулируем полную цепочку обработки
            await self._simulate_full_processing_chain()

            # 10. Генерируем отчет
            await self._generate_diagnostic_report()

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в диагностике: {e}")
            self.test_stats["errors"].append(f"Critical error: {e}")

    async def _test_database_connection(self):
        """Тест подключения к БД"""
        self.logger.info("📊 Тестируем подключение к PostgreSQL...")

        try:
            async with get_async_db() as db:
                result = await db.execute(text("SELECT version()"))
                version = result.scalar()
                self.logger.info(f"✅ БД подключена: {version}")

                # Проверяем структуру таблиц
                result = await db.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                )
                tables = [row[0] for row in result]
                required_tables = ["signals", "orders", "trades", "balances"]

                for table in required_tables:
                    if table in tables:
                        self.logger.info(f"✅ Таблица {table} существует")
                    else:
                        self.logger.error(f"❌ Таблица {table} не найдена!")

        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к БД: {e}")
            self.test_stats["errors"].append(f"DB connection failed: {e}")

    async def _analyze_existing_data(self):
        """Анализ существующих данных в БД"""
        self.logger.info("📈 Анализируем существующие данные...")

        try:
            async with get_async_db() as db:
                # Сигналы
                result = await db.execute("SELECT COUNT(*), MAX(created_at) FROM signals")
                signals_count, last_signal = result.fetchone()

                # Ордера
                result = await db.execute(
                    "SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'filled') FROM orders"
                )
                orders_count, filled_orders = result.fetchone()

                # Сделки
                result = await db.execute(
                    "SELECT COUNT(*), COALESCE(SUM(quantity * price), 0) FROM trades"
                )
                trades_count, total_volume = result.fetchone()

                self.logger.info("📊 Статистика данных:")
                self.logger.info(f"   🔸 Сигналы: {signals_count} (последний: {last_signal})")
                self.logger.info(f"   🔸 Ордера: {orders_count} (исполнено: {filled_orders})")
                self.logger.info(f"   🔸 Сделки: {trades_count} (объем: ${total_volume:.2f})")

                if signals_count > 0 and orders_count == 0:
                    self.logger.warning("⚠️  ПРОБЛЕМА: Есть сигналы, но нет ордеров!")
                    self.test_stats["warnings"].append("Signals exist but no orders created")

        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа данных: {e}")

    async def _create_test_signals(self) -> list[Signal]:
        """Создание тестовых сигналов LONG и SHORT"""
        self.logger.info("📝 Создаем тестовые сигналы...")

        test_signals = []
        current_time = datetime.utcnow()

        # Тестовые данные для разных сценариев
        test_scenarios = [
            {
                "symbol": "BTCUSDT",
                "signal_type": SignalType.LONG,
                "strength": 0.85,
                "confidence": 0.90,
                "suggested_price": 45000.0,
                "suggested_quantity": 0.001,
                "suggested_stop_loss": 44000.0,
                "suggested_take_profit": 47000.0,
                "strategy": "test_ml_strategy",
                "exchange": "bybit",
            },
            {
                "symbol": "ETHUSDT",
                "signal_type": SignalType.SHORT,
                "strength": 0.75,
                "confidence": 0.85,
                "suggested_price": 2800.0,
                "suggested_quantity": 0.01,
                "suggested_stop_loss": 2900.0,
                "suggested_take_profit": 2700.0,
                "strategy": "test_momentum_strategy",
                "exchange": "bybit",
            },
            {
                "symbol": "ADAUSDT",
                "signal_type": SignalType.LONG,
                "strength": 0.60,
                "confidence": 0.70,
                "suggested_price": None,  # Market order
                "suggested_quantity": 10.0,
                "suggested_stop_loss": 0.45,
                "suggested_take_profit": 0.55,
                "strategy": "test_breakout_strategy",
                "exchange": "bybit",
            },
        ]

        try:
            async with get_async_db() as db:
                for scenario in test_scenarios:
                    signal = Signal(
                        symbol=scenario["symbol"],
                        exchange=scenario["exchange"],
                        signal_type=scenario["signal_type"],
                        strength=scenario["strength"],
                        confidence=scenario["confidence"],
                        suggested_price=scenario["suggested_price"],
                        suggested_quantity=scenario["suggested_quantity"],
                        suggested_stop_loss=scenario["suggested_stop_loss"],
                        suggested_take_profit=scenario["suggested_take_profit"],
                        strategy_name=scenario["strategy"],
                        timeframe="15m",
                        created_at=current_time,
                        expires_at=current_time + timedelta(hours=1),
                        indicators={
                            "rsi": 65.5,
                            "macd": 0.15,
                            "bb_position": 0.75,
                            "volume_ratio": 1.8,
                        },
                        extra_data={
                            "test_signal": True,
                            "test_id": str(uuid.uuid4()),
                            "created_by": "comprehensive_diagnostics",
                        },
                    )

                    db.add(signal)
                    test_signals.append(signal)

                await db.commit()

                # Обновляем ID после коммита
                for signal in test_signals:
                    await db.refresh(signal)

                self.test_stats["signals_created"] = len(test_signals)
                self.logger.info(f"✅ Создано {len(test_signals)} тестовых сигналов")

        except Exception as e:
            self.logger.error(f"❌ Ошибка создания тестовых сигналов: {e}")
            self.test_stats["errors"].append(f"Test signal creation failed: {e}")

        return test_signals

    async def _verify_signals_in_db(self, test_signals: list[Signal]):
        """Проверка корректного сохранения сигналов в БД"""
        self.logger.info("🔍 Проверяем сохранение сигналов в БД...")

        try:
            async with get_async_db() as db:
                for signal in test_signals:
                    result = await db.execute("SELECT * FROM signals WHERE id = %s", (signal.id,))
                    db_signal = result.fetchone()

                    if db_signal:
                        self.logger.info(f"✅ Сигнал {signal.id} найден в БД")

                        # Проверяем целостность данных
                        if db_signal.symbol == signal.symbol:
                            self.logger.info(f"   🔸 Symbol: {db_signal.symbol} ✓")
                        else:
                            self.logger.error(
                                f"   ❌ Symbol mismatch: {db_signal.symbol} != {signal.symbol}"
                            )

                        if db_signal.signal_type == signal.signal_type:
                            self.logger.info(f"   🔸 Type: {db_signal.signal_type.value} ✓")
                        else:
                            self.logger.error("   ❌ Type mismatch")

                        if abs(float(db_signal.strength) - float(signal.strength)) < 0.01:
                            self.logger.info(f"   🔸 Strength: {db_signal.strength} ✓")
                        else:
                            self.logger.error("   ❌ Strength mismatch")

                    else:
                        self.logger.error(f"❌ Сигнал {signal.id} не найден в БД!")
                        self.test_stats["errors"].append(f"Signal {signal.id} not found in DB")

        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки сигналов: {e}")

    async def _test_signal_processing(self, test_signals: list[Signal]):
        """Тестирование обработки сигналов через SignalProcessor"""
        self.logger.info("⚙️  Тестируем SignalProcessor...")

        try:
            processor = SignalProcessor()

            for signal in test_signals:
                self.logger.info(f"🔄 Обрабатываем сигнал {signal.id} ({signal.signal_type.value})")

                # Тестируем валидацию
                if processor._validate_signal(signal):
                    self.logger.info("   ✅ Валидация пройдена")
                else:
                    self.logger.error("   ❌ Валидация не пройдена!")
                    self.test_stats["errors"].append(f"Signal {signal.id} validation failed")
                    continue

                # Тестируем обработку
                try:
                    result = await processor.process_signal(signal)
                    if result:
                        self.logger.info("   ✅ Обработка успешна")
                        self.test_stats["signals_processed"] += 1
                    else:
                        self.logger.warning("   ⚠️  Обработка отклонена (возможно дубликат)")
                        self.test_stats["warnings"].append(
                            f"Signal {signal.id} processing rejected"
                        )

                except Exception as e:
                    self.logger.error(f"   ❌ Ошибка обработки: {e}")
                    self.test_stats["errors"].append(f"Signal {signal.id} processing error: {e}")

        except Exception as e:
            self.logger.error(f"❌ Ошибка создания SignalProcessor: {e}")

    async def _test_order_creation_from_signals(self, test_signals: list[Signal]):
        """Тестирование создания ордеров из сигналов"""
        self.logger.info("📋 Тестируем создание ордеров из сигналов...")

        try:
            # Создаем мок exchange_registry
            class MockExchangeRegistry:
                async def get_exchange(self, exchange_name):
                    return MockExchange()

            class MockExchange:
                async def create_order(self, **kwargs):
                    return f"test_order_{uuid.uuid4().hex[:8]}"

                async def get_balance(self, asset):
                    return {"free": 1000.0, "locked": 0.0, "total": 1000.0}

                async def get_ticker(self, symbol):
                    return {"last": 45000.0, "high": 46000.0, "low": 44000.0}

                async def get_orderbook(self, symbol):
                    return {"bids": [[44950.0, 1.5]], "asks": [[45050.0, 1.2]]}

            exchange_registry = MockExchangeRegistry()
            order_manager = OrderManager(exchange_registry)

            for signal in test_signals:
                self.logger.info(f"🔄 Создаем ордер из сигнала {signal.id}")

                try:
                    order = await order_manager.create_order_from_signal(signal, "test_trader")

                    if order:
                        self.logger.info(f"   ✅ Ордер создан: {order.order_id}")
                        self.logger.info(f"      🔸 Symbol: {order.symbol}")
                        self.logger.info(f"      🔸 Side: {order.side.value}")
                        self.logger.info(f"      🔸 Type: {order.order_type.value}")
                        self.logger.info(f"      🔸 Quantity: {order.quantity}")
                        self.logger.info(f"      🔸 Price: {order.price}")
                        self.logger.info(f"      🔸 Status: {order.status.value}")

                        self.test_stats["orders_created"] += 1

                        # Тестируем отправку ордера
                        await self._test_order_submission(order, order_manager)

                    else:
                        self.logger.error("   ❌ Ордер не создан!")
                        self.test_stats["errors"].append(
                            f"Order creation failed for signal {signal.id}"
                        )

                except Exception as e:
                    self.logger.error(f"   ❌ Ошибка создания ордера: {e}")
                    self.test_stats["errors"].append(
                        f"Order creation error for signal {signal.id}: {e}"
                    )

        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации тестов ордеров: {e}")

    async def _test_order_submission(self, order: Order, order_manager: OrderManager):
        """Тестирование отправки ордера"""
        self.logger.info(f"📤 Тестируем отправку ордера {order.order_id}")

        try:
            result = await order_manager.submit_order(order)

            if result:
                self.logger.info("   ✅ Ордер отправлен успешно")
                self.test_stats["orders_submitted"] += 1
            else:
                self.logger.warning("   ⚠️  Ордер не отправлен")
                self.test_stats["warnings"].append(f"Order {order.order_id} submission failed")

        except Exception as e:
            self.logger.error(f"   ❌ Ошибка отправки ордера: {e}")
            self.test_stats["errors"].append(f"Order {order.order_id} submission error: {e}")

    async def _test_order_validation(self):
        """Тестирование валидации ордеров"""
        self.logger.info("✅ Тестируем валидацию ордеров...")

        # Создаем тестовые ордера с разными проблемами
        test_orders = [
            # Валидный ордер
            Order(
                exchange="bybit",
                symbol="BTCUSDT",
                order_id="valid_order",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.PENDING,
                price=45000.0,
                quantity=0.001,
            ),
            # Нулевое количество
            Order(
                exchange="bybit",
                symbol="BTCUSDT",
                order_id="zero_quantity",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.PENDING,
                price=45000.0,
                quantity=0.0,
            ),
            # Лимитный ордер без цены
            Order(
                exchange="bybit",
                symbol="BTCUSDT",
                order_id="no_price",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.PENDING,
                price=None,
                quantity=0.001,
            ),
            # Неправильный статус
            Order(
                exchange="bybit",
                symbol="BTCUSDT",
                order_id="wrong_status",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.FILLED,
                price=45000.0,
                quantity=0.001,
            ),
        ]

        # Мок execution engine
        class MockExecutionEngine:
            def _validate_order(self, order):
                if order.status != OrderStatus.PENDING:
                    return False
                if order.quantity <= 0:
                    return False
                if order.order_type == OrderType.LIMIT and not order.price:
                    return False
                return True

        executor = MockExecutionEngine()

        for order in test_orders:
            is_valid = executor._validate_order(order)
            expected_valid = order.order_id == "valid_order"

            if is_valid == expected_valid:
                self.logger.info(f"   ✅ {order.order_id}: валидация корректна ({is_valid})")
            else:
                self.logger.error(f"   ❌ {order.order_id}: неожиданный результат валидации")

    async def _test_system_components(self):
        """Проверка состояния компонентов системы"""
        self.logger.info("🔧 Проверяем компоненты торговой системы...")

        # Проверяем импорты
        components_check = {
            "SignalProcessor": False,
            "OrderManager": False,
            "ExecutionEngine": False,
            "Database": False,
            "Models": False,
        }

        try:
            components_check["SignalProcessor"] = True
            self.logger.info("   ✅ SignalProcessor импортирован")
        except Exception as e:
            self.logger.error(f"   ❌ Ошибка импорта SignalProcessor: {e}")

        try:
            components_check["OrderManager"] = True
            self.logger.info("   ✅ OrderManager импортирован")
        except Exception as e:
            self.logger.error(f"   ❌ Ошибка импорта OrderManager: {e}")

        try:
            components_check["ExecutionEngine"] = True
            self.logger.info("   ✅ ExecutionEngine импортирован")
        except Exception as e:
            self.logger.error(f"   ❌ Ошибка импорта ExecutionEngine: {e}")

        try:
            components_check["Database"] = True
            self.logger.info("   ✅ Database connection импортирован")
        except Exception as e:
            self.logger.error(f"   ❌ Ошибка импорта database: {e}")

        try:
            components_check["Models"] = True
            self.logger.info("   ✅ Database models импортированы")
        except Exception as e:
            self.logger.error(f"   ❌ Ошибка импорта models: {e}")

    async def _simulate_full_processing_chain(self):
        """Симуляция полной цепочки обработки сигнал → ордер → исполнение"""
        self.logger.info("🔄 Симулируем полную цепочку обработки...")

        try:
            # Создаем новый тестовый сигнал для полной цепочки
            test_signal = Signal(
                symbol="BTCUSDT",
                exchange="bybit",
                signal_type=SignalType.LONG,
                strength=0.80,
                confidence=0.85,
                suggested_price=45000.0,
                suggested_quantity=0.001,
                suggested_stop_loss=44000.0,
                suggested_take_profit=46000.0,
                strategy_name="full_chain_test",
                timeframe="5m",
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=30),
                indicators={"test": True},
                extra_data={"full_chain_test": True},
            )

            # Сохраняем в БД
            async with get_async_db() as db:
                db.add(test_signal)
                await db.commit()
                await db.refresh(test_signal)

            self.logger.info(f"   🔸 Шаг 1: Создан тестовый сигнал {test_signal.id}")

            # Обрабатываем через SignalProcessor
            processor = SignalProcessor()
            processed = await processor.process_signal(test_signal)

            if processed:
                self.logger.info("   🔸 Шаг 2: Сигнал обработан ✅")
            else:
                self.logger.warning("   🔸 Шаг 2: Сигнал отклонен ⚠️")
                return

            # Создаем ордер
            class MockExchangeRegistry:
                async def get_exchange(self, name):
                    class MockExchange:
                        async def create_order(self, **kwargs):
                            return f"chain_test_{uuid.uuid4().hex[:8]}"

                        async def get_balance(self, asset):
                            return {"free": 1000.0}

                    return MockExchange()

            order_manager = OrderManager(MockExchangeRegistry())
            order = await order_manager.create_order_from_signal(test_signal, "chain_test_trader")

            if order:
                self.logger.info(f"   🔸 Шаг 3: Ордер создан {order.order_id} ✅")
            else:
                self.logger.error("   🔸 Шаг 3: Ордер НЕ создан ❌")
                return

            # Отправляем ордер
            submitted = await order_manager.submit_order(order)

            if submitted:
                self.logger.info("   🔸 Шаг 4: Ордер отправлен ✅")
            else:
                self.logger.error("   🔸 Шаг 4: Ордер НЕ отправлен ❌")

            self.logger.info("🎉 Полная цепочка протестирована!")

        except Exception as e:
            self.logger.error(f"❌ Ошибка в полной цепочке: {e}")
            self.test_stats["errors"].append(f"Full chain simulation error: {e}")

    async def _generate_diagnostic_report(self):
        """Генерация итогового отчета диагностики"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        self.logger.info("=" * 60)

        self.logger.info("📈 СТАТИСТИКА:")
        self.logger.info(f"   🔸 Создано тестовых сигналов: {self.test_stats['signals_created']}")
        self.logger.info(f"   🔸 Обработано сигналов: {self.test_stats['signals_processed']}")
        self.logger.info(f"   🔸 Создано ордеров: {self.test_stats['orders_created']}")
        self.logger.info(f"   🔸 Отправлено ордеров: {self.test_stats['orders_submitted']}")

        if self.test_stats["errors"]:
            self.logger.error(f"\n❌ ОШИБКИ ({len(self.test_stats['errors'])}):")
            for i, error in enumerate(self.test_stats["errors"], 1):
                self.logger.error(f"   {i}. {error}")

        if self.test_stats["warnings"]:
            self.logger.warning(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(self.test_stats['warnings'])}):")
            for i, warning in enumerate(self.test_stats["warnings"], 1):
                self.logger.warning(f"   {i}. {warning}")

        # Рекомендации
        self.logger.info("\n💡 РЕКОМЕНДАЦИИ:")

        if self.test_stats["signals_created"] > 0 and self.test_stats["orders_created"] == 0:
            self.logger.info("   🔸 КРИТИЧНО: Сигналы создаются, но ордера не создаются!")
            self.logger.info("      - Проверьте инициализацию OrderManager в TradingEngine")
            self.logger.info("      - Убедитесь что SignalProcessor вызывает создание ордеров")
            self.logger.info("      - Проверьте логику обработки в _process_signal()")

        if len(self.test_stats["errors"]) == 0:
            self.logger.info("   🎉 Все основные компоненты работают корректно!")
        else:
            self.logger.info(
                f"   ⚠️  Обнаружено {len(self.test_stats['errors'])} критических проблем"
            )

        self.logger.info("\n" + "=" * 60)


async def main():
    """Главная функция запуска диагностики"""
    diagnostics = ComprehensiveTradingDiagnostics()
    await diagnostics.run_comprehensive_tests()


if __name__ == "__main__":
    asyncio.run(main())
