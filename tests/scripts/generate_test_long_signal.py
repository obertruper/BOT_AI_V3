#!/usr/bin/env python3
"""
Генерация тестового LONG сигнала для проверки торгового пайплайна
"""

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal

sys.path.append(".")

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from database.models.base_models import SignalType
from database.models.signal import Signal

logger = setup_logger("test_signal_generator")


async def create_test_long_signal():
    """Создаем принудительный тестовый LONG сигнал"""

    try:
        # Инициализируем БД (пул создается автоматически при первом использовании)
        logger.info("✅ Подключение к БД будет установлено при первом запросе")

        # Создаем тестовый LONG сигнал
        test_signal = Signal(
            symbol="BTCUSDT",
            signal_type=SignalType.LONG,
            confidence=0.85,
            entry_price=Decimal("90000.0"),
            stop_loss=Decimal("88000.0"),  # -2.2%
            take_profit=Decimal("95000.0"),  # +5.5%
            position_size=Decimal("0.001"),
            source="TEST_MANUAL",
            strategy="test_long_signal",
            timeframe="15m",
            exchange="bybit",
            created_at=datetime.now(UTC),
            metadata={
                "test": True,
                "ml_confidence": 0.85,
                "risk_level": "LOW",
                "expected_duration": "2h",
                "generated_by": "manual_test",
            },
        )

        # Сохраняем в БД
        await AsyncPGPool.execute(
            """
            INSERT INTO signals (symbol, signal_type, confidence, entry_price, stop_loss, take_profit,
                               position_size, source, strategy, timeframe, exchange, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
            test_signal.symbol,
            test_signal.signal_type.value,
            float(test_signal.confidence),
            float(test_signal.entry_price),
            float(test_signal.stop_loss),
            float(test_signal.take_profit),
            float(test_signal.position_size),
            test_signal.source,
            test_signal.strategy,
            test_signal.timeframe,
            test_signal.exchange,
            test_signal.metadata,
            test_signal.created_at,
        )

        logger.info("🟢 ТЕСТОВЫЙ LONG СИГНАЛ СОЗДАН!")
        logger.info(f"📊 Символ: {test_signal.symbol}")
        logger.info(f"📈 Тип: {test_signal.signal_type.value}")
        logger.info(f"💰 Вход: ${test_signal.entry_price}")
        logger.info(f"🛑 SL: ${test_signal.stop_loss} (-2.2%)")
        logger.info(f"🎯 TP: ${test_signal.take_profit} (+5.5%)")
        logger.info(f"📏 Размер: {test_signal.position_size} BTC")
        logger.info(f"🎲 Уверенность: {test_signal.confidence * 100}%")

        print("\n" + "=" * 60)
        print("🚀 ТЕСТОВЫЙ LONG СИГНАЛ УСПЕШНО СОЗДАН!")
        print("=" * 60)
        print(f"📊 Символ: {test_signal.symbol}")
        print(f"📈 Направление: {test_signal.signal_type.value}")
        print(f"💰 Цена входа: ${test_signal.entry_price}")
        print(f"🛑 Stop Loss: ${test_signal.stop_loss} (-2.2%)")
        print(f"🎯 Take Profit: ${test_signal.take_profit} (+5.5%)")
        print(f"📏 Размер позиции: {test_signal.position_size} BTC")
        print(f"🎲 Уверенность: {test_signal.confidence * 100}%")
        print(f"🔧 Источник: {test_signal.source}")
        print(f"⏰ Создан: {test_signal.created_at}")
        print("=" * 60)
        print("👀 Теперь проверьте логи торговой системы для обработки этого сигнала!")
        print("=" * 60)

        await AsyncPGPool.close_pool()
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка создания тестового сигнала: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(create_test_long_signal())
    if success:
        print("\n✅ Скрипт выполнен успешно")
    else:
        print("\n❌ Ошибка выполнения скрипта")
        sys.exit(1)
