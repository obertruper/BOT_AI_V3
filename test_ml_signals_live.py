#!/usr/bin/env python3
"""
Тест генерации ML сигналов в реальном времени.
"""

import asyncio
import sys

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger(__name__)


async def test_ml_signals():
    """Тестируем генерацию сигналов."""

    print("🚀 Тестирование ML сигналов...")

    # Инициализация компонентов
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # ML Manager
    ml_manager = MLManager(config)
    await ml_manager.initialize()
    print("✅ ML Manager инициализирован")

    # ML Signal Processor
    signal_processor = MLSignalProcessor(ml_manager, config, config_manager)
    await signal_processor.initialize()
    print("✅ ML Signal Processor инициализирован")

    # Тестовые символы
    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    print("\n📊 Генерация сигналов:")
    for symbol in test_symbols:
        print(f"\n  Обработка {symbol}...")
        try:
            # Генерируем сигнал
            signal = await signal_processor.process_realtime_signal(symbol, "bybit")

            if signal:
                print(f"    ✅ Сгенерирован {signal.signal_type.value} сигнал")
                print(f"    📈 Уверенность: {signal.confidence:.2%}")
                print(f"    💪 Сила: {signal.strength:.2f}")
                print(f"    💰 Цена входа: {signal.suggested_price}")
                print(f"    🛑 Stop Loss: {signal.suggested_stop_loss}")
                print(f"    🎯 Take Profit: {signal.suggested_take_profit}")

                # Проверяем сохранение в БД
                if config.get("ml", {}).get("save_signals", True):
                    saved = await signal_processor.save_signal(signal)
                    if saved:
                        print("    💾 Сохранен в БД")
                    else:
                        print("    ❌ Ошибка сохранения в БД")
            else:
                print("    ⚠️ Сигнал не сгенерирован (недостаточная уверенность)")

        except Exception as e:
            print(f"    ❌ Ошибка: {e}")

    # Проверяем метрики
    metrics = await signal_processor.get_metrics()
    print("\n📊 Метрики обработки:")
    print(f"  Всего обработано: {metrics['total_processed']}")
    print(f"  Успешно сгенерировано: {metrics['success_rate']:.1%}")
    print(f"  Сохранено в БД: {metrics['save_rate']:.1%}")
    print(f"  Ошибок: {metrics['error_rate']:.1%}")


if __name__ == "__main__":
    asyncio.run(test_ml_signals())
