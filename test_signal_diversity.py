#!/usr/bin/env python3
"""
Тест для проверки генерации сбалансированных LONG/SHORT сигналов после исправлений
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections import init_db
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("test_signal_diversity")


async def test_signal_generation():
    """
    Тестирует генерацию сигналов и проверяет разнообразие
    """
    try:
        logger.info("🚀 Начинаем тест генерации сигналов после исправлений...")

        # Инициализация
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Инициализация БД
        await init_db()

        # Инициализация ML Manager
        ml_manager = MLManager(config)
        await ml_manager.initialize()

        # Инициализация ML Signal Processor
        signal_processor = MLSignalProcessor(ml_manager, config, config_manager)
        await signal_processor.initialize()

        # Тестовые символы
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]

        # Счетчики сигналов
        signal_counts = {"LONG": 0, "SHORT": 0, "NEUTRAL": 0, "TOTAL": 0}

        logger.info("📊 Генерируем сигналы для тестовых символов...")

        # Генерируем сигналы для каждого символа
        for symbol in symbols:
            logger.info(f"\n🔄 Обрабатываем {symbol}...")

            try:
                # Генерируем случайные данные для теста
                # В реальной работе здесь будут актуальные OHLCV данные
                np.random.seed(hash(symbol) % 1000)  # Для воспроизводимости

                # Создаем синтетические OHLCV данные
                dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq="15min")
                price_base = 100 * (1 + np.random.rand())
                price_changes = np.random.randn(100) * 0.01
                prices = price_base * np.cumprod(1 + price_changes)

                ohlcv_data = pd.DataFrame(
                    {
                        "datetime": dates,
                        "open": prices * (1 + np.random.randn(100) * 0.001),
                        "high": prices * (1 + np.abs(np.random.randn(100)) * 0.002),
                        "low": prices * (1 - np.abs(np.random.randn(100)) * 0.002),
                        "close": prices,
                        "volume": np.random.randint(1000, 10000, 100),
                        "symbol": symbol,
                    }
                )

                # Генерируем сигнал
                signal = await signal_processor.process_market_data(
                    symbol=symbol,
                    exchange="bybit",
                    ohlcv_data=ohlcv_data,
                    additional_data={"current_price": float(prices[-1])},
                )

                if signal:
                    signal_type = signal.signal_type.name
                    signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1
                    signal_counts["TOTAL"] += 1

                    logger.info(
                        f"✅ {symbol}: {signal_type} сигнал "
                        f"(confidence: {signal.confidence:.2f}, strength: {signal.strength:.2f})"
                    )
                else:
                    signal_counts["NEUTRAL"] += 1
                    signal_counts["TOTAL"] += 1
                    logger.info(f"⚪ {symbol}: Нет сигнала (NEUTRAL)")

            except Exception as e:
                logger.error(f"Ошибка при обработке {symbol}: {e}")
                continue

        # Анализ результатов
        logger.info("\n" + "=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТА РАЗНООБРАЗИЯ СИГНАЛОВ")
        logger.info("=" * 60)

        if signal_counts["TOTAL"] > 0:
            long_pct = (signal_counts.get("LONG", 0) / signal_counts["TOTAL"]) * 100
            short_pct = (signal_counts.get("SHORT", 0) / signal_counts["TOTAL"]) * 100
            neutral_pct = (signal_counts.get("NEUTRAL", 0) / signal_counts["TOTAL"]) * 100

            logger.info(f"📈 LONG сигналов:    {signal_counts.get('LONG', 0)} ({long_pct:.1f}%)")
            logger.info(f"📉 SHORT сигналов:   {signal_counts.get('SHORT', 0)} ({short_pct:.1f}%)")
            logger.info(
                f"⚪ NEUTRAL сигналов: {signal_counts.get('NEUTRAL', 0)} ({neutral_pct:.1f}%)"
            )
            logger.info(f"📊 Всего сигналов:   {signal_counts['TOTAL']}")

            # Проверка баланса
            if long_pct > 80:
                logger.error("❌ ПРОБЛЕМА: Слишком много LONG сигналов!")
                logger.error("   Модель все еще имеет проблемы с интерпретацией")
            elif short_pct > 80:
                logger.error("❌ ПРОБЛЕМА: Слишком много SHORT сигналов!")
                logger.error("   Модель может быть слишком пессимистична")
            elif long_pct == 0:
                logger.error("❌ ПРОБЛЕМА: Нет LONG сигналов вообще!")
            elif short_pct == 0:
                logger.error("❌ ПРОБЛЕМА: Нет SHORT сигналов вообще!")
            else:
                logger.info("✅ УСПЕХ: Сигналы сбалансированы!")
                logger.info(f"   Соотношение LONG/SHORT: {long_pct:.1f}% / {short_pct:.1f}%")

                if 30 <= long_pct <= 70 and 30 <= short_pct <= 70:
                    logger.info("🎯 ОТЛИЧНО: Идеальный баланс сигналов для торговли!")
        else:
            logger.error("❌ Не удалось сгенерировать ни одного сигнала")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Тест завершен")

    except Exception as e:
        logger.error(f"Ошибка теста: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_signal_generation())
