#!/usr/bin/env python3
"""
Тест полной ML цепочки с реальными API ключами
"""

import asyncio
import os

import pandas as pd
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

from core.logger import setup_logger
from core.signals.unified_signal_processor import UnifiedSignalProcessor
from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager
from trading.order_executor import OrderExecutor

logger = setup_logger("test_real_ml_chain")


async def test_full_chain():
    """Тестирует полную цепочку с реальными API ключами"""

    try:
        # 1. Инициализация БД
        logger.info("1. Подключение к БД...")
        # AsyncPGPool автоматически инициализируется при первом вызове get_pool()

        # 2. Загрузка свежих данных
        logger.info("2. Загрузка свежих данных...")
        pool = await AsyncPGPool.get_pool()

        # Получаем последние 96 свечей для BTCUSDT
        candles = await pool.fetch(
            """
            SELECT datetime, open, high, low, close, volume
            FROM raw_market_data
            WHERE symbol = 'BTCUSDT'
            AND exchange = 'bybit'
            ORDER BY datetime DESC
            LIMIT 96
        """
        )

        if len(candles) < 96:
            logger.error(f"Недостаточно данных: {len(candles)} свечей")
            return

        logger.info(f"✅ Загружено {len(candles)} свечей")

        # 3. Инициализация ML Manager
        logger.info("3. Инициализация ML Manager...")
        # Загружаем ML конфигурацию
        import yaml

        with open("config/ml/ml_config.yaml", "r") as f:
            ml_config = yaml.safe_load(f)

        ml_manager = MLManager(ml_config)
        await ml_manager.initialize()

        # 4. Инициализация Order Executor
        logger.info("4. Инициализация Order Executor...")
        order_executor = OrderExecutor()
        await order_executor.initialize()

        # 5. Создание Unified Signal Processor
        logger.info("5. Создание Unified Signal Processor...")
        signal_processor = UnifiedSignalProcessor(
            ml_manager=ml_manager,
            trading_engine=None,  # Для теста не нужен
            config={
                "min_confidence_threshold": 0.3,
                "max_daily_trades": 100,
                "position_size": 0.001,  # Минимальный размер для теста
                "exchange": "bybit",
            },
        )

        # 6. Подготовка данных для ML
        logger.info("6. Подготовка данных для ML...")
        market_data = {
            "candles": [dict(row) for row in candles],
            "current_price": float(candles[0]["close"]),
            "symbol": "BTCUSDT",
        }

        # 7. Обработка ML предсказания
        logger.info("7. Генерация ML сигнала...")
        order = await signal_processor.process_ml_prediction("BTCUSDT", market_data)

        if order:
            logger.info(
                f"✅ Создан ордер: {order.symbol} {order.side} {order.quantity} @ {order.price}"
            )

            # 8. Исполнение ордера на бирже
            logger.info("8. Исполнение ордера на бирже...")
            success = await order_executor.execute_order(order)

            if success:
                logger.info("🎉 ОРДЕР УСПЕШНО ИСПОЛНЕН НА БИРЖЕ!")

                # Проверяем статус в БД
                order_status = await pool.fetchval(
                    "SELECT status FROM orders WHERE id = $1", order.id
                )
                logger.info(f"Статус в БД: {order_status}")
            else:
                logger.error("❌ Ордер отклонен биржей")

                # Получаем причину отклонения
                error = await pool.fetchval(
                    "SELECT metadata->>'error_message' FROM orders WHERE id = $1",
                    order.id,
                )
                logger.error(f"Причина: {error}")
        else:
            logger.warning("ML не сгенерировал торговый сигнал")

            # Давайте посмотрим что вернул ML
            logger.info("Проверяем предсказание ML напрямую...")
            # Преобразуем Decimal в float
            candles_data = []
            for row in candles:
                candles_data.append(
                    {
                        "datetime": row["datetime"],
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                    }
                )
            df = pd.DataFrame(candles_data).sort_values("datetime")
            prediction = await ml_manager.predict(df)

            logger.info(f"ML Prediction: {prediction}")

            # Проверим что модель вернула
            if prediction:
                logger.info(
                    f"ML вернул: signal_type={prediction.get('signal_type')}, confidence={prediction.get('confidence')}, strength={prediction.get('signal_strength')}"
                )

            # Показываем статистику
            stats = await signal_processor.get_stats()
            logger.info(f"Статистика процессора: {stats}")

        # 9. Общая статистика
        logger.info("\n=== ИТОГОВАЯ СТАТИСТИКА ===")

        # Статистика ML Manager
        if hasattr(ml_manager, "get_stats"):
            ml_stats = await ml_manager.get_stats()
            logger.info(f"ML Manager: {ml_stats}")
        else:
            logger.info("ML Manager работает корректно")

        # Статистика Signal Processor
        sp_stats = await signal_processor.get_stats()
        logger.info(f"Signal Processor: {sp_stats}")

        # Статистика Order Executor
        oe_stats = await order_executor.get_stats()
        logger.info(f"Order Executor: {oe_stats}")

        # Проверяем баланс на бирже
        if order_executor.exchanges.get("bybit"):
            logger.info("\n=== БАЛАНС НА БИРЖЕ ===")
            exchange = order_executor.exchanges["bybit"]
            balance = await exchange.fetch_balance()

            for currency, info in balance.items():
                if info.get("total", 0) > 0:
                    logger.info(f"{currency}: {info['total']} (free: {info['free']})")

    except Exception as e:
        logger.error(f"Ошибка в тесте: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await AsyncPGPool.close_pool()


if __name__ == "__main__":
    logger.info("🚀 Запуск теста полной ML цепочки с реальными API ключами")
    logger.info(f"BYBIT_API_KEY: {os.getenv('BYBIT_API_KEY')[:10]}...")
    asyncio.run(test_full_chain())
