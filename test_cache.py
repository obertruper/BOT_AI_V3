#!/usr/bin/env python3
"""
Тест кеширования ML сигналов.
"""

import asyncio
import sys
import time

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger(__name__)


async def test_signal_caching():
    """Тестируем кеширование сигналов."""

    print("🔍 Тестирование кеширования сигналов...")

    # Инициализация
    config_manager = ConfigManager()
    config = config_manager.get_config()

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    signal_processor = MLSignalProcessor(ml_manager, config, config_manager)
    await signal_processor.initialize()

    print(f"📊 Cache TTL: {signal_processor.cache_ttl} сек (15 минут)")

    symbol = "BTCUSDT"

    # Первый запрос - должен быть без кеша
    print(f"\n1️⃣ Первый запрос для {symbol}...")
    start = time.time()
    signal1 = await signal_processor.process_realtime_signal(symbol, "bybit")
    time1 = time.time() - start
    print(f"   Время: {time1:.2f} сек")

    if signal1:
        print(
            f"   Сигнал: {signal1.signal_type.value}, confidence={signal1.confidence:.2%}"
        )

    # Второй запрос - должен быть из кеша
    print(f"\n2️⃣ Второй запрос для {symbol} (должен быть из кеша)...")
    start = time.time()
    signal2 = await signal_processor.process_realtime_signal(symbol, "bybit")
    time2 = time.time() - start
    print(f"   Время: {time2:.2f} сек")

    if signal2:
        print(
            f"   Сигнал: {signal2.signal_type.value}, confidence={signal2.confidence:.2%}"
        )

    # Проверяем что второй запрос быстрее
    if time2 < time1 * 0.5:
        print("✅ Кеширование работает! Второй запрос значительно быстрее.")
    else:
        print("⚠️ Кеширование может не работать. Времена похожи.")

    # Проверяем размер кеша
    cache_size = len(signal_processor.prediction_cache)
    print(f"\n📦 Размер кеша: {cache_size} записей")

    # Показываем ключи кеша
    if signal_processor.prediction_cache:
        print("🔑 Ключи в кеше:")
        for key in list(signal_processor.prediction_cache.keys())[:5]:
            print(f"   - {key}")


if __name__ == "__main__":
    asyncio.run(test_signal_caching())
